"""Phase 25 — Data Quality package (D-01).

Single home for pandera schemas, the JSONB sanitizer, the per-rule shadow
dispatcher, and the quarantine repo. See 25-CONTEXT.md for design.
"""
from __future__ import annotations

# Per CONTEXT D-07 + RESEARCH Pitfall G: cap error message length on the
# failed_symbols JSON to bound stats row size.
MAX_ERROR_CHARS: int = 200

__all__ = ["MAX_ERROR_CHARS"]
