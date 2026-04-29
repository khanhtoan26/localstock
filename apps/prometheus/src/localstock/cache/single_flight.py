"""Phase 26 / D-03 — Per-key asyncio.Lock via WeakValueDictionary (stub).

Full implementation lands in 26-01 Task 2.
"""
from __future__ import annotations

import asyncio
import weakref

# Module-level WeakValueDictionary; entries auto-GC when no strong ref
# held by any awaiter. Test conftest expects `_locks` to be present so
# `_locks.clear()` between tests works during RED collection.
_locks: "weakref.WeakValueDictionary[str, asyncio.Lock]" = weakref.WeakValueDictionary()


def get_lock(full_key: str) -> asyncio.Lock:  # pragma: no cover - stub
    raise NotImplementedError("26-01 Task 2 fills this in")
