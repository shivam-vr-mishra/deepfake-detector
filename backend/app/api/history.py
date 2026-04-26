"""History + scan-result endpoints."""
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.deps import CurrentUser, DbSession
from app.models.scan import Scan, ScanType
from app.schemas.detection import ScanOut
from app.services.pdf_report import generate_scan_report

router = APIRouter(tags=["history"])


@router.get("/history", response_model=List[ScanOut])
def list_history(
    db: DbSession,
    user: CurrentUser,
    scan_type: ScanType | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    q = db.query(Scan).filter(Scan.user_id == user.id)
    if scan_type:
        q = q.filter(Scan.scan_type == scan_type)
    rows = q.order_by(Scan.created_at.desc()).offset(offset).limit(limit).all()
    return [ScanOut.model_validate(r) for r in rows]


@router.get("/report/{scan_id}")
def download_report(scan_id: uuid.UUID, db: DbSession, user: CurrentUser):
    scan = (
        db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user.id).first()
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    pdf = generate_scan_report(scan)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="scan-{scan.id}.pdf"'
        },
    )
