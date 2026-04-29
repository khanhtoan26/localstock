"""Phase 25 / DQ-01 + DQ-02 — Validation runner (D-01, D-06).

Implements the Tier 1 partition (this plan, 25-05). Tier 2 dispatch
(`evaluate_tier2`) lands in 25-07.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandera.errors as pae


def partition_valid_invalid(
    df: pd.DataFrame,
    schema: Any,
) -> tuple[pd.DataFrame, list[dict], pd.DataFrame | None]:
    """Validate ``df`` against ``schema`` lazily; partition rows.

    Returns ``(valid_df, invalid_rows, failure_cases_df)``.

    Each ``invalid_rows`` dict flattens the offending row's columns at the
    top level (so callers can read ``item["symbol"]`` directly) and adds
    metadata keys:
      - ``rule``    — canonical rule name (CONTEXT D-01 vocabulary)
      - ``reason``  — pandera check name as captured
      - ``all_rules`` — every distinct rule the row violated
      - ``row``     — the original row as a dict (used by the pipeline
                      caller as the quarantine ``payload``)
    """
    if schema is None:  # defensive — Wave 0 stub leftover
        raise RuntimeError("partition_valid_invalid: schema is None")

    try:
        valid = schema.validate(df, lazy=True)
        return valid, [], None
    except pae.SchemaErrors as exc:
        failure_cases = exc.failure_cases

        # Per-row rule map: idx -> [(rule, check_name), ...]
        rule_by_idx: dict[int, list[tuple[str, str]]] = {}
        # Frame-level (no specific row index) rules apply to every row.
        frame_rules: list[tuple[str, str]] = []

        for _, fc in failure_cases.iterrows():
            check_name = str(fc.get("check") or fc.get("check_number") or "unknown")
            column = "" if pd.isna(fc.get("column")) else str(fc.get("column") or "")
            rule = _normalize_rule(check_name, column)
            idx_val = fc.get("index")
            if pd.isna(idx_val):
                frame_rules.append((rule, check_name))
            else:
                try:
                    idx_int = int(idx_val)
                except (TypeError, ValueError):
                    continue
                rule_by_idx.setdefault(idx_int, []).append((rule, check_name))

        bad_idx_set: set[int] = set(rule_by_idx.keys())
        if frame_rules:
            # Any frame-level failure invalidates every row in the frame.
            bad_idx_set.update(int(i) for i in df.index.tolist())

        invalid_rows: list[dict] = []
        for i in sorted(bad_idx_set):
            rules = rule_by_idx.get(i, []) + frame_rules
            primary_rule, primary_check = (
                rules[0] if rules else ("unknown", "unknown")
            )
            row_dict = df.loc[i].to_dict()
            payload_dict = _coerce_payload(row_dict)
            invalid_rows.append(
                {
                    **row_dict,  # flatten so callers can read item["symbol"]
                    "row": payload_dict,
                    "rule": primary_rule,
                    "reason": primary_check,
                    "all_rules": sorted({r[0] for r in rules}),
                }
            )

        valid_df = df.drop(index=list(bad_idx_set), errors="ignore")
        return valid_df, invalid_rows, failure_cases


def _coerce_payload(row: dict) -> dict:
    """Coerce a row dict's values to JSON-serializable scalars.

    Pandas/numpy-native types (Timestamp, datetime, date, numpy scalars)
    are converted to plain ``str``/``int``/``float`` so that
    ``QuarantineRepository.insert`` → ``json.dumps`` succeeds. NaN/Inf
    remain as ``float`` here — ``sanitize_jsonb`` (called inside
    ``QuarantineRepository.insert``) handles those at the JSONB
    write boundary (Rule 1 / DQ-04 belt-and-suspenders).
    """
    import datetime as _dt

    out: dict = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
        elif isinstance(v, pd.Timestamp):
            out[k] = v.isoformat()
        elif isinstance(v, (_dt.datetime, _dt.date)):
            out[k] = v.isoformat()
        elif hasattr(v, "item") and not isinstance(v, (str, bytes)):
            # numpy scalar → native Python (np.int64/np.float64).
            try:
                out[k] = v.item()
            except Exception:
                out[k] = v
        else:
            out[k] = v
    return out


def _normalize_rule(check_name: str, column: str) -> str:
    """Map pandera check names → CONTEXT D-01 canonical rule strings."""
    cn = (check_name or "").lower()
    if "future_date" in cn:
        return "future_date"
    if "nan_ratio" in cn:
        return "nan_ratio_exceeded"
    if "malformed_date" in cn:
        return "malformed_date"
    if "unique" in cn or "duplicate" in cn:
        return "duplicate_pk"
    if "str_matches" in cn:
        return "bad_symbol_format"
    if "greater_than" in cn or cn == "gt" or cn.startswith("greater_than"):
        return f"non_positive_{column}" if column else "negative_price"
    if "greater_than_or_equal" in cn or cn == "ge":
        return f"negative_{column}" if column else "negative_value"
    if "not_nullable" in cn or "nullable" in cn:
        return f"null_{column}" if column else "null_value"
    if "dtype" in cn or "type" in cn:
        return f"bad_type_{column}" if column else "bad_type"
    return cn or "unknown"


# ---------------------------------------------------------------------
# Tier 2 — DQ-02 / 25-07. Advisory dispatch with per-rule mode lookup.
# ---------------------------------------------------------------------
def evaluate_tier2(
    rule: str,
    df: Any,
    predicate: Any,
    *,
    symbol: str | None = None,
) -> None:
    """Run a Tier 2 advisory check.

    - ``predicate(df)`` MUST return a DataFrame (or anything with ``.empty``)
      of offending rows. An empty/None result == pass (no-op).
    - ALWAYS emits ``localstock_dq_violations_total{rule, tier}`` and
      a structured ``dq_warn`` log line when the predicate fires.
    - In ``shadow`` mode (default): logs + counts and returns ``None``.
    - In ``enforce`` mode: same emission then raises ``Tier2Violation``.

    Tier label: ``advisory`` when mode == ``shadow``; ``strict`` when
    mode == ``enforce``. Promotion from shadow → strict is operational
    (env flag flip) — see ``docs/runbook/dq-tier2-promotion.md``.

    Per CONTEXT D-06 + D-03 + RESEARCH §Pattern 2.
    """
    from loguru import logger

    from localstock.dq.shadow import Tier2Violation, get_tier2_mode
    from localstock.observability.metrics import iter_tracked_collectors

    bad = predicate(df)
    if bad is None:
        return
    has_empty = hasattr(bad, "empty")
    if has_empty and bad.empty:
        return

    mode = get_tier2_mode(rule)
    tier = "advisory" if mode == "shadow" else "strict"

    try:
        count = len(bad)
    except TypeError:
        count = 0

    incremented = 0
    try:
        for counter in iter_tracked_collectors("localstock_dq_violations_total"):
            counter.labels(rule=rule, tier=tier).inc(count)
            incremented += 1
    except Exception:  # noqa: BLE001 — metric lookup must never crash dispatch
        logger.debug("dq.tier2.metric_lookup_failed", rule=rule)
    if incremented == 0:
        logger.debug("dq.tier2.metric_not_registered", rule=rule)

    logger.warning(
        "dq_warn",
        rule=rule,
        tier=tier,
        symbol=symbol,
        violation_count=count,
    )

    if mode == "enforce":
        raise Tier2Violation(rule, bad)
