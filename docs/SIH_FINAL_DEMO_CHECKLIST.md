# InfernoX — SIH Final Live Demonstration Checklist

**Release Target:** Smart India Hackathon (SIH) Live Jury Presentation  
**System:** InfernoX AI-Based Industrial Fire & Persistent Thermal Source Intelligence Platform  
**Architecture:** Multimodal Geospatial Intelligence Pipeline  

---

## BEFORE DEMO

- [ ] **Docker Engine Running**: Verify Docker daemon / Docker Desktop is active if running full PostGIS container.
- [ ] **Database Connectivity**: Verify PostgreSQL/PostGIS is accepting connections (`GET /api/v1/system/health`).
- [ ] **Backend Health**: Verify FastAPI backend responds HTTP 200 on `http://localhost:8000/api/v1/health`.
- [ ] **Frontend Application**: Verify Next.js 14 is running on `http://localhost:3000` with 0 console errors.
- [ ] **FIRMS Credentials Status**:
  - If live API key is available: Verify `FIRMS_MAP_KEY` is present in `.env` and `GET /api/v1/system/providers/firms` displays `LIVE`.
  - If live key is unavailable: Confirm UI explicitly displays `HISTORICAL ARCHIVE` / `DEMO MODE` (no fabricated live points).
- [ ] **Cesium Ion Token**:
  - If token present: 3D Cesium World Terrain and photogrammetry tiles active.
  - If token absent: Ellipsoidal 3D globe with OpenStreetMap base imagery active.
- [ ] **Historical Archive**: Verify historical FIRMS CSV directory (`backend/data/historical/firms/`) is accessible (2024–2026 archives).
- [ ] **Controlled Demo Mode**: Test anomaly injection via `POST /api/v1/system/demo/trigger` or via the top-bar SIH Demo controller.
- [ ] **WebSocket Stream**: Verify green pulse on `LIVE ●` pill in the header and real-time connectivity to `/api/v1/ws/stream`.
- [ ] **Dossier & Report Studio**: Test PDF and CSV export in the Dossier Studio tab (`POST /api/v1/reports/generate`).
- [ ] **Browser Console Clean**: Inspect browser devtools to verify zero uncaught exceptions or hydration mismatches.

---

## DURING DEMO (14-STEP INVESTIGATION WALKTHROUGH)

1. **Show Mission Control (Cesium 3D Globe)**:
   - Present the global ellipsoidal globe, layer toggles (FIRMS, Facilities, Land Cover, Heatmap), and HUD status bar.
   - Explain why raw NASA FIRMS alone is insufficient (point-in-time sensor data without facility context or temporal memory).
2. **Show Thermal Detection**:
   - Select an active VIIRS detection (e.g., Jamnagar Refinery or Paradip Petrochemicals).
   - Point out sensor parameters: FRP (MW), Brightness Temperature (K), satellite source (`VIIRS_SNPP_NRT`), and confidence.
3. **Open Event Dossier**:
   - Expand the right-hand inspection drawer showing the consolidated intelligence dossier.
4. **Show Industrial Facility Context**:
   - Highlight the OpenStreetMap industrial proximity card: Geodesic ellipsoidal distance (`ST_DWithin` / `ST_Distance`) to nearest high-hazard infrastructure.
5. **Show Land Cover Attribution**:
   - Display ESA WorldCover 10m land cover class (`INDUSTRIAL/BUILT` vs `FOREST` vs `AGRICULTURE`).
6. **Show Temporal Persistence & Dynamics**:
   - Open the 90-day lookback timeline.
   - Demonstrate the stationary flare signature (<150m spread) vs spreading wildfire.
   - Show rolling FRP baseline and abnormal spike transition (`ABNORMAL >= 2.5x mean`).
7. **Show Sentinel-2 Spectral Evidence**:
   - Highlight Level-2A surface reflectance data queried via public STAC API.
   - Show NDVI (vegetation degradation), NBR (burn scar indicator), and SWIR2/NIR combustion ratio.
8. **Show Machine Learning Classification**:
   - Present the calibrated XGBoost prediction (`GAS_FLARE`, `INDUSTRIAL_FIRE`, `WILDFIRE`, etc.) across the 6 operational classes.
9. **Show AI Feature Importance & Explainability**:
   - Review top contributing feature weights explaining why the model classified the event (e.g., proximity to flare stack + high persistence).
10. **Show Deterministic 0–100 Risk Score**:
    - Walk through the explainable 5-factor scoring breakdown (Classification 35%, FRP 25%, Temporal 20%, Proximity 15%, Satellite 5%).
    - Show the assigned 4-tier risk level (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`).
11. **Show Incident Correlation**:
    - Demonstrate how detections within 1.5 km and 48 hours group into a single incident (`INC-2026-XXXXXX`), preventing alert storms.
12. **Show Active Alert Center & Response Routing**:
    - Open the Alert Center tab.
    - Show 60-minute anti-storm cooldown and recommended authority response routing.
    - Demonstrate analyst triage actions (`Acknowledge`, `Investigate`, `Escalate`, `Resolve`).
13. **Show Cesium 3D Investigation Flight**:
    - Click "Fly To" to demonstrate smooth WebGL camera interpolation directly to the anomaly coordinates with 3D pulsing risk rings.
14. **Show Intelligence Dossier Report Generation**:
    - Open the Dossier Studio tab.
    - Generate and download a publication-grade PDF and CSV incident report with data provenance.

---

## AFTER DEMO

- [ ] **No Secrets Exposed**: Confirm `FIRMS_MAP_KEY`, database passwords, and JWT secrets were never logged or visible in UI.
- [ ] **Data Transparency Maintained**: Verify demo and historical data were transparently badged and never presented as unverified live telemetry.
- [ ] **API Keys Protected**: Confirm client-side bundles contain no server secrets.
- [ ] **Audit Trail Preserved**: Review `AutonomousAuditLog` and `PlatformAuditLog` to confirm every action was recorded with correlation IDs.
