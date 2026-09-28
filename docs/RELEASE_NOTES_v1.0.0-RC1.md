# InfernoX v1.0.0-RC1 Release Notes
**Release Candidate 1 — Production & SIH Launch Readiness**  
**Date:** September 28, 2026  
**System:** InfernoX — AI-Based Industrial Fire & Persistent Thermal Source Intelligence Platform  

---

## Overview
InfernoX v1.0.0-RC1 represents the validated release candidate of the InfernoX platform, built and verified for the Smart India Hackathon (SIH) live presentation and enterprise industrial fire monitoring deployments.

---

## Key Features & Capabilities

### 1. Real NASA FIRMS Multi-Satellite Ingestion
- Real-time connectivity with the official NASA FIRMS API (`https://firms.modaps.eosdis.nasa.gov/api/`).
- Multi-source satellite ingestion: `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`, and historical archives.
- Automated API key protection, token masking, and rate-limit handling (429 backoff).
- Zero silent fallbacks: Clear UI distinction between `LIVE`, `HISTORICAL`, and `DEMO` data modes.

### 2. Geospatial & Industrial Facility Proximity Engine
- PostGIS spherical geodesic calculations (`ST_Distance`, `ST_DWithin`) on WGS 84.
- OpenStreetMap (OSM) industrial facility integration with automatic facility classification (refineries, chemical plants, steel mills, thermal stations).
- Spatial indexing for sub-5ms query response over large spatial databases.

### 3. Temporal Persistence & Flaring Intelligence
- 90-day lookback clustering engine evaluating active detection days, spatial spread radius, and recurrence scores.
- Dynamic flare baseline tracking: Differentiates stationary, routine flaring from abnormal thermal excursions (`ABNORMAL_FRP_MULTIPLIER = 2.5`).
- Temporal states: `NEW`, `RECURRING`, `PERSISTENT`, `ABNORMAL`.

### 4. Machine Learning Inference & Provenance Tracking
- XGBoost tabular classifier trained on multimodal thermal, temporal, and spatial features.
- Native missing-value resilience: Robust inference when optical satellite feeds are cloud-obscured.
- Strict provenance segregation: AI preliminary predictions (`event_assessments`) are permanently isolated from human operator reviews (`analyst_reviews`).

### 5. Deterministic 0–100 Risk Engine & Anti-Storm Alerting
- Explainable 5-factor scoring model: Classification weight (35%), FRP intensity (25%), Temporal persistence (20%), Infrastructure proximity (15%), Satellite confirmation (5%).
- Standardized risk tiers: `LOW` (0–24.9), `MODERATE` (25–49.9), `HIGH` (50–74.9), `CRITICAL` (75–100).
- Anti-storm incident correlation: Deduplicates nearby detections within 1,500m and 48 hours to prevent notification flooding.

### 6. Mission Control 3D Cesium Visualization
- WebGL GPU-accelerated 3D WGS84 globe rendering dynamic thermal anomalies, pulsing risk halos, and industrial facilities.
- Smooth camera fly-to animations to incident coordinates.
- Live streaming updates via WebSockets and SSE.

### 7. SaaS Architecture, RBAC & Billing
- Multi-tenant isolation for enterprise organizations, private facilities, and alert rules.
- Role-Based Access Control (`SUPER_ADMIN`, `ORG_ADMIN`, `ANALYST`, `OPERATOR`, `VIEWER`).
- Razorpay subscription integration with automated webhook signature verification and sandbox testing.

---

## Automated Test Verification
- **Backend Test Suite:** 132/132 tests passed (100% pass rate).
- **Frontend Production Build:** Next.js 14 compiled with 0 TypeScript/lint errors.
- **Security Audit:** Zero SQL injection, path traversal, or secret leakage vulnerabilities.

---

## Deployment Requirements
- **Docker Engine:** Version 24.0+ and Docker Compose v2.0+
- **Database:** PostgreSQL 15+ with PostGIS 3.3+ (or SQLite with SpatiaLite shims for local testing)
- **Runtime:** Python 3.11+ / Node.js 18+
- **Environment Configuration:** Valid `.env` with `FIRMS_MAP_KEY` and `NEXT_PUBLIC_CESIUM_ION_ACCESS_TOKEN`.
