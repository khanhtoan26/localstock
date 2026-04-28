#!/usr/bin/env bash
# OBS-06 — fail if any logger.X(f"...") call exists in src or tests.
# Per CONTEXT.md D-07. Escape: append `# noqa: log-fstring` to a line to bypass.
set -euo pipefail

PATTERN='logger\.(debug|info|warning|error|critical|exception|trace|success)\(\s*f["'"'"']'
ROOTS=("apps/prometheus/src" "apps/prometheus/tests" "apps/prometheus/bin")

HITS=$(grep -rEn "$PATTERN" "${ROOTS[@]}" 2>/dev/null | grep -v 'noqa: log-fstring' || true)

if [ -n "$HITS" ]; then
  echo "::error::f-string log calls detected — convert to positional/kwargs (Phase 22 RESEARCH §6):"
  echo "$HITS"
  exit 1
fi
echo "OK: zero f-string log calls."
