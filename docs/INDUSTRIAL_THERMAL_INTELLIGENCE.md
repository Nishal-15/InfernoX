# InfernoX Industrial Thermal Intelligence Architecture

## 1. Executive Summary & Scientific Purpose

InfernoX is an autonomous, multi-modal industrial wildfire and thermal incident intelligence platform designed for critical infrastructure, refineries, chemical plants, and high-hazard industrial zones. 

Standard thermal anomaly detection frameworks frequently conflate persistent industrial operations (e.g., routine petrochemical gas flaring, furnace exhaust) with structural loss-of-containment fires, or conversely mistake expanding natural wildfires encroaching on industrial buffers for stationary facility emissions.

InfernoX resolves this through a multi-tiered, physically grounded analytical intelligence pipeline integrating:
1. **Multi-Sensor Satellite Fusion**: Quality-weighted consolidation of NASA FIRMS passes (VIIRS SNPP, NOAA-20, NOAA-21, and MODIS Aqua/Terra).
2. **Deterministic Spatial Propagation Modeling**: Eigenvalue covariance analysis distinguishing stationary emitters from expanding or propagating combustion fronts.
3. **Industrial vs. Natural Fire Discrimination**: Explainable evidence ledger categorizing thermal sources into operational baselines, abnormal industrial surges, agricultural burns, or propagating wildfires.
4. **Multi-Spectral Verification**: Copernicus Sentinel-2 MSI Level-2A surface reflectance analysis (B02, B03, B04, B08, B11, B12, NDVI, NBR, SWIR ratio).
5. **Operational Risk Modulation & Alert Suppression**: Automatic mitigation of alarm storms for verified persistent operational sources while escalating rapid loss-of-containment surges.

---

## 2. Mathematical & Algorithmic Foundations

### 2.1 Multi-Sensor Observation Fusion & Quality Weighting

NASA FIRMS provides observations across multiple polar-orbiting satellite instruments with varying Ground Sampling Distances (GSD) and off-nadir scan geometries. Rather than discarding duplicate or sequential observations within spatial and temporal proximity windows ($R = 1200\text{ m}$, $\Delta t = 6.0\text{ h}$), InfernoX groups them into an observation cluster $\mathcal{C} = \{o_1, o_2, \dots, o_n\}$ and assigns each observation $o_i$ a transparent quality weight $w_i$:

$$w_i = w_{\text{base}} \times f_{\text{footprint}}(\text{scan}, \text{track}) \times f_{\text{conf}}(\text{confidence}) \times f_{\text{diurnal}}(\text{day/night})$$

Where:
- **Base GSD Weight ($w_{\text{base}}$)**:
  - $\text{VIIRS I-Band (375m at nadir)} \rightarrow 1.0$
  - $\text{MODIS (1000m at nadir)} \rightarrow 0.6$
  - $\text{Unknown/Generic} \rightarrow 0.5$
- **Geometric Footprint Expansion**:
  $$f_{\text{footprint}} = \frac{1.0}{\sqrt{\max(1.0, \text{scan} \times \text{track})}}$$
  Accounts for pixel enlargement and radiometric dilution towards swath edges (bow-tie effect).
- **Confidence Scaling**:
  $$f_{\text{conf}} = 0.5 + 0.5 \times \left(\frac{\text{confidence}}{100.0}\right)$$
- **Night Observation Factor**:
  $$f_{\text{diurnal}} = \begin{cases} 1.10 & \text{if night pass (N) — absence of solar reflection / sunglint} \\ 1.00 & \text{if day pass (D)} \end{cases}$$

The quality-weighted fused coordinates $(\bar{\phi}, \bar{\lambda})$ and fused Fire Radiative Power ($\overline{\text{FRP}}$) are computed as:

$$\bar{\phi} = \frac{\sum_{i=1}^n w_i \phi_i}{\sum_{i=1}^n w_i}, \quad \bar{\lambda} = \frac{\sum_{i=1}^n w_i \lambda_i}{\sum_{i=1}^n w_i}, \quad \overline{\text{FRP}} = \frac{\sum_{i=1}^n w_i \text{FRP}_i}{\sum_{i=1}^n w_i}$$

Cross-sensor corroboration is established if:
$$\text{unique\_platforms}(\mathcal{C}) \ge 2 \implies \text{cross\_sensor\_confirmation} = \text{True}$$

---

### 2.2 Spatial Propagation Model

To distinguish stationary industrial emitters from propagating natural fires, the `SpatialPropagationModel` analyzes the geographic dispersion of detections over time.

For an event cluster with coordinates $\{(\phi_k, \lambda_k)\}_{k=1}^K$ ($K \ge 3$):
1. **Centroid**:
   $$\phi_c = \frac{1}{K}\sum_{k=1}^K \phi_k, \quad \lambda_c = \frac{1}{K}\sum_{k=1}^K \lambda_k$$
2. **Spread Radius ($R_{\text{spread}}$)**:
   $$R_{\text{spread}} = \max_k \text{Haversine}(\phi_k, \lambda_k, \phi_c, \lambda_c)$$
3. **Stationary Concentration ($C_{250}$)**:
   $$C_{250} = \frac{1}{K} \sum_{k=1}^K \mathbf{1}\left(\text{Haversine}(\phi_k, \lambda_k, \phi_c, \lambda_c) \le 250\text{ m}\right)$$
4. **Spread Velocity ($V_{\text{spread}}$)**:
   $$V_{\text{spread}} = \frac{R_{\text{spread}}}{\max(1.0, \Delta t_{\text{hours}})} \quad [\text{m/h}]$$
5. **Principal Axis of Spread & Spatial Covariance**:
   Coordinates are projected onto local Euclidean coordinates relative to the centroid:
   $$y_k = (\phi_k - \phi_c) \cdot 111132\text{ m}, \quad x_k = (\lambda_k - \lambda_c) \cdot 111132\text{ m} \cdot \cos(\phi_c)$$
   The covariance matrix elements are:
   $$\sigma_{yy} = \frac{1}{K}\sum y_k^2, \quad \sigma_{xx} = \frac{1}{K}\sum x_k^2, \quad \sigma_{xy} = \frac{1}{K}\sum y_k x_k$$
   The principal axis azimuth $\theta$ and elongation ratio $\mathcal{E}$ are:
   $$\theta = \frac{1}{2} \operatorname{atan2}(2\sigma_{xy}, \sigma_{xx} - \sigma_{yy}) \pmod{360^\circ}$$
   $$\mathcal{E} = \sqrt{\frac{\lambda_1}{\lambda_2}}, \quad \text{where } \lambda_{1,2} = \frac{\sigma_{xx} + \sigma_{yy} \pm \sqrt{(\sigma_{xx} - \sigma_{yy})^2 + 4\sigma_{xy}^2}}{2}$$

#### Propagation State Classifications
- **`STATIONARY_SOURCE`**: $R_{\text{spread}} \le 350\text{ m}$, $V_{\text{spread}} \le 12\text{ m/h}$, $C_{250} \ge 0.70$.
- **`LOCALIZED_EVENT`**: $R_{\text{spread}} \le 750\text{ m}$, $V_{\text{spread}} \le 30\text{ m/h}$.
- **`EXPANDING_EVENT`**: $R_{\text{spread}} \le 2000\text{ m}$ or $30 < V_{\text{spread}} \le 100\text{ m/h}$.
- **`PROPAGATING_EVENT`**: $R_{\text{spread}} > 2000\text{ m}$ or $V_{\text{spread}} > 100\text{ m/h}$ with directional elongation.
- **`INSUFFICIENT_DATA`**: $K < 3$ historical observations (prevents premature extrapolation).

---

### 2.3 Industrial vs. Natural Fire Discrimination

The `IndustrialFireDiscriminator` synthesizes spatial infrastructure proximity, temporal baselines, propagation dynamics, and remote sensing diagnostics to construct an explainable evidence ledger.

#### Facility Footprint Hierarchy
- $\le 100\text{ m}$: `INSIDE_FACILITY_FOOTPRINT`
- $101 - 250\text{ m}$: `FACILITY_BOUNDARY_PROXIMITY`
- $251 - 500\text{ m}$: `PROCESS_AREA_PROXIMITY`
- $501 - 750\text{ m}$: `STORAGE_AREA_PROXIMITY`
- $751 - 2000\text{ m}$: `INDUSTRIAL_ZONE_PROXIMITY`
- $> 2000\text{ m}$: `OUTSIDE_INDUSTRIAL_CONTEXT`

#### Change-Point Anomaly Detection
Given historical median FRP ($\widetilde{\text{FRP}}$), FRP acceleration ($\alpha = \Delta\text{FRP}/\Delta t$), and spatial spread ($R_{\text{spread}}$):
- Ratio $\rho = \text{FRP} / \max(1.0, \widetilde{\text{FRP}})$.
- **`MAJOR_ANOMALY`**: $\rho \ge 4.0$ or $\alpha \ge 25.0\text{ MW/h}$.
- **`SIGNIFICANT_DEVIATION`**: $\rho \ge 2.5$ or $R_{\text{spread}} > 600\text{ m}$.
- **`MINOR_DEVIATION`**: $\rho \ge 1.8$.
- **`NORMAL_BASELINE`**: $\rho < 1.8$ and $\alpha < 15.0\text{ MW/h}$.

#### Expected Thermal Context Mapping
- If the nearest facility is hazardous industrial (refinery, chemical, gas plant, LNG, LPG, fertilizer) AND history shows $\ge 3$ active days or persistent status AND propagation is `STATIONARY_SOURCE` AND change-point is `NORMAL_BASELINE`:
  $$\implies \text{EXPECTED\_INDUSTRIAL\_THERMAL\_CONTEXT}$$
- If hazardous industrial AND change-point is `MAJOR_ANOMALY` or `SIGNIFICANT_DEVIATION`:
  $$\implies \text{UNEXPECTED\_INDUSTRIAL\_THERMAL\_CONTEXT}$$

---

### 2.4 Multi-Spectral Remote Sensing (Sentinel-2 MSI)

Copernicus Sentinel-2 Level-2A surface reflectance data is analyzed across 6 critical diagnostic bands:
- $B02$ (Blue, 490 nm)
- $B03$ (Green, 560 nm)
- $B04$ (Red, 665 nm)
- $B08$ (NIR, 842 nm)
- $B11$ (SWIR-1, 1610 nm)
- $B12$ (SWIR-2, 2190 nm)

#### Derived Biophysical Indices
- **Normalized Difference Vegetation Index (NDVI)**:
  $$\text{NDVI} = \frac{B08 - B04}{B08 + B04}$$
- **Normalized Burn Ratio (NBR)**:
  $$\text{NBR} = \frac{B08 - B12}{B08 + B12}$$
- **SWIR Combustion Ratio**:
  $$\text{Ratio}_{\text{SWIR}} = \frac{B12}{\max(0.01, B08)}$$

#### Spectral Diagnosis Engine
- **`CLOUD_OBSCURED`**: Cloud cover exceeds operational threshold or scene is obscured by meteorological overcast. **Crucial Rule**: Cloud obstruction is classified as `INCONCLUSIVE` (neutral evidence) and is never treated as negative evidence against the presence of fire.
- **`BURN_SCAR_SUPPORT`**: $\text{NBR} < -0.15$ and $\Delta\text{NBR} \ge 0.20$. Confirms physical ground surface charring.
- **`VEGETATION_FIRE_SUPPORT`**: $\text{Ratio}_{\text{SWIR}} > 1.2$ and $\text{NDVI} < 0.35$. Confirms intense subpixel combustion in vegetative fuel beds.
- **`INDUSTRIAL_SURFACE_SUPPORT`**: $\text{Ratio}_{\text{SWIR}} > 1.1$ localized over non-vegetative impervious built surfaces.
- **`NO_CLEAR_SPECTRAL_SIGNAL`**: Reflectances within normal seasonal range.

---

### 2.5 Operational Risk Dampening & Alert Suppression

#### Risk Engine Dampening
In `RiskEngine.evaluate_risk`:
- When `expected_thermal_context == "EXPECTED_INDUSTRIAL_THERMAL_CONTEXT"`:
  $$\text{Risk Score} = \min(42.0, \text{Raw Score})$$
  $$\text{Risk Reasons} \leftarrow \text{["EXPECTED\_OPERATIONAL\_THERMAL\_SOURCE"]}$$
  Caps the risk at `MODERATE` ($\le 42.0$), preventing false `HIGH` or `CRITICAL` risk alerts for routine operational flares.
- When `expected_thermal_context == "UNEXPECTED_INDUSTRIAL_THERMAL_CONTEXT"`:
  $$\text{Risk Score} = \min(100.0, \text{Raw Score} + 15.0)$$
  $$\text{Risk Reasons} \leftarrow \text{["UNEXPECTED\_INDUSTRIAL\_THERMAL\_SURGE"]}$$
  Escalates risk to `HIGH` or `CRITICAL` for abnormal flare surges or loss of containment.

#### Alert Anti-Storm Cooldown & Suppression
In `AlertEngine.evaluate_event_alerts`:
- Verified persistent operational sources (`EXPECTED_OPERATIONAL_THERMAL_SOURCE`) have all non-critical alerts suppressed (e.g. `HAZARDOUS_INFRASTRUCTURE_PROXIMITY` or `ABNORMAL_THERMAL_SURGE` are silenced, while `CRITICAL_INDUSTRIAL_FIRE` is preserved).
- 60-minute sliding window cooldown deduplication suppresses redundant alerts for the same incident/facility.

---

## 3. Assumptions, Constraints & Limitations

1. **Satellite Pass Cadence**: FIRMS polar orbits provide intermittent coverage (typically 4–6 observations per 24-hour cycle per location depending on latitude). InfernoX does not claim continuous minute-by-minute satellite telemetry; it explicitly tags the temporal provenance and latency of every observation.
2. **Cloud Penetration**: Thermal infrared (MWIR/LWIR) and optical surface reflectance cannot penetrate thick meteorological overcast. In cloudy conditions, Sentinel-2 status is cleanly designated as `CLOUD_OBSCURED` rather than falsely asserting no fire exists.
3. **Subpixel Flares**: Small operational flares ($< 5\text{ MW}$) may fall below the detection threshold of MODIS (1 km nadir) or wide off-nadir VIIRS angles. InfernoX weights observations according to scan angle and sensor resolution.
4. **Machine Learning Horizon**: The XGBoost `xgb-v1` model is trained on canonical tabular thermal features. While probability tiers (`HIGH_CONFIDENCE`, `MEDIUM_CONFIDENCE`, `LOW_CONFIDENCE`, `UNCERTAIN`) and Shannon entropy are reported, the model status is honestly documented as requiring an expanded multi-region benchmark evaluation corpus before claiming generalized empirical accuracy.
