"""Phase 24 — @observe decorator (D-01, OBS-11).

Wraps a function/coroutine with timing + structured log + Prometheus
histogram emission against the Phase 23 ``localstock_op_duration_seconds``
primitive (labels: ``domain, subsystem, action, outcome``).

Naming convention enforced at decoration time: ``name`` MUST be of the form
``domain.subsystem.action`` (3 dot-separated, non-empty tokens). Malformed
names raise ``ValueError`` at decoration / import time, never silently at
call time.

Behaviour (per CONTEXT D-01):
  - Detects coroutine functions via ``inspect.iscoroutinefunction`` and
    returns the matching async / sync wrapper.
  - On exception: marks ``outcome=fail``, records the histogram, emits
    ``op_failed`` log (when ``log=True``), then **re-raises** the original
    exception (bare ``raise`` — preserves traceback).
  - On success: marks ``outcome=success``, records the histogram, emits
    ``op_complete`` log (when ``log=True``).

Logs use structured kwargs only (no f-strings — Phase 22 OBS-06).
"""
from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from loguru import logger
from prometheus_client import REGISTRY

P = ParamSpec("P")
R = TypeVar("R")

_OP_HIST_NAME = "localstock_op_duration_seconds"


def _split_name(name: str) -> tuple[str, str, str]:
    """Validate ``name`` and split into ``(domain, subsystem, action)``.

    Raises:
        ValueError: when ``name`` does not contain exactly 3 non-empty
            dot-separated tokens.
    """
    parts = name.split(".")
    if len(parts) != 3 or not all(p for p in parts):
        raise ValueError(
            f"@observe name must be 'domain.subsystem.action' "
            f"(3 non-empty dot-separated tokens); got {name!r}"
        )
    return parts[0], parts[1], parts[2]


def _get_op_histogram() -> Any:
    """Lazy lookup of the Phase 23 histogram on the default registry.

    Looked up lazily so tests can rely on the module-level
    ``_DEFAULT_METRICS`` registration in ``observability.metrics`` without
    binding the decorator to a stale collector at import time.
    """
    coll = REGISTRY._names_to_collectors.get(_OP_HIST_NAME)
    if coll is None:
        # Defensive: init_metrics() should have run at observability.metrics
        # import. Fall back to an idempotent re-init.
        from localstock.observability.metrics import init_metrics

        return init_metrics()["op_duration_seconds"]
    return coll


def observe(
    name: str, *, log: bool = True
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Time + log + emit histogram for the wrapped function.

    Args:
        name: ``"domain.subsystem.action"`` — split into 3 histogram labels.
        log: When True (default) emit ``op_complete`` / ``op_failed`` log
            line. Set False to record the metric silently.

    Returns:
        Decorator that wraps either a sync function or a coroutine function.
        Wrapper preserves ``functools.wraps`` metadata, so
        ``inspect.iscoroutinefunction`` continues to report the original
        coroutine identity for async wrappees.
    """
    domain, subsystem, action = _split_name(name)  # validate at decoration time

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:

            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                hist = _get_op_histogram()
                t0 = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)  # type: ignore[misc]
                except Exception as exc:
                    elapsed = time.perf_counter() - t0
                    hist.labels(domain, subsystem, action, "fail").observe(elapsed)
                    if log:
                        logger.opt(exception=False).error(
                            "op_failed",
                            op_name=name,
                            duration_ms=int(elapsed * 1000),
                            outcome="fail",
                            error_type=type(exc).__name__,
                        )
                    raise  # bare re-raise — never swallow (D-01)
                else:
                    elapsed = time.perf_counter() - t0
                    hist.labels(domain, subsystem, action, "success").observe(elapsed)
                    if log:
                        logger.info(
                            "op_complete",
                            op_name=name,
                            duration_ms=int(elapsed * 1000),
                            outcome="success",
                        )
                    return result

            return async_wrapper  # type: ignore[return-value]

        @wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            hist = _get_op_histogram()
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                elapsed = time.perf_counter() - t0
                hist.labels(domain, subsystem, action, "fail").observe(elapsed)
                if log:
                    logger.error(
                        "op_failed",
                        op_name=name,
                        duration_ms=int(elapsed * 1000),
                        outcome="fail",
                        error_type=type(exc).__name__,
                    )
                raise
            else:
                elapsed = time.perf_counter() - t0
                hist.labels(domain, subsystem, action, "success").observe(elapsed)
                if log:
                    logger.info(
                        "op_complete",
                        op_name=name,
                        duration_ms=int(elapsed * 1000),
                        outcome="success",
                    )
                return result

        return sync_wrapper

    return decorator


def timed_query(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Repository-level alias — equivalent to ``observe(f"db.query.{name}")``.

    Use on service methods that wrap multiple SQL statements (bulk upserts,
    transactional batches) where event-level timing from the SQLAlchemy
    listener (Phase 24-03) is too low-grain.
    """
    return observe(f"db.query.{name}")
