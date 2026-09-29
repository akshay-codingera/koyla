import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "koyla_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "reap-stale-jobs-periodic": {
            "task": "app.tasks.reap_stale_jobs_task",
            "schedule": float(settings.JOB_JANITOR_INTERVAL_MINUTES * 60),
        },
    },
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["app.tasks"])


def check_celery_health() -> dict:
    """
    Inspect worker health and broker connectivity.
    """
    status = {
        "broker_connected": False,
        "active_workers": 0,
        "registered_tasks": [],
        "error": None,
    }
    try:
        # Check broker connection
        with celery_app.connection_for_read() as conn:
            conn.connect()
            status["broker_connected"] = True

        # Inspect active workers
        inspector = celery_app.control.inspect(timeout=1.0)
        if inspector:
            ping_res = inspector.ping()
            if ping_res:
                status["active_workers"] = len(ping_res)
            registered = inspector.registered()
            if registered:
                all_tasks = set()
                for worker_tasks in registered.values():
                    all_tasks.update(worker_tasks)
                status["registered_tasks"] = sorted(list(all_tasks))
    except Exception as e:
        status["error"] = str(e)

    return status
