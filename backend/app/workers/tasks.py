"""Celery tasks for AI processing.

Each task:
- Loads the Scan row.
- Downloads the file from MinIO (for file-based scans).
- Calls the relevant AI service.
- Persists the result back to the database.

The virus scan has already happened *before* the task is queued, in the API
layer. Workers therefore never receive infected files.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure the ai-services package is importable in both local dev and Docker.
# Docker image already sets PYTHONPATH=/srv:/srv/ai-services; this fallback
# helps when running uvicorn/celery directly from the repo root.
for _candidate in (
    Path(__file__).resolve().parents[3] / "ai-services",
    Path("/srv/ai-services"),
):
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.append(str(_candidate))

from celery import Task

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.scan import Scan, ScanStatus, ScanType
from app.services.storage import get_storage
from app.workers.celery_app import celery_app

log = get_logger(__name__)


def _update_scan(scan_id: str, **fields) -> None:
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == uuid.UUID(scan_id)).first()
        if not scan:
            log.warning("worker.scan_not_found", scan_id=scan_id)
            return
        for k, v in fields.items():
            setattr(scan, k, v)
        db.commit()
    finally:
        db.close()


def _set_processing(scan_id: str) -> None:
    _update_scan(
        scan_id,
        status=ScanStatus.PROCESSING,
        started_at=datetime.now(timezone.utc),
    )


def _set_completed(scan_id: str, result: dict) -> None:
    _update_scan(
        scan_id,
        status=ScanStatus.COMPLETED,
        score=result.get("score"),
        label=result.get("label"),
        confidence=result.get("confidence"),
        explanation=result.get("explanation"),
        result_payload=result,
        completed_at=datetime.now(timezone.utc),
    )


def _set_failed(scan_id: str, error: str) -> None:
    _update_scan(
        scan_id,
        status=ScanStatus.FAILED,
        error_message=error[:2000],
        completed_at=datetime.now(timezone.utc),
    )


def _load_scan_text(scan_id: str) -> tuple[Scan | None, bytes | None]:
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == uuid.UUID(scan_id)).first()
        if not scan:
            return None, None
        data = None
        if scan.storage_key:
            data = get_storage().download_bytes(scan.storage_key)
        return scan, data
    finally:
        db.close()


# ---------------- Image ----------------
@celery_app.task(name="app.workers.tasks.process_image_scan", bind=True)
def process_image_scan(self: Task, scan_id: str) -> dict:
    from image.detector import detect_image  # type: ignore

    _set_processing(scan_id)
    try:
        scan, data = _load_scan_text(scan_id)
        if not scan or data is None:
            raise RuntimeError("Scan or file data not found")
        result = detect_image(data)
        _set_completed(scan_id, result)
        return result
    except Exception as exc:
        log.error("worker.image_failed", scan_id=scan_id, error=str(exc))
        _set_failed(scan_id, str(exc))
        raise


# ---------------- Video ----------------
@celery_app.task(name="app.workers.tasks.process_video_scan", bind=True)
def process_video_scan(self: Task, scan_id: str) -> dict:
    from video.detector import detect_video  # type: ignore

    _set_processing(scan_id)
    try:
        scan, data = _load_scan_text(scan_id)
        if not scan or data is None:
            raise RuntimeError("Scan or file data not found")
        result = detect_video(data)
        _set_completed(scan_id, result)
        return result
    except Exception as exc:
        log.error("worker.video_failed", scan_id=scan_id, error=str(exc))
        _set_failed(scan_id, str(exc))
        raise


# ---------------- Audio ----------------
@celery_app.task(name="app.workers.tasks.process_audio_scan", bind=True)
def process_audio_scan(self: Task, scan_id: str) -> dict:
    from audio.detector import detect_audio  # type: ignore

    _set_processing(scan_id)
    try:
        scan, data = _load_scan_text(scan_id)
        if not scan or data is None:
            raise RuntimeError("Scan or file data not found")
        ext = Path(scan.original_filename or "").suffix.lower() or ".wav"
        result = detect_audio(data, extension=ext)
        _set_completed(scan_id, result)
        return result
    except Exception as exc:
        log.error("worker.audio_failed", scan_id=scan_id, error=str(exc))
        _set_failed(scan_id, str(exc))
        raise


# ---------------- Text ----------------
@celery_app.task(name="app.workers.tasks.process_text_scan", bind=True)
def process_text_scan(self: Task, scan_id: str) -> dict:
    from text.detector import detect_text  # type: ignore

    _set_processing(scan_id)
    try:
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == uuid.UUID(scan_id)).first()
            if not scan or not scan.input_text:
                raise RuntimeError("Scan or text not found")
            text = scan.input_text
        finally:
            db.close()

        result = detect_text(text)
        _set_completed(scan_id, result)
        return result
    except Exception as exc:
        log.error("worker.text_failed", scan_id=scan_id, error=str(exc))
        _set_failed(scan_id, str(exc))
        raise


# ---------------- URL ----------------
@celery_app.task(name="app.workers.tasks.process_url_scan", bind=True)
def process_url_scan(self: Task, scan_id: str) -> dict:
    from url.detector import detect_url  # type: ignore

    _set_processing(scan_id)
    try:
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == uuid.UUID(scan_id)).first()
            if not scan or not scan.source_url:
                raise RuntimeError("Scan or URL not found")
            url = scan.source_url
        finally:
            db.close()

        result = detect_url(url)
        _set_completed(scan_id, result)
        return result
    except Exception as exc:
        log.error("worker.url_failed", scan_id=scan_id, error=str(exc))
        _set_failed(scan_id, str(exc))
        raise
