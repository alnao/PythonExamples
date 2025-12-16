import os
import time

from celery import Celery


broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery("tasks", broker=broker_url, backend=result_backend)


@celery_app.task
def long_task(duration: int = 5) -> str:
    """Simula un lavoro lungo."""
    time.sleep(duration)
    return f"Task completed in {duration} seconds"


