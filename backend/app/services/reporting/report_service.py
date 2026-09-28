from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session

from app.models.reporting import GeneratedReport
from app.schemas.reporting import ReportGenerateRequest, ReportDataPayload, ReportListItem
from app.services.reporting.report_builder import ReportBuilder
from app.services.reporting.report_export import ReportExportService


class ReportService:
    @staticmethod
    def generate_report(
        db: Session,
        request: ReportGenerateRequest,
        actor: str = "Analyst-01",
        organization_id: Optional[str] = None
    ) -> Tuple[ReportDataPayload, Union[bytes, str, Dict[str, Any]]]:
        """
        Build and optionally render report into requested format (PDF, CSV, GEOJSON, JSON).
        """
        rep_type = request.report_type.upper()
        target_id = request.target_id

        if rep_type == "INCIDENT":
            if not target_id:
                raise ValueError("Target Event ID is required for INCIDENT report")
            payload = ReportBuilder.build_incident_report(db, int(target_id))
        elif rep_type == "FACILITY":
            if not target_id:
                raise ValueError("Target Facility ID is required for FACILITY report")
            payload = ReportBuilder.build_facility_report(db, int(target_id), request.start_date, request.end_date)
        elif rep_type == "REGIONAL":
            reg_name = target_id or "National Monitored Corridor"
            payload = ReportBuilder.build_regional_report(db, reg_name, request.start_date, request.end_date)
        elif rep_type == "EXECUTIVE":
            payload = ReportBuilder.build_executive_report(db, request.start_date, request.end_date)
        else:
            raise ValueError(f"Unknown report type: {rep_type}")

        if request.title:
            payload.metadata.title = request.title

        # Persist report execution record
        rep_record = GeneratedReport(
            report_id=payload.metadata.report_id,
            report_type=payload.metadata.report_type,
            title=payload.metadata.title,
            target_id=target_id,
            parameters_json=request.model_dump(mode="json"),
            summary_json=payload.summary,
            provenance_json=payload.provenance.model_dump(mode="json"),
            format=request.format.upper(),
            organization_id=organization_id,
            created_at=datetime.now(timezone.utc),
            created_by=actor
        )
        db.add(rep_record)
        db.commit()
        db.refresh(rep_record)

        # Export according to format
        fmt = request.format.upper()
        if fmt == "PDF":
            rendered = ReportExportService.export_pdf(payload)
        elif fmt == "CSV":
            rendered = ReportExportService.export_csv(payload)
        elif fmt == "GEOJSON":
            rendered = ReportExportService.export_geojson(payload)
        else:  # JSON
            rendered = ReportExportService.export_json(payload)

        return payload, rendered

    @staticmethod
    def list_reports(
        db: Session,
        limit: int = 50,
        report_type: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> List[ReportListItem]:
        """
        List previously generated and persisted reports.
        Filters by organization_id if provided (allowing global reports with organization_id=None).
        """
        query = db.query(GeneratedReport)
        if report_type:
            query = query.filter(GeneratedReport.report_type == report_type.upper())
        if organization_id:
            query = query.filter(
                (GeneratedReport.organization_id == organization_id) |
                (GeneratedReport.organization_id == None)
            )
        records = query.order_by(GeneratedReport.created_at.desc()).limit(limit).all()

        return [
            ReportListItem(
                id=r.id,
                report_id=r.report_id,
                report_type=r.report_type,
                title=r.title,
                target_id=r.target_id,
                format=r.format,
                created_at=r.created_at.isoformat() if r.created_at else "",
                created_by=r.created_by
            )
            for r in records
        ]
