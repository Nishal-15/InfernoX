from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.reporting import (
    ReportGenerateRequest,
    ReportDataPayload,
    ReportListItem
)
from app.services.reporting.report_service import ReportService
from app.services.reporting.report_builder import ReportBuilder
from app.services.reporting.report_export import ReportExportService

router = APIRouter()


@router.post("/generate")
def generate_report(
    request: ReportGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate an intelligence report and return either JSON payload or binary file (PDF/CSV/GeoJSON).
    """
    try:
        payload, rendered = ReportService.generate_report(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fmt = request.format.upper()
    if fmt == "PDF":
        filename = f"{payload.metadata.report_id}.pdf"
        return Response(
            content=rendered,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif fmt == "CSV":
        filename = f"{payload.metadata.report_id}.csv"
        return Response(
            content=rendered,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif fmt == "GEOJSON":
        return rendered
    else:  # JSON
        return payload


@router.get("/incident/{event_id}", response_model=ReportDataPayload)
def get_incident_report(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get incident investigation report payload for a specific thermal event.
    """
    try:
        return ReportBuilder.build_incident_report(db, event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/facility/{facility_id}", response_model=ReportDataPayload)
def get_facility_report(
    facility_id: int,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get facility thermal intelligence report payload.
    """
    try:
        return ReportBuilder.build_facility_report(db, facility_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/executive", response_model=ReportDataPayload)
def get_executive_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get executive intelligence summary briefing.
    """
    return ReportBuilder.build_executive_report(db, start_date=start_date, end_date=end_date)


@router.get("/regional", response_model=ReportDataPayload)
def get_regional_report(
    region_name: str = Query("National Monitored Corridor"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get regional intelligence assessment report.
    """
    return ReportBuilder.build_regional_report(db, region_name=region_name, start_date=start_date, end_date=end_date)


@router.get("/history", response_model=List[ReportListItem])
def list_report_history(
    limit: int = Query(50, ge=1, le=100),
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List previously generated reports.
    """
    return ReportService.list_reports(db, limit=limit, report_type=report_type)
