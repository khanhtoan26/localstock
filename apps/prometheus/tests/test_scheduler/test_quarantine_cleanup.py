"""Phase 25 / DQ-08 — APScheduler retention job registration (RED until 25-03)."""

from __future__ import annotations


def test_quarantine_cleanup_job_registered() -> None:
    from localstock.scheduler.scheduler import scheduler, setup_scheduler

    # Reset job store for test isolation.
    scheduler.remove_all_jobs()
    setup_scheduler()
    job = scheduler.get_job("dq_quarantine_cleanup")
    assert job is not None, "DQ-08: dq_quarantine_cleanup job missing"
    # CronTrigger with hour=3 minute=15 in Asia/Ho_Chi_Minh
    # (per RESEARCH Pattern 5 + Pitfall F).
    assert "Asia/Ho_Chi_Minh" in str(job.trigger)
