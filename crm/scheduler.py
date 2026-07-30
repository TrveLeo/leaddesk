from apscheduler.schedulers.background import BackgroundScheduler

from crm.config import settings
from crm.jobs import followup_job

_scheduler = BackgroundScheduler()


def start() -> None:
    _scheduler.add_job(
        followup_job,
        trigger="cron",
        hour=settings.followup_job_hour,
        minute=settings.followup_job_minute,
        id="followup",
        replace_existing=True,
    )
    _scheduler.start()
    print(
        f"[scheduler] Follow-up job agendado para "
        f"{settings.followup_job_hour:02d}:{settings.followup_job_minute:02d} diariamente."
    )


def stop() -> None:
    _scheduler.shutdown(wait=False)
