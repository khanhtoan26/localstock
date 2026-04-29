"""Phase 26 / D-03 — Per-key asyncio.Lock via WeakValueDictionary."""
from __future__ import annotations

import asyncio
import weakref

# Module-level WeakValueDictionary; entries auto-GC when no strong ref
# is held by any awaiter. CALLER MUST hold a strong local ref to the
# returned lock for the lifetime of its ``async with`` (RESEARCH P-3).
_locks: "weakref.WeakValueDictionary[str, asyncio.Lock]" = weakref.WeakValueDictionary()


def get_lock(full_key: str) -> asyncio.Lock:
    """Return a per-key lock; creates one lazily on first call.

    P-2: lock is allocated lazily inside the calling coroutine, never at
    module import — binds to the *current* event loop, not the import-time
    loop. P-3: caller MUST keep ``lock`` as a local variable across
    ``async with`` to prevent premature GC.
    """
    lock = _locks.get(full_key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[full_key] = lock
    return lock
