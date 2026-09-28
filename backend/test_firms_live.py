import os
import asyncio
import httpx

MAP_KEY = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")
BASE_URL = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api")

async def test_endpoints():
    async with httpx.AsyncClient(timeout=20.0) as client:
        # Test 1: Country endpoint (IND, 1 day)
        url_country = f"{BASE_URL}/country/csv/{MAP_KEY}/VIIRS_SNPP_NRT/IND/1"
        print(f"Testing Country endpoint: .../country/csv/***REDACTED***/VIIRS_SNPP_NRT/IND/1")
        try:
            r = await client.get(url_country)
            print(f"Country Status: {r.status_code}, Length: {len(r.text)}")
            print("First 3 lines:\n", "\n".join(r.text.splitlines()[:3]))
        except Exception as e:
            print("Country Error:", e)

        # Test 2: Area endpoint (68,7,97,36, 1 day)
        url_area = f"{BASE_URL}/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/68,7,97,36/1"
        print(f"\nTesting Area endpoint: .../area/csv/***REDACTED***/VIIRS_SNPP_NRT/68,7,97,36/1")
        try:
            r2 = await client.get(url_area)
            print(f"Area Status: {r2.status_code}, Length: {len(r2.text)}")
            print("First 3 lines:\n", "\n".join(r2.text.splitlines()[:3]))
        except Exception as e:
            print("Area Error:", e)

        # Test 3: VIIRS_NOAA20_NRT (Country IND, 1 day)
        url_n20 = f"{BASE_URL}/country/csv/{MAP_KEY}/VIIRS_NOAA20_NRT/IND/1"
        print(f"\nTesting NOAA-20 Country endpoint: .../country/csv/***REDACTED***/VIIRS_NOAA20_NRT/IND/1")
        try:
            r3 = await client.get(url_n20)
            print(f"NOAA-20 Status: {r3.status_code}, Length: {len(r3.text)}")
            print("First 3 lines:\n", "\n".join(r3.text.splitlines()[:3]))
        except Exception as e:
            print("NOAA-20 Error:", e)

        # Test 4: VIIRS_NOAA21_NRT (Country IND, 1 day)
        url_n21 = f"{BASE_URL}/country/csv/{MAP_KEY}/VIIRS_NOAA21_NRT/IND/1"
        print(f"\nTesting NOAA-21 Country endpoint: .../country/csv/***REDACTED***/VIIRS_NOAA21_NRT/IND/1")
        try:
            r4 = await client.get(url_n21)
            print(f"NOAA-21 Status: {r4.status_code}, Length: {len(r4.text)}")
            print("First 3 lines:\n", "\n".join(r4.text.splitlines()[:3]))
        except Exception as e:
            print("NOAA-21 Error:", e)

asyncio.run(test_endpoints())
