from typing import Dict, Any, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FirmsValidator:
    def validate(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates a single FIRMS record.
        Returns (is_valid, error_reason).
        """
        try:
            # Check coordinates
            lat = float(record.get('latitude', 0))
            lon = float(record.get('longitude', 0))
            if not (-90 <= lat <= 90):
                return False, f"Invalid latitude: {lat}"
            if not (-180 <= lon <= 180):
                return False, f"Invalid longitude: {lon}"

            # Check timestamp
            acq_date = record.get('acq_date')
            acq_time = record.get('acq_time')
            if not acq_date or not acq_time:
                return False, "Missing acquisition date/time"
                
            # Date format usually YYYY-MM-DD, Time is HHMM or HMM
            # Just verify they are strings
            if not isinstance(acq_date, str) or not isinstance(acq_time, str):
                return False, "Invalid date/time format"

            # Check required satellite info
            if 'satellite' not in record:
                return False, "Missing satellite field"

            return True, ""
        except ValueError as e:
            return False, f"Value error: {str(e)}"
        except Exception as e:
            logger.error(f"Validation exception: {e}")
            return False, "Internal validation error"
