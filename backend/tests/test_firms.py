import pytest
from app.services.firms.parser import FirmsParser
from app.services.firms.validator import FirmsValidator
from app.services.firms.normalizer import FirmsNormalizer

def test_parser_valid_csv():
    parser = FirmsParser()
    csv_data = "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n39.8,-100.2,300.5,1.0,1.0,2026-09-01,1230,Aqua,MODIS,75,6.1,290.0,15.5,D"
    records = parser.parse_csv(csv_data)
    assert len(records) == 1
    assert records[0]['latitude'] == '39.8'
    assert records[0]['satellite'] == 'Aqua'

def test_parser_malformed_csv():
    parser = FirmsParser()
    csv_data = "latitude,longitude\n39.8\n" # Missing column
    records = parser.parse_csv(csv_data)
    assert len(records) == 1
    assert records[0]['longitude'] == None

def test_validator_valid_record():
    validator = FirmsValidator()
    record = {
        'latitude': '39.8',
        'longitude': '-100.2',
        'acq_date': '2026-09-01',
        'acq_time': '1230',
        'satellite': 'Aqua'
    }
    is_valid, reason = validator.validate(record)
    assert is_valid is True

def test_validator_invalid_coordinates():
    validator = FirmsValidator()
    record = {
        'latitude': '95.0', # Invalid > 90
        'longitude': '-100.2',
        'acq_date': '2026-09-01',
        'acq_time': '1230',
        'satellite': 'Aqua'
    }
    is_valid, reason = validator.validate(record)
    assert is_valid is False
    assert "Invalid latitude" in reason

def test_normalizer():
    normalizer = FirmsNormalizer()
    record = {
        'latitude': '39.8',
        'longitude': '-100.2',
        'acq_date': '2026-09-01',
        'acq_time': '1230',
        'satellite': 'Aqua',
        'confidence': '75',
        'frp': '15.5',
        'bright_ti4': '300.5'
    }
    normalized = normalizer.normalize(record)
    assert normalized.source == "NASA_FIRMS"
    assert normalized.latitude == 39.8
    assert normalized.longitude == -100.2
    assert normalized.satellite == "Aqua"
    assert normalized.confidence == 75.0
    assert normalized.frp == 15.5
    assert normalized.brightness_temperature == 300.5
