from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ThermalEventBase(BaseModel):
    source: str
    latitude: float
    longitude: float
    detected_at: datetime
    satellite: str
    confidence: Optional[float] = None
    frp: Optional[float] = None
    brightness_temperature: Optional[float] = None
    status: Optional[str] = "NEW"

class ThermalEventCreate(ThermalEventBase):
    acquired_at: Optional[datetime] = None
    instrument: Optional[str] = None
    day_night: Optional[str] = None
    scan: Optional[float] = None
    track: Optional[float] = None

class ThermalEventOut(ThermalEventBase):
    id: int
    acquired_at: Optional[datetime] = None
    instrument: Optional[str] = None
    day_night: Optional[str] = None
    scan: Optional[float] = None
    track: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedThermalEvents(BaseModel):
    items: List[ThermalEventOut]
    total: int
    limit: int
    offset: int
