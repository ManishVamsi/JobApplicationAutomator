"""Celery application configuration."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jobapp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # JSON serialization only (not pickle — security)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Retry policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Task routing
    task_routes={
        "app.workers.job_fetch_task.*": {"queue": "job_fetch"},
        "app.workers.linkedin_score_task.*": {"queue": "scoring"},
        "app.workers.resume_parse_task.*": {"queue": "resume"},
    },
    # Beat schedule — driven by config, not hardcoded
    beat_schedule={
        "daily-job-fetch": {
            "task": "app.workers.job_fetch_task.fetch_jobs_for_all_users",
            "schedule": __import__("celery.schedules", fromlist=["crontab"]).crontab(
                *settings.JSEARCH_FETCH_CRON.split()[:2],
                day_of_month=settings.JSEARCH_FETCH_CRON.split()[2],
                month_of_year=settings.JSEARCH_FETCH_CRON.split()[3],
                day_of_week=settings.JSEARCH_FETCH_CRON.split()[4],
            ),
        },
    },
)
