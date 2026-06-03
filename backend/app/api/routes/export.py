"""
export.py — Data export routes (CSV)

All export endpoints return CSV files for download.
Exports are authenticated and limited to the user's own data.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["export"])


def _csv_response(csv_content: str, filename: str) -> Response:
    """Return a streaming CSV download response."""
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/export/drafts",
    summary="Export saved drafts as CSV",
    description="Download all saved draft history as a CSV file.",
)
async def export_drafts(
    request: Request,
    limit: int = Query(default=500, ge=1, le=2000),
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    service = ExportService(db)
    csv_content = await service.export_drafts_csv(limit=limit)
    tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    return _csv_response(csv_content, f"lea_drafts_{tag}.csv")


@router.get(
    "/export/engagement",
    summary="Export engagement metrics as CSV",
    description="Download engagement prediction history as a CSV file.",
)
async def export_engagement(
    request: Request,
    limit: int = Query(default=500, ge=1, le=2000),
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    service = ExportService(db)
    csv_content = await service.export_engagement_csv(limit=limit)
    tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    return _csv_response(csv_content, f"lea_engagement_{tag}.csv")


@router.get(
    "/export/ab-tests",
    summary="Export A/B test records as CSV",
    description="Download post variation A/B test history as a CSV file.",
)
async def export_ab_tests(
    request: Request,
    limit: int = Query(default=500, ge=1, le=2000),
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    service = ExportService(db)
    csv_content = await service.export_ab_tests_csv(limit=limit)
    tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    return _csv_response(csv_content, f"lea_ab_tests_{tag}.csv")
