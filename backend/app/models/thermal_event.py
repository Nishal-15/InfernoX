from sqlalchemy import Column, String, Float, DateTime, Integer, func, UniqueConstraint
from geoalchemy2 import Geometry
from app.db.database import Base

class ThermalEvent(Base):
    __tablename__ = "thermal_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True, nullable=False)
    source_id = Column(String, index=True, nullable=True) # Optional provider ID
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # PostGIS Point geometry (SRID 4326 is WGS 84 standard for GPS)
    geometry = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False)
    
    detected_at = Column(DateTime(timezone=True), index=True, nullable=False) # When anomaly was detected
    acquired_at = Column(DateTime(timezone=True), nullable=True) # When data was acquired by satellite
    
    satellite = Column(String, index=True, nullable=False)
    instrument = Column(String, nullable=True)
    confidence = Column(Float, index=True, nullable=True) # Confidence % or value
    frp = Column(Float, nullable=True) # Fire Radiative Power
    brightness_temperature = Column(Float, nullable=True)
    day_night = Column(String, nullable=True) # 'D' or 'N'
    scan = Column(Float, nullable=True)
    track = Column(Float, nullable=True)
    status = Column(String, default="NEW", nullable=False, index=True) # NEW, INVESTIGATING, CONFIRMED, REJECTED, CLOSED
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('source', 'satellite', 'detected_at', 'latitude', 'longitude', name='_thermal_event_uc'),
    )
