from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
from app.schemas.thermal_event import ThermalEventCreate
from app.core.config import settings

logger = logging.getLogger(__name__)

class FirmsNormalizer:
    def _parse_datetime(self, acq_date: str, acq_time: str) -> Optional[datetime]:
        try:
            # acq_time is often 3 or 4 digits: e.g., '350' -> '0350'
            padded_time = acq_time.zfill(4)
            dt_str = f"{acq_date} {padded_time}"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H%M")
            return dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to parse datetime {acq_date} {acq_time}: {e}")
            return None

    def normalize(self, record: Dict[str, Any]) -> ThermalEventCreate:
        """
        Normalizes a FIRMS CSV row into our internal ThermalEventCreate schema.
        """
        acq_date = record.get('acq_date', '')
        acq_time = record.get('acq_time', '')
        detected_at = self._parse_datetime(acq_date, acq_time) or datetime.now(timezone.utc)
        
        # Parse numeric fields safely
        def safe_float(val, default=None):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default

        # Confidence can be 'l', 'n', 'h' in some VIIRS or numeric 0-100 in MODIS.
        conf_str = str(record.get('confidence', '')).lower()
        confidence_val = None
        if conf_str in ['l', 'low']: confidence_val = 33.0
        elif conf_str in ['n', 'nominal']: confidence_val = 66.0
        elif conf_str in ['h', 'high']: confidence_val = 100.0
        else:
            confidence_val = safe_float(record.get('confidence'))

        return ThermalEventCreate(
            source="NASA_FIRMS",
            latitude=safe_float(record.get('latitude', 0)),
            longitude=safe_float(record.get('longitude', 0)),
            detected_at=detected_at,
            acquired_at=detected_at,
            satellite=record.get('satellite', 'UNKNOWN'),
            instrument=record.get('instrument'),
            confidence=confidence_val,
            frp=safe_float(record.get('frp')),
            brightness_temperature=safe_float(record.get('bright_ti4', record.get('brightness'))),
            day_night=record.get('daynight'),
            scan=safe_float(record.get('scan')),
            track=safe_float(record.get('track'))
        )
