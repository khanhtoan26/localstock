"""Phase 25 / DQ-08 — APScheduler retention job registration."""

from __future__ import annotations

from apscheduler.triggers.cron import CronTrigger


def test_quarantine_cleanup_job_registered() -> None:
    from localstock.scheduler.scheduler import scheduler, setup_scheduler

    # Reset job store for test isolation.
    scheduler.remove_all_jobs()
    setup_scheduler()
    job = scheduler.get_job("dq_quarantine_cleanup")
    assert job is not None, "DQ-08: dq_quarantine_cleanup job missing"

    # CronTrigger with hour=3 minute=15 in Asia/Ho_Chi_Minh
    # (per RESEARCH Pattern 5 + Pitfall F).
    assert isinstance(job.trigger, CronTrigger)
    # ``CronTrigger.__str__`` omits timezone; check the attribute directly.
    assert str(job.trigger.timezone) == "Asia/Ho_Chi_Minh"

    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "3"
    assert fields["minute"] == "15"

    # Pitfall F — single instance + coalesce so retention can't pile up.
    assert job.max_instances == 1
    assert job.coalesce is True

