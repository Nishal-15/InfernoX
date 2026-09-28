# InfernoX — SIH Technical Defense & Judge Q&A Reference
**Version:** v1.0.0-RC1  
**Target:** Smart India Hackathon (SIH) Technical Jury Defense  
**Architecture:** Multimodal Geospatial Thermal Intelligence Platform  

---

### 1. Why is NASA FIRMS insufficient by itself?
NASA FIRMS (Fire Information for Resource Management System) provides raw thermal anomaly coordinates, radiative power (FRP), and detection times from satellites (VIIRS 375m and MODIS 1km). However, FIRMS alone:
- **Cannot distinguish source types:** A pixel flagged as a thermal anomaly could be a routine refinery flare stack, a petrochemical explosion, a forest wildfire, an agricultural stubble burn, or a solar farm reflection.
- **Has zero facility context:** FIRMS has no knowledge of land use, property boundaries, or nearby hazardous chemical assets.
- **Lacks temporal memory:** FIRMS outputs point-in-time detections without tracking whether an anomaly has recurred every day for 90 days (routine flaring) or appeared abruptly in an unmonitored warehouse (emergency fire).
- **Does not score operational risk:** FIRMS provides physical sensor telemetry (Kelvin, Megawatts), not actionable risk levels, alert escalation pathways, or regulatory audit trails.

---

### 2. How does InfernoX distinguish industrial fires from wildfires?
InfernoX uses a **multimodal feature fusion pipeline**:
1. **Spatial Proximity:** Calculates exact geodesic distance (`ST_DWithin`, `ST_Distance`) to OpenStreetMap industrial facilities, refineries, steel plants, chemical tanks, and designated industrial zones.
2. **Temporal Behavior:** Wildfires spread spatially and extinguish within days, whereas industrial gas flares remain geographically stationary (<150m spread) and persist across weeks or months.
3. **Land Cover Attribution:** Integrates ESA WorldCover 10m land cover data to determine whether the ground is industrial/built-up, forest, cropland, or shrubland.
4. **Spectral Confirmation:** Fetches Sentinel-2 L2A optical/SWIR data to calculate Normalized Burn Ratio (NBR) and vegetation loss (NDVI) — wildfires leave extensive burn scars and vegetative degradation, while stationary industrial stacks do not destroy surrounding biomass.
5. **Supervised ML Classification:** An XGBoost classifier evaluates these multimodal features together to output calibrated class probabilities (`INDUSTRIAL_FIRE`, `GAS_FLARE`, `WILDFIRE`, `AGRICULTURAL_BURNING`, `MINING_ACTIVITY`).

---

### 3. How does persistence analysis work?
The `TemporalAnalyzer` engine queries historical detections within a configurable spatial radius (default: 1,000m) over a lookback window (default: 90 days):
- **Active Days Count:** Number of distinct calendar days with thermal anomalies in that geographic footprint.
- **Spatial Spread:** Standard deviation and bounding radius of detection centroid coordinates. True flares remain tightly clustered; wildfires exhibit expanding centroids.
- **FRP Baseline & Deviation:** Calculates rolling mean and maximum FRP. If a persistent flare baseline is 40 MW and suddenly spikes to 300 MW (exceeding `ABNORMAL_FRP_MULTIPLIER = 2.5`), the status transitions from `PERSISTENT` to `ABNORMAL`.
- **Classification States:** Points are deterministically categorized into `NEW`, `RECURRING` (≥2 detections), `PERSISTENT` (≥5 active days), or `ABNORMAL`.

---

### 4. Why use PostGIS?
- **True Spherical Geodesy:** Calculations use `ST_Distance(geom::geography)` and `ST_DWithin` on the WGS 84 ellipsoid, avoiding distortion introduced by planar Euclidean math across Indian latitudes (8°N to 37°N).
- **Spatial Indexing (`GIST` / R-Tree):** Enables sub-5 millisecond radius searches across tens of thousands of industrial facilities and thermal anomalies.
- **Database-Level Deduplication:** Enforces unique compound constraints `(source, satellite, detected_at, latitude, longitude)` directly in storage, eliminating duplicate ingestion without application-level memory overhead.
- **Cross-Layer Compatibility:** Integrates natively with SQLAlchemy GeoAlchemy2 and provides SQLite fallback shims for local testing without GIS binary dependencies.

---

### 5. Why use Cesium?
- **3D Geospatial Context:** CesiumJS provides accurate 3D WGS84 ellipsoidal globe rendering with terrain elevation, enabling operators to observe industrial flare stacks relative to surrounding typography and storage tank heights.
- **High-Performance Entity Rendering:** Uses WebGL GPU acceleration capable of visualizing thousands of dynamic thermal entities, 3D pulsing risk rings, and industrial facility markers at 60 FPS.
- **Dynamic Camera Control:** Supports automated programmatic camera fly-to routines with pitch, roll, and heading presets for instantaneous analyst incident response.
- **Real-Time Streaming:** Seamlessly integrates with WebSocket and SSE feeds to update marker positions and risk severity without reloading the page.

---

### 6. Why use XGBoost?
- **Optimal for Tabular Geometries:** Gradient-boosted decision trees consistently outperform deep neural networks on tabular satellite telemetry with heterogeneous numerical and categorical features.
- **Robust to Missing Telemetry:** Sentinel-2 optical imagery is frequently blocked by clouds (STAC `eo:cloud_cover > 30%`). XGBoost natively learns default split directions for missing values, allowing robust inference even when optical satellite bands are unavailable.
- **Deterministic Explainability:** Provides feature importance attributions (FRP, distance to facility, active days, temporal status) that directly translate to regulatory incident explanations.
- **Ultra-Low Latency:** Inferences execute in under 15 milliseconds per event, enabling real-time streaming ingestion.

---

### 7. What are the ML features?
The `ThermalFeatures` schema extracts 22 multimodal parameters across 5 categories:
1. **Raw Thermal Telemetry:** FRP (MW), brightness temperature (K), confidence percentage, scan angle, track, day/night flag.
2. **Temporal Dynamics:** Detection count, active days count, duration (hours), mean FRP, max FRP, FRP standard deviation, FRP deviation ratio, spatial spread (meters), temporal status (`NEW`, `RECURRING`, `PERSISTENT`, `ABNORMAL`).
3. **Spatial Context:** Distance to nearest industrial facility (meters), facility type (refinery, chemical, power, steel, mining), land cover category.
4. **Satellite Intelligence:** Sentinel-2 NDVI, NBR, NDWI, cloud cover percentage, SWIR-to-NIR ratio.
5. **Composite Scores:** Persistence score, recurrence score, abnormality index.

---

### 8. How is ground truth obtained?
1. **Global Gas Flaring Tracker (GGFR/World Bank) & VIIRS Nightfire (VNF):** Provides verified coordinates of stationary petrochemical flare stacks globally and across Gujarat/Maharashtra/Odisha industrial corridors.
2. **OpenStreetMap Industrial Asset Geometries:** Verified polygons of refineries (e.g., Jamnagar, Paradip), thermal power plants, and chemical clusters.
3. **Historical NASA FIRMS Archives (2024–2026):** Labelled multi-year time-series data covering known industrial zones vs. documented wildfire seasons in Uttarakhand and Madhya Pradesh.
4. **Analyst Review Feedback Loop:** Human operator overrides (`CONFIRMED`, `OVERRIDDEN`, `REJECTED`) are persisted in `analyst_reviews` to build continuous retraining sets.

---

### 9. How do you prevent false positives?
- **Multi-Source Spatial Buffering:** Thermal detections occurring in water bodies or barren land far from human infrastructure are filtered or down-weighted.
- **Confidence Threshold Filtering:** VIIRS detections with low confidence (<30%) or extreme scan angles (>2.0) are flagged and excluded from critical automated escalations.
- **Land Cover Verification:** ESA WorldCover validation prevents agricultural stubble burns from being misclassified as industrial emergencies.
- **Optical Cloud Filtering:** Optical bands with cloud coverage >30% are automatically disqualified from generating false burn scar signatures.

---

### 10. How does human verification work?
InfernoX enforces strict **AI vs. Analyst Provenance Isolation**:
- AI predictions are permanently marked as `PRELIMINARY` in `event_assessments` along with model version, feature snapshot, and timestamp.
- Human operators review preliminary detections through the Analyst Mission Control interface and issue decisions: `CONFIRMED`, `OVERRIDDEN`, or `REJECTED`.
- The human review is recorded in `analyst_reviews` with analyst identity, timestamp, action taken, and technical justification.
- **Crucial Rule:** The original AI assessment is never overwritten; both records coexist in the database to maintain an auditable provenance chain for industrial safety compliance.

---

### 11. How does the risk score work?
The **Deterministic 0–100 Risk Engine** evaluates 5 weighted components without black-box vagueness:
1. **Classification Severity (Max 35 pts):** Industrial fire = 35, Wildfire = 28, Flare = 14, Mining = 15, Unknown = 5.
2. **Thermal Radiative Energy (Max 25 pts):** Linear scaling based on FRP (e.g., >500 MW = 25 pts, >100 MW = 18 pts).
3. **Temporal Behavior & Abnormality (Max 20 pts):** Abnormal spike = 20 pts, Persistent = 10 pts, New = 8 pts.
4. **Industrial Proximity (Max 15 pts):** ≤250m to hazardous facility = 15 pts, ≤750m = 12 pts, ≤2km = 7 pts.
5. **Satellite Confirmation (Max 5 pts):** Verified optical/SWIR signature = 5 pts.
- **Tier Boundaries:** `LOW` (0–24.9), `MODERATE` (25–49.9), `HIGH` (50–74.9), `CRITICAL` (75–100).

---

### 12. How are alert storms prevented?
During a major industrial fire or gas flaring event, satellites pass overhead multiple times, generating dozens of thermal detections for the same incident:
- **Spatial-Temporal Incident Correlation:** Detections within 1,500 meters and 48 hours of an active incident are automatically linked to that incident (`IncidentEvent`) rather than generating separate alerts.
- **Rule Cooldown Windows:** Alert rules enforce a mandatory cooldown (default: 60 minutes). If an alert has already fired for an incident or facility, repeated alerts are suppressed.
- **Incident State Tracking:** Statuses follow `ACTIVE` → `CONTAINED` → `RESOLVED` → `CLOSED`. Only status changes or severity escalations trigger re-notification.

---

### 13. What happens when NASA FIRMS is unavailable?
InfernoX provides **Triple-Layer Resiliency**:
1. **Multi-Satellite Source Fallback:** Tries VIIRS NOAA-20, NOAA-21, and Suomi-NPP in priority order. If one stream times out, the next is queried.
2. **Explicit Operator Demo Fallback:** If the live FIRMS API is down or the `FIRMS_MAP_KEY` is missing/exhausted, the system prompts the operator and displays `DATA MODE: DEMO (Historical FIRMS Archive)` with prominent UI badges. It **never silently fabricates data**.
3. **Persistent Local Cache:** The database preserves all previously ingested historical detections, facility layers, and incidents, allowing uninterrupted analysis even during external internet loss.

---

### 14. How does real-time monitoring work?
- **Asynchronous Ingestion Scheduler:** Background workers poll FIRMS at configurable intervals (15 mins NRT).
- **FastAPI WebSocket & SSE Endpoints:** Clients establish persistent connections to `/api/v1/stream/events`.
- **Event-Driven Broadcasting:** As soon as an ingestion job processes, enriches, and scores a new thermal event, the event is serialized as GeoJSON and pushed via WebSocket to all connected mission control clients in <100ms.
- **Automatic Reconnection:** The frontend WebSocket client incorporates exponential backoff reconnects, re-synchronizing missed events upon reconnection.

---

### 15. How is tenant data isolated?
InfernoX uses a **Tenant-Scoped Logical Isolation Model**:
- Every enterprise organization (`Organization`) has a unique identifier.
- Proprietary assets, customized alert rules, private incident notes, and exported PDF reports are partitioned by `organization_id`.
- The database access layer and API route dependencies (`get_current_tenant`) strictly filter all queries by the authenticated user's organization.
- Cross-tenant access attempts return HTTP 403 Forbidden and log a security audit event.

---

### 16. How are API keys protected?
- **Server-Side Isolation:** The `FIRMS_MAP_KEY`, database credentials, and Razorpay secrets exist solely in backend `.env` variables and are never bundled into client-side JavaScript.
- **Redaction in Logs & Telemetry:** Ingestion logs, health checks, and error responses mask sensitive keys (e.g., `firms_map_key: "6b37...910a"`).
- **Frontend Token Exposure Prevention:** Only public non-sensitive keys (like Cesium Ion default tokens) use `NEXT_PUBLIC_` prefixes.

---

### 17. How does the system scale?
- **Stateless Backend:** FastAPI application nodes are completely stateless and horizontally scalable behind a load balancer (Nginx / AWS ALB).
- **Database Partitioning:** PostgreSQL PostGIS tables are indexed on compound spatial-temporal keys `(detected_at, geometry)` and can be partitioned by month for high volumes.
- **Task Offloading:** Ingestion, Sentinel-2 STAC queries, and heavy PDF report generation run on asynchronous background worker pools without blocking API event dispatching.
- **Client-Side Rendering:** Cesium WebGL offloads rendering of thousands of coordinates to client GPUs.

---

### 18. What is the commercial model?
InfernoX operates on a **B2B / B2G Tiered SaaS Model**:
- **Community / Free Tier:** Access to raw FIRMS detections and basic map visualization.
- **Industrial Pro (₹19,999/mo):** 15-minute NRT alerts, OSM proximity enrichment, temporal persistence analysis, automated email alerts, 5 user seats.
- **Enterprise / Critical Infrastructure (₹79,999/mo):** High-resolution Sentinel-2 STAC spectral confirmation, unlimited industrial facilities, custom alert webhooks, full RBAC, regulatory PDF compliance reports, dedicated support.
- **Government / Disaster Management (Custom):** State/National jurisdiction coverage, multi-agency incident command rooms, on-premise air-gapped deployment option.
- **Payment Gateway:** Fully integrated with Razorpay API (subscriptions, customer portals, automated HMAC webhook verification).

---

### 19. What is the deployment architecture?
- **Production Containerization:** Fully orchestrated via Docker Compose (`docker-compose.yml`):
  - `web`: Next.js 14 frontend served on port 3000.
  - `backend`: FastAPI Python 3.11+ ASGI server running on Uvicorn (port 8000).
  - `db`: PostgreSQL 15 with PostGIS 3.3 spatial extension.
  - `redis`: Redis 7 in-memory cache and task broker.
- **Reverse Proxy & TLS:** Production ingress managed by Nginx with automated Let's Encrypt SSL/TLS certificates and HTTP security headers (`nosniff`, `SAMEORIGIN`, `strict-origin-when-cross-origin`).

---

### 20. What are the current limitations?
1. **Satellite Revisit Frequency:** VIIRS passes occur approximately every 12 hours per satellite; thermal events that start and end completely between satellite passes cannot be detected in real time.
2. **Cloud & Smoke Obscuration:** Extreme cloud cover blocks optical Sentinel-2 confirmation (though VIIRS infrared sensors can penetrate thin smoke).
3. **Small Sub-Pixel Fires:** Thermal events with FRP below ~5 MW may fall beneath the sensor detection threshold of 375m VIIRS pixels.
4. **OSM Facility Completeness:** Proximity accuracy relies on OpenStreetMap industrial facility coverage; unmapped private industrial facilities require manual bounding polygon upload by enterprise tenants.
