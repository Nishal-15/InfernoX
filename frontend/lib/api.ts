import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Phase 9: Injects JWT Authorization token and active tenant context
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('infernox_token');
    const orgId = localStorage.getItem('infernox_active_org_id');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (orgId) {
      config.headers['X-Organization-Id'] = orgId;
    }
  }
  return config;
});

export interface QueryParams {
  start?: string;
  end?: string;
  min_confidence?: number;
  satellite?: string;
  limit?: number;
  offset?: number;
  [key: string]: unknown;
}

export interface ReviewPayload {
  decision?: string;
  action?: string;
  comment?: string;
  note?: string;
  final_classification?: string;
  analyst_id?: string;
}

export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('API health check failed:', error);
    throw error;
  }
};

export const getFirmsStatus = async () => {
  const response = await apiClient.get('/data/firms/status');
  return response.data;
};

export const getIngestionStatus = async () => {
  const response = await apiClient.get('/ingestion/status');
  return response.data;
};

export const getIngestionJobs = async () => {
  const response = await apiClient.get('/ingestion/jobs');
  return response.data;
};

export const ingestFirmsData = async () => {
  const response = await apiClient.post('/data/firms/ingest');
  return response.data;
};

export const ingestOsmData = async () => {
  const response = await apiClient.post('/data/osm/ingest');
  return response.data;
};

export const getEventsGeoJson = async (params: QueryParams = {}) => {
  const response = await apiClient.get('/events/geojson', { params });
  return response.data;
};

export const getEventsList = async (params: QueryParams = {}) => {
  const response = await apiClient.get('/events', { params });
  return response.data;
};

export const getEventDetails = async (id: number | string) => {
  const response = await apiClient.get(`/events/${id}`);
  return response.data;
};

export const getEventContext = async (id: number | string) => {
  const response = await apiClient.get(`/events/${id}/context`);
  return response.data;
};

export const getFacilitiesGeoJson = async (params: QueryParams = {}) => {
  const response = await apiClient.get('/facilities/geojson', { params });
  return response.data;
};

export const globalSearch = async (query: string) => {
  const response = await apiClient.get('/search', { params: { query } });
  return response.data;
};

export const getTemporalAnalysis = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/temporal-analysis`);
  return response.data;
};

export const getEventFeatures = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/features`);
  return response.data;
};

export const classifyEvent = async (eventId: number) => {
  const response = await apiClient.post(`/events/${eventId}/classification`);
  return response.data;
};

export const runAiInference = async (eventId: number) => {
  // Uses Phase 3 classification route with backwards fallback
  try {
    const response = await apiClient.post(`/events/${eventId}/classification`);
    return response.data;
  } catch {
    const response = await apiClient.post(`/ai/predict/${eventId}`);
    return response.data;
  }
};

export const getAiAssessment = async (eventId: number) => {
  try {
    const response = await apiClient.get(`/events/${eventId}/classification`);
    return response.data;
  } catch {
    const response = await apiClient.get(`/ai/events/${eventId}/assessment`);
    return response.data;
  }
};

export const submitAnalystReview = async (eventId: number, data: ReviewPayload) => {
  try {
    const response = await apiClient.post(`/events/${eventId}/reviews`, data);
    return response.data;
  } catch {
    const response = await apiClient.post(`/ai/events/${eventId}/review`, data);
    return response.data;
  }
};

export const getEventReviews = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/reviews`);
  return response.data;
};

export const exportTrainingData = async () => {
  const response = await apiClient.get('/ai/training-data/export');
  return response.data;
};

// Phase 4: Production ML & Satellite Intelligence APIs
export const predictEventMl = async (eventId: number) => {
  try {
    const response = await apiClient.post(`/ml/predict/${eventId}`);
    return response.data;
  } catch {
    // Graceful fallback to classification endpoint
    const response = await apiClient.post(`/events/${eventId}/classification`);
    return response.data;
  }
};

export const getCurrentModel = async () => {
  const response = await apiClient.get('/ml/models/current');
  return response.data;
};

export const getMlModels = async () => {
  const response = await apiClient.get('/ml/models');
  return response.data;
};

export const getDatasetStatus = async () => {
  const response = await apiClient.get('/ml/dataset/status');
  return response.data;
};

export const getEventSatellite = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/satellite`);
  return response.data;
};

export const getEventLandcover = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/landcover`);
  return response.data;
};

// Phase 5: Event Investigation & Advanced 3D Mission Control APIs
export const getEventInvestigation = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/investigation`);
  return response.data;
};

export const getEventTimeline = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/timeline`);
  return response.data;
};

export const getEventEvidence = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/evidence`);
  return response.data;
};

export const getEventNearbyFacilities = async (eventId: number, radiusKm: number = 5.0) => {
  const response = await apiClient.get(`/events/${eventId}/nearby-facilities`, {
    params: { radius_km: radiusKm }
  });
  return response.data;
};

export const updateEventStatus = async (eventId: number, status: string, reason?: string) => {
  const response = await apiClient.patch(`/events/${eventId}/status`, {
    status,
    reason
  });
  return response.data;
};

export const compareEvents = async (id1: number, id2: number) => {
  const response = await apiClient.get('/events/compare', {
    params: { id1, id2 }
  });
  return response.data;
};

export const getFacilityInvestigation = async (facilityId: number, radiusKm: number = 3.0) => {
  const response = await apiClient.get(`/facilities/${facilityId}/investigation`, {
    params: { radius_km: radiusKm }
  });
  return response.data;
};

export const getFacilityTimeline = async (facilityId: number, days: number = 30) => {
  const response = await apiClient.get(`/facilities/${facilityId}/timeline`, {
    params: { days }
  });
  return response.data;
};

// ==========================================
// Phase 6 — Risk, Alert & Response Engine APIs
// ==========================================

export interface AlertData {
  id: number;
  alert_code: string;
  event_id: number;
  rule_id?: number | null;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  title: string;
  message: string;
  status: 'NEW' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'ESCALATED' | 'RESOLVED' | 'DISMISSED';
  incident_payload: Record<string, unknown>;
  created_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  escalated_at?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
  audit_logs?: Array<{
    id: number;
    actor: string;
    action: string;
    previous_status?: string | null;
    new_status?: string | null;
    comment?: string | null;
    timestamp: string;
  }>;
}

export interface AlertStats {
  total_alerts: number;
  critical_count: number;
  high_count: number;
  moderate_count: number;
  low_count: number;
  new_count: number;
  acknowledged_count: number;
  investigating_count: number;
  escalated_count: number;
  resolved_count: number;
}

export const getAlertsList = async (params?: {
  severity?: string;
  status?: string;
  event_id?: number;
  skip?: number;
  limit?: number;
}) => {
  const response = await apiClient.get('/alerts', { params });
  return response.data;
};

export const getAlert = async (alertId: number) => {
  const response = await apiClient.get(`/alerts/${alertId}`);
  return response.data;
};

export const acknowledgeAlert = async (alertId: number, actor: string = 'analyst', comment?: string) => {
  const response = await apiClient.post(`/alerts/${alertId}/acknowledge`, { actor, comment });
  return response.data;
};

export const investigateAlert = async (alertId: number, actor: string = 'analyst', comment?: string) => {
  const response = await apiClient.post(`/alerts/${alertId}/investigate`, { actor, comment });
  return response.data;
};

export const escalateAlert = async (alertId: number, actor: string = 'analyst', comment?: string) => {
  const response = await apiClient.post(`/alerts/${alertId}/escalate`, { actor, comment });
  return response.data;
};

export const resolveAlert = async (alertId: number, actor: string = 'analyst', comment?: string) => {
  const response = await apiClient.post(`/alerts/${alertId}/resolve`, { actor, comment });
  return response.data;
};

export const dismissAlert = async (alertId: number, actor: string = 'analyst', comment?: string) => {
  const response = await apiClient.post(`/alerts/${alertId}/dismiss`, { actor, comment });
  return response.data;
};

export const getAlertStatsSummary = async (): Promise<AlertStats> => {
  const response = await apiClient.get('/alerts/stats/summary');
  return response.data;
};

export const getEventRisk = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/risk`);
  return response.data;
};

export const getEventRiskHistory = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/risk/history`);
  return response.data;
};

export const getEventRouting = async (eventId: number) => {
  const response = await apiClient.get(`/events/${eventId}/routing`);
  return response.data;
};

export interface NotificationLogItem {
  id: number;
  alert_id?: number;
  recipient?: string;
  channel: string;
  title: string;
  message: string;
  is_read: boolean;
  status: string;
  metadata?: {
    alert_id?: number;
    event_id?: number;
    severity?: string;
    risk_score?: number;
    classification?: string;
  };
  created_at: string;
}

export interface NotificationPreferences {
  user_id?: string;
  channels?: string[];
  subscribed_severities?: string[];
  subscribed_classifications?: string[];
  min_risk_score?: number;
  quiet_hours_enabled?: boolean;
}

export const getNotifications = async (params?: number | { unread_only?: boolean; limit?: number }) => {
  const queryParams = typeof params === 'number' 
    ? { limit: params } 
    : { limit: params?.limit ?? 20, unread_only: params?.unread_only ?? false };
  const response = await apiClient.get('/notifications', { params: queryParams });
  return response.data;
};

export const markNotificationRead = async (notificationId: number) => {
  const response = await apiClient.post(`/notifications/${notificationId}/read`);
  return response.data;
};

export const getNotificationPreferences = async (userId: string = "analyst-default") => {
  const response = await apiClient.get('/notifications/preferences', { params: { user_id: userId } });
  return response.data;
};

export const saveNotificationPreferences = async (prefs: NotificationPreferences) => {
  const response = await apiClient.put('/notifications/preferences', {
    subscribed_severities: prefs.subscribed_severities,
    subscribed_categories: prefs.subscribed_classifications,
    in_app_enabled: prefs.channels?.includes('in_app') ?? true,
    email_enabled: prefs.channels?.includes('email') ?? false,
    webhook_url: null
  }, {
    params: { user_id: prefs.user_id || 'analyst-default' }
  });
  return response.data;
};

export const updateNotificationPreferences = saveNotificationPreferences;

// ==========================================
// PHASE 7: Analytics & Reporting
// ==========================================

export interface KPISummary {
  total_events: number;
  active_events: number;
  industrial_events: number;
  mean_frp: number;
  peak_frp: number;
  high_risk_count: number;
  total_alerts: number;
  active_alerts: number;
  mean_tt_acknowledge_mins?: number | null;
  mean_tt_resolve_mins?: number | null;
  temporal_window: {
    start: string;
    end: string;
    preset: string;
  };
}

export interface TimeSeriesPoint {
  timestamp: string;
  count: number;
  mean_frp: number;
  max_frp: number;
  alert_count: number;
}

export interface TimeSeriesResponse {
  interval: string;
  data: TimeSeriesPoint[];
}

export interface ClassificationItem {
  classification: string;
  count: number;
  percentage: number;
  mean_confidence: number;
  mean_frp: number;
  max_frp: number;
}

export interface ClassificationAnalyticsResponse {
  total: number;
  breakdown: ClassificationItem[];
}

export interface RiskAnalyticsResponse {
  total_scored: number;
  mean_risk_score: number;
  tier_counts: {
    LOW: number;
    MODERATE: number;
    HIGH: number;
    CRITICAL: number;
  };
  score_histogram: {
    bin: string;
    count: number;
  }[];
}

export interface AlertAnalyticsResponse {
  total_alerts: number;
  status_counts: {
    NEW: number;
    ACKNOWLEDGED: number;
    INVESTIGATING: number;
    ESCALATED: number;
    RESOLVED: number;
    DISMISSED: number;
  };
  severity_counts: {
    INFO: number;
    LOW: number;
    MEDIUM: number;
    HIGH: number;
    CRITICAL: number;
  };
  escalation_rate_percent: number;
  mean_tt_acknowledge_mins: number | null;
  mean_tt_resolve_mins: number | null;
}

export interface FacilityMetric {
  facility_id: number;
  name: string;
  facility_type: string;
  operator?: string | null;
  event_count: number;
  mean_frp: number;
  max_frp: number;
  high_risk_event_count: number;
  last_detected_at?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface FacilityTimelineNode {
  event_id: number;
  detected_at: string;
  frp: number;
  confidence: number;
  classification: string;
  risk_score?: number | null;
  distance_meters?: number | null;
}

export interface GeospatialHeatmapCell {
  grid_id: string;
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  centroid_lat: number;
  centroid_lon: number;
  event_count: number;
  mean_frp: number;
  max_frp: number;
  high_risk_count: number;
}

export interface GeospatialHeatmapResponse {
  resolution_deg: number;
  cell_count: number;
  cells: GeospatialHeatmapCell[];
  geojson: unknown;
}

export interface ComparisonMetric {
  metric: string;
  value_a: number | string;
  value_b: number | string;
  delta_percent?: number | null;
}

export interface ComparisonResponse {
  comparison_type: string;
  label_a: string;
  label_b: string;
  metrics: ComparisonMetric[];
  summary: string;
}

export interface TrendSummary {
  metric: string;
  current_value: number;
  previous_value: number;
  percentage_change: number;
  status: 'STABLE' | 'INCREASING' | 'DECREASING' | 'VOLATILE' | 'EMERGING';
}

export interface AnomalyItem {
  event_id: number;
  detected_at: string;
  frp: number;
  baseline_mean_frp: number;
  excursion_factor: number;
  classification: string;
  facility_name?: string | null;
  reason: string;
}

export interface ReportMetadata {
  report_id: string;
  report_type: string;
  title: string;
  generated_at: string;
  generated_by: string;
  parameters: Record<string, unknown>;
  classification_level: string;
}

export interface ReportProvenance {
  firms_source: string;
  osm_source: string;
  land_cover_source: string;
  satellite_imagery_source: string;
  ml_model_version: string;
  risk_engine_version: string;
  analytics_engine_version: string;
  export_timestamp: string;
  tamper_seal_hash: string;
}

export interface ReportDataPayload {
  metadata: ReportMetadata;
  executive_summary: string;
  sections: {
    section_id: string;
    title: string;
    summary?: string;
    data: unknown;
  }[];
  kpis: Record<string, unknown>;
  provenance: ReportProvenance;
}

export interface ReportListItem {
  report_id: string;
  report_type: string;
  title: string;
  target_id?: string | null;
  format: string;
  created_at: string;
  created_by: string;
}

export interface ReportGenerateRequest {
  report_type: 'INCIDENT' | 'FACILITY' | 'REGIONAL' | 'EXECUTIVE';
  target_id?: string;
  format: 'JSON' | 'PDF' | 'CSV' | 'GEOJSON';
  parameters?: Record<string, unknown>;
  sections_to_include?: string[];
  generated_by?: string;
}

export const getAnalyticsOverview = async (params: { range_preset?: string; start_date?: string; end_date?: string; min_frp?: number; max_frp?: number } = {}) => {
  const response = await apiClient.get<KPISummary>('/analytics/overview', { params });
  return response.data;
};

export const getAnalyticsSummary = getAnalyticsOverview;

export const getAnalyticsTimeseries = async (params: { interval?: string; range_preset?: string; start_date?: string; end_date?: string; min_frp?: number } = {}) => {
  const response = await apiClient.get<TimeSeriesResponse>('/analytics/timeseries', { params });
  return response.data;
};

export const getAnalyticsClassifications = async (params: { range_preset?: string; start_date?: string; end_date?: string; risk_level?: string } = {}) => {
  const response = await apiClient.get<ClassificationAnalyticsResponse>('/analytics/classifications', { params });
  return response.data;
};

export const getAnalyticsRisk = async (params: { range_preset?: string; start_date?: string; end_date?: string } = {}) => {
  const response = await apiClient.get<RiskAnalyticsResponse>('/analytics/risk', { params });
  return response.data;
};

export const getAnalyticsAlerts = async (params: { range_preset?: string; start_date?: string; end_date?: string } = {}) => {
  const response = await apiClient.get<AlertAnalyticsResponse>('/analytics/alerts', { params });
  return response.data;
};

export const getAnalyticsFacilities = async (params: { facility_type?: string; min_events?: number; limit?: number } = {}) => {
  const response = await apiClient.get<FacilityMetric[]>('/analytics/facilities', { params });
  return response.data;
};

export const getAnalyticsFacilityTimeline = async (facilityId: number, days: number = 90) => {
  const response = await apiClient.get<FacilityTimelineNode[]>(`/analytics/facilities/${facilityId}`, { params: { days } });
  return response.data;
};

export const getAnalyticsGeospatial = async (params: { resolution_deg?: number; range_preset?: string; start_date?: string; end_date?: string; min_frp?: number } = {}) => {
  const response = await apiClient.get<GeospatialHeatmapResponse>('/analytics/geospatial', { params });
  return response.data;
};

export const getAnalyticsComparison = async (params: { comparison_type: string; id_a?: number; id_b?: number; period_a_start?: string; period_a_end?: string; period_b_start?: string; period_b_end?: string }) => {
  const response = await apiClient.get<ComparisonResponse>('/analytics/comparison', { params });
  return response.data;
};

export const getAnalyticsTrends = async (params: { range_preset?: string; start_date?: string; end_date?: string } = {}) => {
  const response = await apiClient.get<Record<string, TrendSummary>>('/analytics/trends', { params });
  return response.data;
};

export const getAnalyticsAnomalies = async (params: { limit?: number; range_preset?: string; start_date?: string; end_date?: string } = {}) => {
  const response = await apiClient.get<AnomalyItem[]>('/analytics/anomalies', { params });
  return response.data;
};

export const generateReport = async (request: ReportGenerateRequest) => {
  if (request.format === 'PDF' || request.format === 'CSV') {
    const response = await apiClient.post('/reports/generate', request, {
      responseType: 'blob'
    });
    return response.data;
  }
  const response = await apiClient.post('/reports/generate', request);
  return response.data;
};

export const getIncidentReport = async (eventId: number) => {
  const response = await apiClient.get<ReportDataPayload>(`/reports/incident/${eventId}`);
  return response.data;
};

export const getFacilityReport = async (facilityId: number, days: number = 90) => {
  const response = await apiClient.get<ReportDataPayload>(`/reports/facility/${facilityId}`, { params: { days } });
  return response.data;
};

export const getExecutiveReport = async (startDate?: string, endDate?: string) => {
  const response = await apiClient.get<ReportDataPayload>('/reports/executive', {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
};

export const getRegionalReport = async (regionName: string = "National Monitored Corridor", startDate?: string, endDate?: string) => {
  const response = await apiClient.get<ReportDataPayload>('/reports/regional', {
    params: { region_name: regionName, start_date: startDate, end_date: endDate }
  });
  return response.data;
};

export const getReportHistory = async (params: { limit?: number; report_type?: string } = {}) => {
  const response = await apiClient.get<ReportListItem[]>('/reports/history', { params });
  return response.data;
};

// ==========================================
// PHASE 8: AUTONOMOUS MONITORING & INTELLIGENCE
// ==========================================

export interface ComponentHealth {
  status: string;
  latency_ms?: number;
  message?: string;
  details?: Record<string, unknown>;
}

export interface SystemHealthResponse {
  status: string;
  timestamp: string;
  uptime_seconds: number;
  components: Record<string, ComponentHealth>;
  active_workers: number;
}

export interface ProviderHealthResponse {
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE' | 'UNKNOWN';
  endpoint: string;
  last_check?: string;
  last_success?: string;
  last_failure?: string;
  latency_ms?: number;
  failure_count: number;
  message?: string;
}

export interface PipelineStageRunResponse {
  id: number;
  stage_name: string;
  status: string;
  attempt: number;
  error_message?: string;
  duration_ms?: number;
  created_at?: string;
}

export interface PipelineJobResponse {
  job_id: string;
  job_type: string;
  status: string;
  source: string;
  correlation_id?: string;
  records_fetched: number;
  records_created: number;
  records_updated: number;
  records_failed: number;
  error_message?: string;
  retry_count: number;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  stages?: PipelineStageRunResponse[];
}

export interface AutonomousAuditResponse {
  id: number;
  correlation_id?: string;
  job_id?: string;
  event_id?: number;
  incident_id?: number;
  action: string;
  actor_type: string;
  previous_state?: Record<string, unknown>;
  new_state?: Record<string, unknown>;
  metadata_info?: Record<string, unknown>;
  created_at: string;
}


export interface ThermalIncidentResponse {
  id: number;
  incident_code: string;
  title: string;
  status: string;
  severity: string;
  classification?: string;
  risk_score: number;
  risk_level?: string;
  centroid_latitude?: number;
  centroid_longitude?: number;
  centroid_lat?: number;
  centroid_lon?: number;
  first_detected_at?: string;
  last_detected_at?: string;
  first_seen?: string;
  last_seen?: string;
  duration_hours?: number;
  event_count?: number;
  observation_count?: number;
  peak_frp?: number;
  mean_frp?: number;
  primary_facility_id?: number;
  primary_facility_name?: string;
  distance_to_facility_meters?: number;
  incident_summary_json?: Record<string, unknown>;
  summary?: string;
  analyst_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ThermalIncidentListResponse {
  items: ThermalIncidentResponse[];
  total: number;
  active_count: number;
  critical_count: number;
}

export interface DemoTriggerResponse {
  message: string;
  event_id: number;
  incident_id?: number;
  risk_score: number;
  alert_id?: number;
  status: string;
}

export const getSystemHealth = async (): Promise<SystemHealthResponse> => {
  const response = await apiClient.get<SystemHealthResponse>('/system/health');
  return response.data;
};

export const getSystemProviders = async (): Promise<ProviderHealthResponse[]> => {
  const response = await apiClient.get<ProviderHealthResponse[]>('/system/providers');
  return response.data;
};

export const getPipelineJobs = async (params: { limit?: number; offset?: number; status?: string } = {}): Promise<PipelineJobResponse[]> => {
  const response = await apiClient.get<PipelineJobResponse[]>('/system/jobs', { params });
  return response.data;
};

export const triggerPipelineRun = async (useDemo: boolean = false): Promise<PipelineJobResponse> => {
  const response = await apiClient.post<PipelineJobResponse>('/system/pipeline/run', null, {
    params: { use_demo: useDemo }
  });
  return response.data;
};

export const triggerDemoEvent = async (params: {
  lat?: number;
  lon?: number;
  frp?: number;
  brightness?: number;
  facility_id?: number;
} = {}): Promise<DemoTriggerResponse> => {
  const response = await apiClient.post<DemoTriggerResponse>('/system/demo/trigger', null, { params });
  return response.data;
};

export const getAutonomousAuditLogs = async (limit: number = 50): Promise<AutonomousAuditResponse[]> => {
  const response = await apiClient.get<AutonomousAuditResponse[]>('/system/audit', { params: { limit } });
  return response.data;
};

export const getIncidents = async (params: {
  status?: string;
  severity?: string;
  classification?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ThermalIncidentListResponse> => {
  const response = await apiClient.get<ThermalIncidentListResponse>('/incidents', { params });
  return response.data;
};

export interface CorrelatedEventItem {
  id: number;
  event_code?: string;
  detected_at?: string;
  frp?: number;
  satellite?: string;
  latitude?: number;
  longitude?: number;
  status?: string;
  confidence?: number;
}

export interface CorrelatedAlertItem {
  id: number;
  alert_code?: string;
  severity?: string;
  title?: string;
  status?: string;
  created_at?: string;
}

export const getIncidentDetail = async (id: number): Promise<{
  incident: ThermalIncidentResponse;
  events: CorrelatedEventItem[];
  alerts: CorrelatedAlertItem[];
}> => {
  const response = await apiClient.get(`/incidents/${id}`);
  return response.data;
};

export const updateIncidentStatus = async (
  id: number,
  status: string,
  analystNotes?: string
): Promise<ThermalIncidentResponse> => {
  const response = await apiClient.patch<ThermalIncidentResponse>(`/incidents/${id}/status`, {
    status,
    analyst_notes: analystNotes
  });
  return response.data;
};

// -------------------------------------------------------------
// Phase 9: Production SaaS Interfaces & Endpoints
// -------------------------------------------------------------

export interface SaasUser {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  status: string;
  email_verified: boolean;
  is_superadmin: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface SaasOrganization {
  id?: string;
  organization_id?: string;
  name: string;
  slug?: string;
  status?: string;
  plan: string;
  custom_region?: string;
  settings?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  role?: string;
  permissions?: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: SaasUser;
  active_organization_id?: string;
  role?: string;
  permissions: string[];
}

export interface SaasMember {
  id: string;
  user_id: string;
  organization_id: string;
  role: string;
  status: string;
  user_email?: string;
  user_name?: string;
  created_at: string;
}

export interface SaasInvitation {
  id: string;
  organization_id: string;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  accepted: boolean;
  created_at: string;
}

export interface SaasApiKey {
  id: string;
  organization_id: string;
  name: string;
  key_prefix: string;
  permissions: string[];
  is_active: boolean;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
}

export interface SaasApiKeyCreated extends SaasApiKey {
  raw_api_key: string;
}

export interface SaasWebhook {
  id: string;
  organization_id: string;
  url: string;
  subscribed_events: string[];
  is_active: boolean;
  created_at: string;
  last_triggered_at?: string;
  consecutive_failures: number;
}

export interface SaasPlan {
  id: string;
  name: string;
  price_inr_monthly: number;
  price_inr_annual: number;
  features: string[];
  limits: Record<string, unknown>;
}

export interface SaasSubscription {
  id: string;
  organization_id: string;
  plan: string;
  status: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  billing_email?: string;
  razorpay_subscription_id?: string;
}

export interface RazorpayCheckoutInfo {
  order_id: string;
  razorpay_key_id: string;
  amount: number;
  currency: string;
  plan: string;
  billing_cycle: string;
  organization_id: string;
  prefill_name: string;
  prefill_email: string;
}

export interface SaasUsageMetric {
  metric_name: string;
  current_value: number;
  limit_value: number;
  usage_percent: number;
}

export interface SaasUsageResponse {
  organization_id: string;
  plan: string;
  billing_period: string;
  metrics: Record<string, SaasUsageMetric>;
}

export interface PlatformOverview {
  organizations: {
    total: number;
    active: number;
    by_plan: Record<string, number>;
  };
  users: {
    total: number;
    active: number;
  };
  intelligence: {
    total_facilities_monitored: number;
    total_alerts_generated: number;
  };
  system_status: string;
}

export interface PlatformAuditLog {
  id: string;
  actor_id?: string;
  actor_email?: string;
  organization_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, unknown>;
  ip_address?: string;
  created_at: string;
}

// Auth API Methods
export const registerUser = async (data: { email: string; full_name: string; password: string; organization_name?: string }): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/auth/register', data);
  return response.data;
};

export const loginUser = async (data: { email: string; password: string }): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/auth/login', data);
  return response.data;
};

export const getMe = async (): Promise<{ user: SaasUser; organizations: SaasOrganization[] }> => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

export const logoutUser = async (): Promise<{ message: string }> => {
  const response = await apiClient.post('/auth/logout');
  return response.data;
};

export const acceptInvitation = async (data: { token: string; full_name: string; password: string }): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/auth/invitations/accept', data);
  return response.data;
};

// Organization API Methods
export const getUserOrganizations = async (): Promise<SaasOrganization[]> => {
  const response = await apiClient.get<SaasOrganization[]>('/organizations');
  return response.data;
};

export const createOrganization = async (data: { name: string; slug?: string; plan?: string }): Promise<SaasOrganization> => {
  const response = await apiClient.post<SaasOrganization>('/organizations', data);
  return response.data;
};

export const getCurrentOrganization = async (): Promise<SaasOrganization> => {
  const response = await apiClient.get<SaasOrganization>('/organizations/current');
  return response.data;
};

export const updateCurrentOrganization = async (data: { name?: string; custom_region?: string }): Promise<SaasOrganization> => {
  const response = await apiClient.patch<SaasOrganization>('/organizations/current', data);
  return response.data;
};

export const getOrganizationMembers = async (): Promise<SaasMember[]> => {
  const response = await apiClient.get<SaasMember[]>('/organizations/members');
  return response.data;
};

export const updateMemberRole = async (memberId: string, role: string): Promise<void> => {
  const response = await apiClient.patch(`/organizations/members/${memberId}/role`, { role });
  return response.data;
};

export const removeMember = async (memberId: string): Promise<void> => {
  const response = await apiClient.delete(`/organizations/members/${memberId}`);
  return response.data;
};

export const inviteMember = async (data: { email: string; role: string }): Promise<SaasInvitation> => {
  const response = await apiClient.post<SaasInvitation>('/organizations/invitations', data);
  return response.data;
};

export const getPendingInvitations = async (): Promise<SaasInvitation[]> => {
  const response = await apiClient.get<SaasInvitation[]>('/organizations/invitations');
  return response.data;
};

export const getApiKeys = async (): Promise<SaasApiKey[]> => {
  const response = await apiClient.get<SaasApiKey[]>('/organizations/api-keys');
  return response.data;
};

export const createApiKey = async (data: { name: string; permissions?: string[]; expires_in_days?: number }): Promise<SaasApiKeyCreated> => {
  const response = await apiClient.post<SaasApiKeyCreated>('/organizations/api-keys', data);
  return response.data;
};

export const revokeApiKey = async (keyId: string): Promise<void> => {
  const response = await apiClient.delete(`/organizations/api-keys/${keyId}`);
  return response.data;
};

export const getWebhooks = async (): Promise<SaasWebhook[]> => {
  const response = await apiClient.get<SaasWebhook[]>('/organizations/webhooks');
  return response.data;
};

export const createWebhook = async (data: { url: string; subscribed_events?: string[]; description?: string }): Promise<SaasWebhook> => {
  const response = await apiClient.post<SaasWebhook>('/organizations/webhooks', data);
  return response.data;
};

export const deleteWebhook = async (webhookId: string): Promise<void> => {
  const response = await apiClient.delete(`/organizations/webhooks/${webhookId}`);
  return response.data;
};

// Billing API Methods
export const getBillingPlans = async (): Promise<SaasPlan[]> => {
  const response = await apiClient.get<SaasPlan[]>('/billing/plans');
  return response.data;
};

export const getCurrentSubscription = async (): Promise<SaasSubscription> => {
  const response = await apiClient.get<SaasSubscription>('/billing/subscription');
  return response.data;
};

export const createRazorpayOrder = async (data: { plan: string; billing_cycle?: string }): Promise<RazorpayCheckoutInfo> => {
  const response = await apiClient.post<RazorpayCheckoutInfo>('/billing/create-order', data);
  return response.data;
};

export const verifyRazorpayPayment = async (data: {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
  plan: string;
}): Promise<void> => {
  const response = await apiClient.post('/billing/verify-payment', data);
  return response.data;
};

export const getOrganizationUsage = async (): Promise<SaasUsageResponse> => {
  const response = await apiClient.get<SaasUsageResponse>('/billing/usage');
  return response.data;
};

// SuperAdmin API Methods
export const getPlatformOverview = async (): Promise<PlatformOverview> => {
  const response = await apiClient.get<PlatformOverview>('/admin/overview');
  return response.data;
};

export const getAllOrganizations = async (): Promise<SaasOrganization[]> => {
  const response = await apiClient.get<SaasOrganization[]>('/admin/organizations');
  return response.data;
};

export const updateOrganizationStatus = async (orgId: string, status: string): Promise<void> => {
  const response = await apiClient.patch(`/admin/organizations/${orgId}/status`, null, { params: { status } });
  return response.data;
};

export const getPlatformAuditLogs = async (params: { limit?: number; offset?: number; action?: string } = {}): Promise<PlatformAuditLog[]> => {
  const response = await apiClient.get<PlatformAuditLog[]>('/admin/audit-logs', { params });
  return response.data;
};




