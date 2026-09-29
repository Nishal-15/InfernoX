import re
from typing import Dict, Any, Tuple, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Valid bounding ranges for earth observation satellites
LAT_RANGE = (-90.0, 90.0)
LON_RANGE = (-180.0, 180.0)
FRP_RANGE = (0.0, 15000.0)  # Fire Radiative Power in MW (sensible upper limit for terrestrial events)
BRIGHTNESS_RANGE = (180.0, 650.0)  # Brightness temperature in Kelvin
SCAN_TRACK_RANGE = (0.1, 10.0)  # Spatial resolution footprint bounds in km

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{3,4}$|^\d{1,2}:\d{2}$")

class FirmsValidator:
    """
    Production-grade FIRMS observation validator.
    Enforces physical observation limits, spatial boundaries, and temporal consistency.
    """

    def validate_with_flags(self, record: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validates a single FIRMS record with fine-grained quality flags.
        Returns:
            is_valid (bool): Whether record meets minimum acceptance criteria.
            rejection_reasons (List[str]): List of fatal validation failures if invalid.
            quality_flags (Dict[str, Any]): Non-fatal warnings and physical sanity tags.
        """
        rejection_reasons: List[str] = []
        quality_flags: Dict[str, Any] = {
            "is_null_island": False,
            "extreme_frp": False,
            "high_brightness": False,
            "low_confidence": False,
            "night_observation": False,
            "sanitized": False,
        }

        try:
            # 1. Coordinate Validation
            if "latitude" not in record or "longitude" not in record:
                rejection_reasons.append("Missing latitude or longitude")
                return False, rejection_reasons, quality_flags

            try:
                lat = float(record["latitude"])
                lon = float(record["longitude"])
            except (ValueError, TypeError):
                rejection_reasons.append(f"Non-numeric coordinates: lat={record.get('latitude')}, lon={record.get('longitude')}")
                return False, rejection_reasons, quality_flags

            if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1]):
                rejection_reasons.append(f"Invalid latitude: {lat} outside valid range [{LAT_RANGE[0]}, {LAT_RANGE[1]}]")
            if not (LON_RANGE[0] <= lon <= LON_RANGE[1]):
                rejection_reasons.append(f"Invalid longitude: {lon} outside valid range [{LON_RANGE[0]}, {LON_RANGE[1]}]")


            # Null island check (0.0, 0.0) - almost always GPS/processing failure in terrestrial fire monitoring
            if abs(lat) < 1e-5 and abs(lon) < 1e-5:
                quality_flags["is_null_island"] = True
                rejection_reasons.append("Coordinates at Null Island (0.0, 0.0) indicate sensor or projection error")

            # 2. Temporal Validation
            acq_date = str(record.get("acq_date", "")).strip()
            acq_time = str(record.get("acq_time", "")).strip()

            if not acq_date or not acq_time:
                rejection_reasons.append("Missing acquisition date or time")
            else:
                if not DATE_PATTERN.match(acq_date):
                    rejection_reasons.append(f"Invalid acquisition date format '{acq_date}' (expected YYYY-MM-DD)")
                if not TIME_PATTERN.match(acq_time):
                    rejection_reasons.append(f"Invalid acquisition time format '{acq_time}' (expected HHMM)")

            # 3. Satellite & Instrument Verification
            satellite = record.get("satellite")
            if not satellite or not str(satellite).strip():
                rejection_reasons.append("Missing satellite platform identification")

            # 4. Physical Observables Validation (FRP & Brightness)
            if "frp" in record and record["frp"] is not None and str(record["frp"]).strip() != "":
                try:
                    frp = float(record["frp"])
                    if frp < FRP_RANGE[0]:
                        rejection_reasons.append(f"Negative Fire Radiative Power (FRP): {frp} MW")
                    elif frp > FRP_RANGE[1]:
                        rejection_reasons.append(f"Unphysical FRP {frp} MW exceeds absolute terrestrial maximum {FRP_RANGE[1]} MW")
                    elif frp > 1000.0:
                        quality_flags["extreme_frp"] = True
                except (ValueError, TypeError):
                    rejection_reasons.append(f"Non-numeric FRP value: {record['frp']}")

            if "brightness" in record and record["brightness"] is not None and str(record["brightness"]).strip() != "":
                try:
                    brightness = float(record["brightness"])
                    if not (BRIGHTNESS_RANGE[0] <= brightness <= BRIGHTNESS_RANGE[1]):
                        rejection_reasons.append(
                            f"Brightness temperature {brightness} K outside physical bounds [{BRIGHTNESS_RANGE[0]}, {BRIGHTNESS_RANGE[1]}]"
                        )
                    elif brightness > 450.0:
                        quality_flags["high_brightness"] = True
                except (ValueError, TypeError):
                    rejection_reasons.append(f"Non-numeric brightness temperature: {record['brightness']}")

            # 5. Scan / Track Geometry Footprint
            for field in ("scan", "track"):
                if field in record and record[field] is not None and str(record[field]).strip() != "":
                    try:
                        val = float(record[field])
                        if not (SCAN_TRACK_RANGE[0] <= val <= SCAN_TRACK_RANGE[1]):
                            rejection_reasons.append(f"Spatial footprint '{field}' value {val} out of bounds {SCAN_TRACK_RANGE}")
                    except (ValueError, TypeError):
                        rejection_reasons.append(f"Non-numeric footprint '{field}': {record[field]}")

            # 6. Day / Night Flagging
            dn = str(record.get("daynight", "")).upper().strip()
            if dn == "N":
                quality_flags["night_observation"] = True

            # 7. Confidence Rating
            conf = record.get("confidence")
            if conf is not None and str(conf).strip() != "":
                try:
                    conf_num = float(conf)
                    if conf_num < 30.0:
                        quality_flags["low_confidence"] = True
                except ValueError:
                    if str(conf).lower() == "l":
                        quality_flags["low_confidence"] = True

            is_valid = len(rejection_reasons) == 0
            return is_valid, rejection_reasons, quality_flags

        except Exception as e:
            logger.error(f"Unexpected validation exception: {e}", exc_info=True)
            return False, [f"Internal validator error: {str(e)}"], quality_flags

    def validate(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Backwards-compatible single-error signature for existing pipeline calls.
        Returns (is_valid, error_reason).
        """
        is_valid, reasons, _ = self.validate_with_flags(record)
        if is_valid:
            return True, ""
        return False, "; ".join(reasons)

