from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class IngestionJobOut(BaseModel):
    id: int
    source: str
    status: str # RUNNING, COMPLETED, PARTIAL, FAILED
    records_received: int
    records_inserted: int
    records_skipped: int
    records_failed: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class IngestionStatusSummary(BaseModel):
    status: str
    last_attempt: Optional[datetime] = None
    last_successful_ingestion: Optional[datetime] = None
    records_fetched: int = 0
    records_inserted: int = 0
    records_rejected: int = 0
    error_state: Optional[str] = None
    latest_job: Optional[IngestionJobOut] = None
