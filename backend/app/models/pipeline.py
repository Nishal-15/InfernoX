from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from app.db.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class PipelineJob(Base):
    """
    Persistent record of an autonomous ingestion or processing job.
    Survives application restarts and tracks total execution progress,
    idempotent metrics, status, duration, and error traces.
    """
    __tablename__ = "pipeline_jobs"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(64), unique=True, nullable=False, index=True)
    job_type = Column(String(64), nullable=False, index=True)  # FIRMS_AUTONOMOUS_PIPELINE, DEMO_PIPELINE, MANUAL_STAGE_RETRY
    source = Column(String(64), nullable=False, default="NASA_FIRMS")
    status = Column(String(32), nullable=False, default="QUEUED", index=True)  # QUEUED, RUNNING, COMPLETED, PARTIAL, FAILED, RETRYING, CANCELLED
    
    records_received = Column(Integer, default=0, nullable=False)
    records_inserted = Column(Integer, default=0, nullable=False)
    records_skipped = Column(Integer, default=0, nullable=False)
    records_processed = Column(Integer, default=0, nullable=False)
    records_succeeded = Column(Integer, default=0, nullable=False)
    records_failed = Column(Integer, default=0, nullable=False)
    
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)


class PipelineStageRun(Base):
    """
    Granular execution tracking for every stage of an autonomous event pipeline.
    Allows independent stage-level retry and recovery without rerunning already completed stages.
    """
    __tablename__ = "pipeline_stage_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("pipeline_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("thermal_events.id", ondelete="CASCADE"), nullable=True, index=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    
    stage_name = Column(String(64), nullable=False, index=True)  # INGESTION, VALIDATION, ENRICHMENT, TEMPORAL_ANALYSIS, FEATURE_ENGINEERING, CLASSIFICATION, SATELLITE_EVALUATION, RISK_ASSESSMENT, INCIDENT_CORRELATION, ALERT_EVALUATION, NOTIFICATION
    status = Column(String(32), nullable=False, default="RUNNING", index=True)  # PENDING, RUNNING, SUCCESS, FAILED, SKIPPED, RETRYING
    
    is_transient_error = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Float, default=0.0, nullable=False)
    
    stage_output_json = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class FirmsIngestionState(Base):
    """
    Persistent state cursor for incremental FIRMS ingestion.
    Tracks last observation timestamp, bounding region, and run count
    to avoid repeatedly querying and processing already-ingested history.
    """
    __tablename__ = "firms_ingestion_state"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(64), unique=True, nullable=False, index=True)
    last_ingested_timestamp = Column(DateTime, nullable=True)
    bounding_box = Column(String(128), nullable=True)
    cursor_info = Column(String(256), nullable=True)
    last_run_status = Column(String(32), default="COMPLETED", nullable=False)
    total_runs = Column(Integer, default=0, nullable=False)
    total_records_ingested = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class AutonomousAuditLog(Base):
    """
    Comprehensive audit trail of autonomous machine intelligence operations.
    Maintains provenance for classifications, risk revisions, alert creation, and incident clustering.
    Distinguishes automated system changes from human analyst confirmations.
    """
    __tablename__ = "autonomous_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)  # AI_CLASSIFICATION_CREATED, RISK_CALCULATED, ALERT_CREATED, INCIDENT_UPDATED, etc.
    source = Column(String(64), default="AUTONOMOUS_PIPELINE", nullable=False)  # AUTONOMOUS_PIPELINE or ANALYST
    event_id = Column(Integer, nullable=True, index=True)
    incident_id = Column(Integer, nullable=True, index=True)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    model_version = Column(String(64), nullable=True)
    details_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
