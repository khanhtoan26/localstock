"""Phase 26 / D-01 — Version-key resolver.

``resolve_latest_run_id`` returns the integer ``pipeline_run_id`` used
to compose cache keys (e.g. ``scores:ranking:limit=50:run={id}``). The
result itself is cached for 5s under the ``pipeline:latest_run_id``
namespace (D-02) so back-to-back composers in the same request burst
share a single DB roundtrip (T-26-03-03 mitigation).

**Invalidation contract:** the pipeline finalize hook landing in 26-05
MUST call ``invalidate_namespace('pipeline:latest_run_id')`` after a
new run reaches ``status='completed'``. Without that, the 5s TTL caps
version-bump latency at 5s — still correct, just slower (T-26-03-01).

The session factory is a zero-arg async-context-manager callable
matching ``AutomationService.session_factory`` so the helper can open
its own short-lived session for the cached lookup.
"""
from __future__ import annotations

from typing import AsyncContextManager, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from localstock.cache.registry import get_cache  # noqa: F401  (registry-warmup import)
from localstock.db.repositories.pipeline_run_repo import PipelineRunRepository


async def resolve_latest_run_id(
    session_factory: Callable[[], AsyncContextManager[AsyncSession]],
) -> int | None:
    """Return the current ``pipeline_run_id`` for cache-key composition.

    Wraps ``PipelineRunRepository.get_latest_completed`` in
    ``get_or_compute(namespace='pipeline:latest_run_id', key='current', ...)``
    so a 5s TTL absorbs request bursts without DB hits.
    """
    # Local import avoids a circular dependency: cache/__init__.py
    # already imports from this module to re-export the helper.
    from localstock.cache import get_or_compute

    async def _fetch() -> int | None:
        async with session_factory() as session:
            repo = PipelineRunRepository(session)
            return await repo.get_latest_completed()

    return await get_or_compute(
        namespace="pipeline:latest_run_id",
        key="current",
        compute_fn=_fetch,
    )
