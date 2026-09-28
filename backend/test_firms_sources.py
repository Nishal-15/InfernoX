import os
import asyncio
import httpx

MAP_KEY = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")
BASE_URL = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api")
AREA = os.getenv("FIRMS_AREA", "68,7,97,36")

sources = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT"
]

async def test_sources():
    async with httpx.AsyncClient(timeout=20.0) as client:
        for s in sources:
            url = f"{BASE_URL}/area/csv/{MAP_KEY}/{s}/{AREA}/1"
            try:
                r = await client.get(url)
                print(f"Source: {s:20} -> Status: {r.status_code}, Length: {len(r.text)}, First line: {r.text.splitlines()[0] if r.text else 'EMPTY'}")
                if len(r.text.splitlines()) > 1:
                    print(f"   Record sample: {r.text.splitlines()[1]}")
            except Exception as e:
                print(f"Source {s} error: {e}")

asyncio.run(test_sources())
