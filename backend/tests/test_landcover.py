import pytest
from app.services.landcover.provider import WorldCoverProvider, PrototypeLandCoverProvider, WORLDCOVER_CLASSES

def test_worldcover_valid_coordinates():
    provider = WorldCoverProvider()
    
    # 1. Mumbai Industrial area
    res_mumbai = provider.get_land_cover(19.0, 72.85)
    assert res_mumbai is not None
    assert res_mumbai["land_cover_code"] == 50
    assert res_mumbai["land_cover_class"] == "Built-up"
    assert res_mumbai["land_cover_category"] == "INDUSTRIAL/BUILT"
    assert res_mumbai["tile_id"] == "N18E072"
    assert res_mumbai["is_prototype"] is False
    assert "ESA WorldCover" in res_mumbai["source"]

    # 2. Agricultural belt (Indo-Gangetic)
    res_punjab = provider.get_land_cover(30.0, 76.0)
    assert res_punjab is not None
    assert res_punjab["land_cover_code"] == 40
    assert res_punjab["land_cover_class"] == "Cropland"
    assert res_punjab["land_cover_category"] == "AGRICULTURE"

    # 3. Dense Forest (Western Ghats)
    res_forest = provider.get_land_cover(12.0, 75.5)
    assert res_forest is not None
    assert res_forest["land_cover_code"] == 10
    assert res_forest["land_cover_class"] == "Tree cover"
    assert res_forest["land_cover_category"] == "FOREST"

def test_worldcover_invalid_coordinates():
    provider = WorldCoverProvider()
    assert provider.get_land_cover(95.0, 50.0) is None
    assert provider.get_land_cover(-92.0, 10.0) is None
    assert provider.get_land_cover(20.0, 195.0) is None
    assert provider.get_land_cover(20.0, -185.0) is None

def test_worldcover_tile_id_calculation():
    # Tile boundaries are 3-degree multiples
    assert WorldCoverProvider.get_tile_id(19.1, 72.9) == "N18E072"
    assert WorldCoverProvider.get_tile_id(-12.5, -45.2) == "S15W048"
    assert WorldCoverProvider.get_tile_id(0.5, 0.5) == "N00E000"

def test_prototype_provider_preserved():
    proto = PrototypeLandCoverProvider()
    res = proto.get_land_cover(19.05, 72.9)
    assert res["is_prototype"] is True
    assert "Built-up" in res["class"]
