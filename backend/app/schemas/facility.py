from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime

class FacilityBase(BaseModel):
    osm_id: str
    name: Optional[str] = None
    facility_type: Optional[str] = None
    latitude: float
    longitude: float
    operator: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    source: str = "OpenStreetMap"

class FacilityCreate(FacilityBase):
    pass

class FacilityOut(FacilityBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedFacilities(BaseModel):
    items: List[FacilityOut]
    total: int
    limit: int
    offset: int
