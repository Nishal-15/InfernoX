import pytest
from datetime import datetime, timezone
from app.services.satellite.provider import Sentinel2Provider

def test_sentinel2_spectral_indices_calculation():
    # Test physical formula calculation
    # NDVI = (NIR - Red) / (NIR + Red) = (0.28 - 0.12) / (0.28 + 0.12) = 0.16 / 0.40 = 0.40
    # NBR = (NIR - SWIR2) / (NIR + SWIR2) = (0.28 - 0.18) / (0.28 + 0.18) = 0.10 / 0.46 = 0.217
    # NDWI = (Green - NIR) / (Green + NIR) = (0.10 - 0.28) / (0.10 + 0.28) = -0.18 / 0.38 = -0.474
    # SWIR2/NIR ratio = 0.18 / 0.28 = 0.643
    spectral = Sentinel2Provider._calculate_spectral_indices(
        red=0.12, green=0.10, blue=0.08,
        nir=0.28, swir1=0.22, swir2=0.18
    )
    indices = spectral["indices"]
    assert indices["ndvi"] == 0.4
    assert indices["nbr"] == 0.217
    assert indices["ndwi"] == -0.474
    assert indices["swir_nir_ratio"] == 0.643
    assert spectral["burn_scar_indicator"] is False

def test_sentinel2_burn_scar_detection():
    # Severe burn scar: depressed NBR (< 0.10)
    spectral = Sentinel2Provider._calculate_spectral_indices(
        red=0.20, green=0.15, blue=0.10,
        nir=0.18, swir1=0.35, swir2=0.30 # High SWIR, low NIR
    )
    indices = spectral["indices"]
    assert indices["nbr"] < 0.10
    assert spectral["burn_scar_indicator"] is True

def test_sentinel2_cloud_cover_rejection():
    provider = Sentinel2Provider()
    now = datetime.now(timezone.utc)
    
    # Query with strict 0.01% cloud cover threshold -> should trigger rejection
    result = provider.search_imagery(
        latitude=19.0,
        longitude=72.8,
        target_time=now,
        max_cloud_cover=0.001
    )
    assert result["satellite_evidence_available"] is False
    assert "Cloud cover" in result["rejection_reason"]
    assert result["indices"] is None

def test_sentinel2_scene_retrieval():
    provider = Sentinel2Provider()
    now = datetime.now(timezone.utc)
    
    result = provider.search_imagery(
        latitude=19.0,
        longitude=72.8,
        target_time=now,
        max_cloud_cover=50.0
    )
    assert "scene_id" in result
    assert result["provider"] == "ESA Copernicus Sentinel-2 MSI"
    assert "indices" in result
