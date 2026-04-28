"""Tests for Phase 22 OBS-03: pipeline run_id propagation via contextvar.

# RED until Wave 1 — depends on `localstock.observability.context.run_id_var`.
Per CONTEXT.md D-03: run_id propagates through `logger.contextualize(run_id=...)`
and survives `asyncio.gather` via `contextvars.ContextVar`.
"""

import uuid

from loguru import logger

from localstock.observability.context import run_id_var


class TestRunIdContextvar:
    def test_run_id_attached_to_records_within_contextualize(self, loguru_caplog):
        run_id = str(uuid.uuid4())
        token = run_id_var.set(run_id)
        try:
            with logger.contextualize(run_id=run_id):
                logger.info("pipeline.step.one", step=1)
                logger.info("pipeline.step.two", step=2)
        finally:
            run_id_var.reset(token)

        events = [r for r in loguru_caplog.records if r["message"].startswith("pipeline.step.")]
        assert len(events) >= 2
        for rec in events:
            assert rec["extra"].get("run_id") == run_id

    def test_run_id_default_none(self):
        # Outside of a contextualize block, the var is None.
        assert run_id_var.get() is None
