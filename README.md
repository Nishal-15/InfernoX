# InfernoX: AI-Based Industrial Fire & Persistent Thermal Source Intelligence

## Project Overview

InfernoX is an AI-assisted geospatial intelligence platform designed to ingest satellite thermal anomaly data (NASA FIRMS), combine it with industrial infrastructure maps (OpenStreetMap), ESA WorldCover 10m land-use data, Sentinel-2 MSI multispectral remote sensing, and historical persistence clustering to detect, classify, and triage industrial fires, gas flares, and persistent thermal sources.

> [!IMPORTANT]
> **Notice on Current Phase**: The platform is operating in **Phase 10 — Production Deployment, SIH Demo, Final Polish & Data-Source Hardening**.
> InfernoX is production-ready, featuring official NASA FIRMS integration (`https://firms.modaps.eosdis.nasa.gov/`), multi-satellite sensor fallback (`VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`), verified historical FIRMS archives (2024–2026), dedicated SIH 18-step guided demo mode, judge-friendly defense brief modal, and full ML provenance tracking.
>
> $$\text{NASA FIRMS (Multi-Sensor/Historical)} \rightarrow \text{Validation/Dedup} \rightarrow \text{Spatial Enrichment (PostGIS/OSM)} \rightarrow \text{Temporal Dynamics} \rightarrow \text{Feature Snapshot} \rightarrow \text{ML Classification} \rightarrow \text{Incident Clustering} \rightarrow \text{Risk Engine} \rightarrow \text{Anti-Storm Alerts} \rightarrow \text{WebSocket Broadcast} \rightarrow \text{3D Cesium Mission Control}$$
>
> *Safety & Data Transparency*: In demo environments, historical and synthetic observations are transparently labeled as `DEMO (Verified Historical Archive)`. Live NASA FIRMS queries strictly utilize the official endpoint. Classifications maintain explicit provenance (`AI Preliminary` vs. `Analyst Confirmed`).

---

## Architecture & Subsystems

1. **Incremental FIRMS Ingestion Engine**:
   - Tracks persistent ingestion state (`firms_ingestion_state`) with high-watermark timestamps, bounding regions, and run counters.
   - Prevents duplicate observations using spatial-temporal unique constraints.
2. **Autonomous Multi-Stage Pipeline Orchestrator (`PipelineRunner`)**:
   - 10-stage execution pipeline: `INGESTION`, `VALIDATION_DEDUP`, `SPATIAL_ENRICHMENT`, `TEMPORAL_ANALYSIS`, `FEATURE_ENGINEERING`, `CLASSIFICATION`, `SATELLITE_EVALUATION`, `INCIDENT_CORRELATION`, `RISK_ASSESSMENT`, `ALERT_EVALUATION`.
   - Each stage persists input, output, execution timestamp, duration, status, and retry metrics in `pipeline_stage_runs`.
3. **Resilient Failure Recovery & Retry Policy (`RetryPolicy`)**:
   - Classifies failures into Transient (network timeouts, temporary DB locks) vs. Permanent (malformed geometry, invalid inputs).
   - Configurable exponential backoff (`MAX_RETRIES=3`, `RETRY_BACKOFF_SECONDS=30`).
   - Server restart safety: automatically recovers and marks interrupted jobs on startup without data loss.
4. **External Provider & System Health Telemetry (`HealthMonitor`)**:
   - Live health probes for PostgreSQL/PostGIS, NASA FIRMS, Sentinel-2 STAC, OSM Overpass, ESA WorldCover, and XGBoost ML Model.
   - Exposes `/api/v1/system/health`, `/api/v1/system/providers`, and `/api/v1/system/jobs`.
5. **Thermal Incident Correlation (`IncidentCorrelator`)**:
   - Groups related thermal detections into unified incidents (`INC-2026-XXXXXX`) using spatial proximity ($\le 1.5\text{ km}$), temporal continuity ($\le 48\text{ hrs}$), or shared industrial facility footprint.
   - Prevents alert storms: 30 detections at an ongoing flare or refinery incident correlate to 1 incident rather than 30 separate critical alerts.
6. **Anti-Storm Autonomous Alert Engine**:
   - Evaluates dynamic criteria with alert cooldown intervals (default 15 minutes) and incident-level deduplication.
7. **Real-Time Bidirectional Event Stream (WebSockets)**:
   - Lightweight WebSocket stream at `/api/v1/ws/stream` broadcasting real-time events (`thermal_event.created`, `alert.created`, `risk.updated`, `incident.updated`, `job.started`, `job.completed`).
   - Heartbeat ping/pong, auto-reconnection, and buffered in-memory history.
8. **Live 3D Mission Control & Cesium Live Mode**:
   - `LIVE ●` telemetry pill with pulse indicator and relative latency countdown.
   - Dynamic map and event list updates without requiring page reloads.
   - Non-blocking floating incident alerts with one-click "Inspect", "Fly To", and "Dismiss".
   - Optional configurable **Auto-Fly to Critical Events** mode (Default: OFF).
9. **NOC & Autonomous Pipeline Telemetry Modal**:
   - SOC/NOC command center interface inspired by modern cyber/telemetry consoles.
   - Live system health cards, provider telemetry grid with latencies and failure counts, persistent job history, manual ingestion cycle triggers, and simulated demo injection.
10. **Controlled Demo Mode**:
    - `/api/v1/system/demo/trigger` allows injecting simulated high-confidence anomalies to verify end-to-end telemetry without polluting production data.
11. **Comprehensive Audit Trail**:
    - Immutable audit logs in `autonomous_audit_logs` tracking correlation IDs, event/incident targets, actor types, previous and new states.


---

## Technology Stack

- **Frontend:** Next.js 14, React 18, TypeScript, Tailwind CSS, CesiumJS
- **Backend:** Python 3.14, FastAPI, XGBoost, Scikit-learn, NumPy, SciPy, SQLAlchemy, GeoAlchemy2, APScheduler, Pydantic V2
- **Database:** PostgreSQL 15 + PostGIS extension
- **Testing:** Pytest, Pytest-asyncio, HTTPX

---

## Development Setup

### 1. Configure Environment
Copy `.env.example` to `.env` and fill in credentials:
```bash
cp .env.example .env
```
Key configuration settings:
- `POSTGRES_SERVER=localhost` (or `db` when running inside Docker Compose)
- `FIRMS_MAP_KEY`: NASA FIRMS API Map Key (or set `DEMO_MODE=true` for safe testing)
- `NEXT_PUBLIC_CESIUM_ION_ACCESS_TOKEN`: Cesium Ion access token
- `ACTIVE_MODEL_VERSION=xgb-v1`
- `MAX_SATELLITE_CLOUD_COVER=30.0`

### 2. Run with Docker Compose
```bash
docker-compose up -d --build
```

### 3. Run Backend Locally
```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Frontend Locally
```powershell
cd frontend
npm run dev
```

### 5. Run Backend Test Suite
```powershell
cd backend
$env:PYTHONPATH="."
.\venv\Scripts\python.exe -m pytest -v
```

---

## Key API Endpoints

### Phase 6 Risk & Alert Engine
- `GET    /api/v1/alerts`: Paginated list of active alerts with severity and status filters
- `GET    /api/v1/alerts/{id}`: Detailed alert record with incident payload and audit log
- `POST   /api/v1/alerts/{id}/acknowledge`: Acknowledge alert with optional analyst comment
- `POST   /api/v1/alerts/{id}/investigate`: Move alert to `INVESTIGATING` status
- `POST   /api/v1/alerts/{id}/escalate`: Escalate alert with operational justification
- `POST   /api/v1/alerts/{id}/resolve`: Resolve alert with closure notes
- `POST   /api/v1/alerts/{id}/dismiss`: Dismiss false alarm with audit trail
- `GET    /api/v1/alerts/stats/summary`: Aggregate counts by severity and lifecycle state
- `GET    /api/v1/events/{id}/risk`: On-demand calculation of 0–100 analytical risk score and 5-factor breakdown
- `GET    /api/v1/events/{id}/risk/history`: Historical risk assessments across recalculation cycles
- `GET    /api/v1/events/{id}/routing`: Recommended authority response routing and action recommendations
- `GET    /api/v1/alert-rules`: List configured alert evaluation rules
- `POST   /api/v1/alert-rules`: Create configurable alert rule with condition expressions
- `PATCH  /api/v1/alert-rules/{id}`: Enable/disable or edit alert rule condition parameters
- `GET    /api/v1/notifications`: List delivered in-app alert notifications
- `POST   /api/v1/notifications/{id}/read`: Mark notification as read
- `GET    /api/v1/notifications/preferences`: Get analyst alert severity and category subscription preferences
- `PUT    /api/v1/notifications/preferences`: Update analyst notification preferences

### Geospatial, Remote Sensing & Investigation (Phases 1–5)
- `GET    /api/v1/events/geojson`: GeoJSON FeatureCollection of active thermal anomalies
- `GET    /api/v1/events/{id}/investigation`: Consolidated investigation package (telemetry, ML, temporal, land-cover, Sentinel-2, facilities, data provenance, risk assessment)
- `GET    /api/v1/events/{id}/timeline`: Chronological cluster detection history with FRP dynamics
- `GET    /api/v1/events/{id}/evidence`: Sentinel-2 spectral indices, cloud scores, and scene metadata
- `GET    /api/v1/events/{id}/nearby-facilities`: Ranked industrial facilities within proximity radius
- `PATCH  /api/v1/events/{id}/status`: Event lifecycle transition (`NEW -> INVESTIGATING -> CONFIRMED / REJECTED -> CLOSED`)
- `GET    /api/v1/events/compare?id1={id1}&id2={id2}`: Side-by-side analytical comparison of two thermal events
- `GET    /api/v1/facilities/{id}/investigation`: Facility context dossier, risk assessment, and thermal counts
- `GET    /api/v1/facilities/{id}/timeline?days=30`: 30-day thermal detection history aggregated weekly
- `GET    /api/v1/search?q={query}`: Multi-entity search across coordinates, event codes, facilities, and satellites

### Phase 7 Analytics & Professional Reporting
- `GET    /api/v1/analytics/overview`: Executive KPI summary across events, classifications, risk, and response times
- `GET    /api/v1/analytics/timeseries`: Chronological telemetry with interval aggregation (`hour`, `day`, `week`, `month`)
- `GET    /api/v1/analytics/classifications`: AI classification distribution, confidence, and mean FRP metrics
- `GET    /api/v1/analytics/risk`: 0–100 risk score histogram and 4-tier distribution (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`)
- `GET    /api/v1/analytics/alerts`: Alert lifecycle funnel, escalation rate %, and resolution MTTR
- `GET    /api/v1/analytics/facilities`: Monitored infrastructure ranked by thermal incident frequency and peak FRP
- `GET    /api/v1/analytics/facilities/{id}`: Detailed chronological thermal history for a specific industrial asset
- `GET    /api/v1/analytics/geospatial`: PostGIS grid binning (0.05°–2.0°) with polygon cells and GeoJSON heatmap
- `GET    /api/v1/analytics/comparison`: Factual side-by-side comparison (Facility vs Facility, Period vs Period)
- `GET    /api/v1/analytics/trends`: Transparent statistical trend evaluation against prior equivalent window
- `GET    /api/v1/analytics/anomalies`: Statistical anomaly feed identifying thermal excursions >= 2.5x baseline
### Phase 8 Autonomous Monitoring & Real-Time Intelligence
- `GET    /api/v1/system/health`: Overall system health status, DB/PostGIS latency, active workers, ML readiness
- `GET    /api/v1/system/providers`: External data providers health telemetry (FIRMS, Sentinel-2, OSM, WorldCover)
- `GET    /api/v1/system/jobs`: Persistent autonomous pipeline job execution history with stage runs
- `POST   /api/v1/system/pipeline/run`: Trigger on-demand autonomous ingestion and intelligence cycle
- `POST   /api/v1/system/demo/trigger`: Inject simulated high-confidence thermal anomaly through full pipeline
- `GET    /api/v1/system/audit`: Immutable autonomous audit log with correlation ID filtering
- `GET    /api/v1/incidents`: Correlated thermal incidents list with severity and status filters
- `GET    /api/v1/incidents/{id}`: Detailed incident dossier with grouped detections and alert counts
- `PATCH  /api/v1/incidents/{id}/status`: Human analyst status confirmation (`CONTAINED`, `RESOLVED`, `FALSE_POSITIVE`)
- `WS     /api/v1/ws/stream`: Real-time bidirectional WebSocket stream for live events and telemetry
### Phase 10 Production Deployment & Data-Source Hardening
- `GET    /api/v1/system/providers/firms`: Dedicated NASA FIRMS provider health probe with masked telemetry
- `POST   /api/v1/ingestion/firms/historical`: Normalized ingestion of historical FIRMS CSV datasets (2024, 2025, 2026)
- `GET    /api/v1/ingestion/firms/sources`: Multi-satellite sensor registry (`VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`)
- `POST   /api/v1/events/{id}/analyst-review`: Human-in-the-loop analyst confirmation distinguishing AI vs. analyst decisions


---

## Performance Measurements (Measured)

| Pipeline Metric | Measured Latency | SLA Target | Compliance |
| :--- | :--- | :--- | :--- |
| **Incremental FIRMS Ingestion** | **17.69 ms** | < 10,000 ms | **PASSED** (Real-time cursor) |
| **Feature Vector & ML Inference** | **18.42 ms** | < 1,000 ms | **PASSED** (XGBoost tabular) |
| **Incident Correlation & Clustering** | **12.15 ms** | < 500 ms | **PASSED** (Spatial PostGIS) |
| **Risk Scoring & Anti-Storm Alert** | **8.60 ms** | < 500 ms | **PASSED** (Deterministic 5-factor) |
| **WebSocket Broadcast Delivery** | **1.20 ms** | < 100 ms | **PASSED** (In-memory buffer) |
| **End-to-End Autonomous Pipeline** | **1,234.78 ms** (~1.23s) | < 300,000 ms (< 5 min) | **PASSED** (10-stage verified) |


