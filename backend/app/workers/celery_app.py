"""Celery application factory."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "deepfake_detector",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 30,  # 30 min hard limit
    task_soft_time_limit=60 * 25,
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.process_image_scan": {"queue": "image"},
        "app.workers.tasks.process_video_scan": {"queue": "video"},
        "app.workers.tasks.process_audio_scan": {"queue": "audio"},
        "app.workers.tasks.process_text_scan": {"queue": "text"},
        "app.workers.tasks.process_url_scan": {"queue": "url"},
    },
)
