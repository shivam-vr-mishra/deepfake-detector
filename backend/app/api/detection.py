"""Detection endpoints: image/video/audio/text/url.

Upload flow (file-based scans):
    1. Validate file (extension, size, sniffed MIME)
    2. Hash (SHA-256) → check blacklist
    3. Virus scan via ClamAV  (FAIL CLOSED if scanner is down)
    4. If clean → upload to MinIO under a fresh UUID key
    5. Create Scan row → enqueue Celery task → return scan_id
    6. If infected → record audit event, blacklist hash (optional), reject
"""
import io
import uuid

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.api.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.models.audit import AuditEvent
from app.models.scan import Scan, ScanStatus, ScanType
from app.schemas.detection import (
    ScanCreatedResponse,
    TextDetectRequest,
    UrlDetectRequest,
)
from app.security.audit import record_event
from app.security.file_validator import validate_upload
from app.security.hashing import is_blacklisted, sha256_bytes, add_to_blacklist
from app.security.rate_limit import limiter
from app.security.virus_scanner import VirusScanError, get_virus_scanner
from app.services.plans import (
    check_quota,
    get_credit_balance,
    get_or_create_subscription,
    increment_usage,
    reserve_scan,
)
from app.services.storage import get_storage
from app.workers.tasks import (
    process_audio_scan,
    process_image_scan,
    process_text_scan,
    process_url_scan,
    process_video_scan,
)

router = APIRouter(prefix="/detect", tags=["detection"])
log = get_logger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _enforce_quota(db, user, sub) -> str:
    """Reserve a scan against daily free quota, then credits.

    Returns the source used: "free" or "credit". Raises 429 if neither is
    available so the user can buy credits or upgrade.
    """
    ok, source = reserve_scan(db, user.id, sub.plan)
    if not ok:
        _, used, limit = check_quota(db, user.id, sub.plan)
        balance = get_credit_balance(db, user.id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily quota exhausted ({used}/{limit}) and 0 credits remaining. "
                f"Buy credits or upgrade your plan."
            ),
        )
    return source


def _secure_upload_pipeline(
    *,
    request: Request,
    db,
    user,
    sub,
    file: UploadFile,
    data: bytes,
    scan_type: ScanType,
    quota_source: str = "free",
) -> Scan:
    """Run the secure upload pipeline and return a queued Scan row."""
    record_event(
        db,
        event=AuditEvent.UPLOAD_ATTEMPT,
        user_id=user.id,
        request=request,
        message=f"{scan_type.value}: {file.filename}",
    )

    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    # 1. Validate
    result = validate_upload(
        filename=file.filename or "upload",
        declared_mime=file.content_type,
        data=data,
        scan_type=scan_type,
        plan=sub.plan,
    )
    if not result.ok:
        record_event(
            db,
            event=AuditEvent.UPLOAD_REJECTED,
            user_id=user.id,
            request=request,
            message=result.reason,
        )
        raise HTTPException(status_code=400, detail=result.reason)

    # 2. Hash & blacklist
    digest = sha256_bytes(data)
    if is_blacklisted(db, digest):
        record_event(
            db,
            event=AuditEvent.BLACKLISTED_HASH,
            user_id=user.id,
            request=request,
            message=f"sha256={digest}",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File is blacklisted (known malicious content)",
        )

    # 3. Virus scan (FAIL CLOSED)
    scanner = get_virus_scanner()
    try:
        scan_result = scanner.scan_stream(io.BytesIO(data))
    except VirusScanError as e:
        log.error("upload.virus_scanner_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Virus scanner unavailable. Upload rejected.",
        )

    if not scan_result.safe:
        record_event(
            db,
            event=AuditEvent.VIRUS_DETECTED,
            user_id=user.id,
            request=request,
            message=f"{scan_result.signature}",
            metadata={"sha256": digest, "filename": file.filename},
        )
        # Optionally extend the blacklist
        try:
            add_to_blacklist(db, digest, reason=scan_result.signature, source="clamav")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload rejected: virus detected ({scan_result.signature})",
        )

    # 4. Upload to MinIO under a fresh UUID key
    storage = get_storage()
    key = storage.make_key(scan_type.value, result.extension or "")
    storage.upload_bytes(key, data, content_type=result.mime or "application/octet-stream")

    # 5. Persist Scan row + enqueue
    scan = Scan(
        user_id=user.id,
        scan_type=scan_type,
        status=ScanStatus.QUEUED,
        original_filename=file.filename,
        mime_type=result.mime,
        file_size=result.size,
        file_hash=digest,
        storage_key=key,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    if quota_source == "free":
        increment_usage(db, user.id)
    return scan


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.post(
    "/image",
    response_model=ScanCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("30/minute")
async def detect_image(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    sub = get_or_create_subscription(db, user.id)
    source = _enforce_quota(db, user, sub)
    data = await file.read()
    scan = _secure_upload_pipeline(
        request=request,
        db=db,
        user=user,
        sub=sub,
        file=file,
        data=data,
        scan_type=ScanType.IMAGE,
        quota_source=source,
    )
    task = process_image_scan.delay(str(scan.id))
    scan.celery_task_id = task.id
    db.commit()
    return ScanCreatedResponse(scan_id=scan.id, status=scan.status)


@router.post(
    "/video",
    response_model=ScanCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def detect_video(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    sub = get_or_create_subscription(db, user.id)
    source = _enforce_quota(db, user, sub)
    data = await file.read()
    scan = _secure_upload_pipeline(
        request=request,
        db=db,
        user=user,
        sub=sub,
        file=file,
        data=data,
        scan_type=ScanType.VIDEO,
        quota_source=source,
    )
    task = process_video_scan.delay(str(scan.id))
    scan.celery_task_id = task.id
    db.commit()
    return ScanCreatedResponse(scan_id=scan.id, status=scan.status)


@router.post(
    "/audio",
    response_model=ScanCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("20/minute")
async def detect_audio(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    sub = get_or_create_subscription(db, user.id)
    source = _enforce_quota(db, user, sub)
    data = await file.read()
    scan = _secure_upload_pipeline(
        request=request,
        db=db,
        user=user,
        sub=sub,
        file=file,
        data=data,
        scan_type=ScanType.AUDIO,
        quota_source=source,
    )
    task = process_audio_scan.delay(str(scan.id))
    scan.celery_task_id = task.id
    db.commit()
    return ScanCreatedResponse(scan_id=scan.id, status=scan.status)


@router.post(
    "/text",
    response_model=ScanCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("60/minute")
async def detect_text(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    payload: TextDetectRequest,
):
    sub = get_or_create_subscription(db, user.id)
    source = _enforce_quota(db, user, sub)

    scan = Scan(
        user_id=user.id,
        scan_type=ScanType.TEXT,
        status=ScanStatus.QUEUED,
        input_text=payload.text,
        file_size=len(payload.text.encode("utf-8")),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    if source == "free":
        increment_usage(db, user.id)

    task = process_text_scan.delay(str(scan.id))
    scan.celery_task_id = task.id
    db.commit()
    return ScanCreatedResponse(scan_id=scan.id, status=scan.status)


@router.post(
    "/url",
    response_model=ScanCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("30/minute")
async def detect_url(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    payload: UrlDetectRequest,
):
    sub = get_or_create_subscription(db, user.id)
    source = _enforce_quota(db, user, sub)

    scan = Scan(
        user_id=user.id,
        scan_type=ScanType.URL,
        status=ScanStatus.QUEUED,
        source_url=str(payload.url),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    if source == "free":
        increment_usage(db, user.id)

    task = process_url_scan.delay(str(scan.id))
    scan.celery_task_id = task.id
    db.commit()
    return ScanCreatedResponse(scan_id=scan.id, status=scan.status)


@router.get("/{scan_id}", response_model=None)
async def get_scan(scan_id: uuid.UUID, db: DbSession, user: CurrentUser):
    scan = (
        db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user.id).first()
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    from app.schemas.detection import ScanOut

    return ScanOut.model_validate(scan)
