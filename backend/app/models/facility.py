from sqlalchemy import Column, String, Float, DateTime, Integer, func, UniqueConstraint # type: ignore
from sqlalchemy.dialects.postgresql import JSONB # type: ignore
from geoalchemy2 import Geometry # type: ignore
from app.db.database import Base

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String, index=True, nullable=False, unique=True)
    name = Column(String, nullable=True)
    facility_type = Column(String, index=True, nullable=True)
    
    # Coordinates for quick fallback, though PostGIS is primary
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # PostGIS Point geometry (SRID 4326)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False)
    
    operator = Column(String, nullable=True)
    tags = Column(JSONB, nullable=True) # Store raw OSM tags
    source = Column(String, nullable=False, default="OpenStreetMap")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
