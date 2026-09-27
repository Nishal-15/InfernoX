"use client";

import React from 'react';
import { RiskCard } from './RiskCard';
import { ClassificationCard } from './ClassificationCard';
import { TemporalCard } from './TemporalCard';
import { LandCoverCard } from './LandCoverCard';
import { FacilityContextCard } from './FacilityContextCard';
import { SatelliteCard } from './SatelliteCard';
import { AnalystReviewCard } from './AnalystReviewCard';
import { DataProvenanceCard } from './DataProvenanceCard';

export interface InvestigationData {
  event: {
    id: number;
    event_code?: string;
    detected_at?: string;
    latitude: number;
    longitude: number;
    confidence?: number;
    frp?: number;
    brightness_temperature?: number;
    satellite?: string;
    instrument?: string;
    status?: string;
    source?: string;
  };
  classification: {
    classification: string;
    confidence_score?: number;
    model_probability?: number;
    validated_confidence?: number;
    confidence_type?: string;
    priority_score?: number;
    priority_level?: string;
    model_type?: string;
    model_version?: string;
    evidence_factors?: string[];
    explanation?: Array<string | { text?: string }>;
    probabilities?: Record<string, number>;
    fallback?: boolean;
    is_calibrated?: boolean;
  };
  temporal_analysis: {
    first_detected?: string;
    last_detected?: string;
    active_days?: number;
    detections_count?: number;
    duration_days?: number;
    mean_frp?: number;
    max_frp?: number;
    status?: string;
    cluster_id?: string;
  };
  nearby_facilities?: Array<{
    id: number;
    osm_id?: string;
    name: string;
    facility_type: string;
    operator?: string;
    distance_meters: number;
    latitude: number;
    longitude: number;
  }>;
  nearest_facility?: {
    id?: number;
    osm_id?: string;
    name?: string;
    facility_type?: string;
    operator?: string;
    distance_meters?: number;
    latitude?: number;
    longitude?: number;
  } | null;
  satellite_evidence: {
    scene_id?: string;
    acquisition_time?: string;
    cloud_percentage?: number;
    evidence_status?: string;
    provider?: string;
    processing_level?: string;
    indices?: {
      ndvi?: number | null;
      nbr?: number | null;
      ndwi?: number | null;
      swir_nir_ratio?: number | null;
      burn_scar_indicator?: boolean;
    };
  };
  land_cover: {
    land_cover_class?: number;
    land_cover_name?: string;
    category?: string;
    source?: string;
    dataset_version?: string;
    tile_id?: string;
    confidence?: number;
  };
  historical_events?: Array<{
    id: number;
    detected_at?: string;
    frp?: number;
    confidence?: number;
    latitude: number;
    longitude: number;
    is_current?: boolean;
  }>;
  reviews?: Array<{
    id: number;
    analyst_id: string;
    decision: string;
    comment?: string;
    previous_classification?: string;
    final_classification?: string;
    created_at?: string;
  }>;
  provenance: {
    thermal_source?: string;
    infrastructure_source?: string;
    land_cover_source?: string;
    satellite_source?: string;
    ml_model_version?: string;
    feature_schema_version?: string;
    analysis_timestamp?: string;
  };
  risk_assessment?: {
    risk_score: number;
    risk_level: string;
    risk_model_version: string;
    breakdown?: {
      classification_score: number;
      intensity_score: number;
      temporal_score: number;
      infrastructure_score: number;
      evidence_score: number;
      explanation?: string[];
    };
    calculated_at?: string;
  };
}

interface EventPanelProps {
  data: InvestigationData | null;
  isLoading: boolean;
  onClose: () => void;
  onInvestigate: () => void;
  onOpenFacilityModal: (facilityId: number) => void;
  onOpenCompareModal: () => void;
  onGenerateReport?: (eventId: number) => void;
  onStatusUpdated: (newStatus: string) => void;
  onToggleLayer?: (layer: 'showSatellite' | 'showNdvi' | 'showNbr') => void;
  layers?: {
    showSatellite?: boolean;
    showNdvi?: boolean;
    showNbr?: boolean;
  };
}

export const EventPanel: React.FC<EventPanelProps> = ({
  data,
  isLoading,
  onClose,
  onInvestigate,
  onOpenFacilityModal,
  onOpenCompareModal,
  onGenerateReport,
  onStatusUpdated,
  onToggleLayer,
  layers
}) => {
  if (isLoading) {
    return (
      <div className="w-96 bg-slate-950/95 border-l border-slate-800 p-6 flex flex-col items-center justify-center text-center font-mono z-30 select-none backdrop-blur-xl">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mb-3"></div>
        <div className="text-xs text-slate-300 font-semibold">SYNTHESIZING INVESTIGATION DOSSIER</div>
        <div className="text-[10px] text-slate-500 mt-1">Cross-referencing FIRMS, Sentinel-2, WorldCover, & ML inference...</div>
      </div>
    );
  }

  if (!data || !data.event) {
    return (
      <div className="w-96 bg-slate-950/95 border-l border-slate-800 p-6 flex flex-col items-center justify-center text-center font-mono z-30 select-none backdrop-blur-xl text-slate-500">
        <span className="text-3xl mb-2">🛰️</span>
        <div className="text-xs font-semibold text-slate-400">NO EVENT SELECTED</div>
        <div className="text-[10px] text-slate-600 mt-1 max-w-xs">
          Select a thermal anomaly on the 3D globe or search for an incident code to open tactical investigation.
        </div>
      </div>
    );
  }

  const { event, classification, temporal_analysis, nearest_facility, nearby_facilities, satellite_evidence, land_cover, reviews, provenance, risk_assessment } = data;
  const eventCode = event.event_code || `#INF-2026-${event.id.toString().padStart(6, '0')}`;

  return (
    <aside className="w-96 lg:w-[410px] bg-slate-950/95 border-l border-slate-800 flex flex-col h-full z-30 select-none backdrop-blur-2xl shadow-2xl">
      {/* Header Bar */}
      <div className="p-3.5 border-b border-slate-800 flex items-start justify-between bg-slate-900/60 font-mono">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-amber-300 tracking-wider">
              {eventCode}
            </span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold uppercase border ${
              event.status === 'INVESTIGATING' ? 'bg-amber-950 text-amber-400 border-amber-800 animate-pulse' :
              event.status === 'CONFIRMED' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' :
              event.status === 'REJECTED' ? 'bg-rose-950 text-rose-400 border-rose-800' :
              'bg-blue-950 text-blue-400 border-blue-800'
            }`}>
              {event.status || 'NEW'}
            </span>
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Detected: {event.detected_at ? new Date(event.detected_at).toUTCString().replace('GMT', 'UTC') : 'N/A'}
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-slate-500 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
          title="Close Investigation Panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Primary Investigation Action Button */}
      <div className="p-3 border-b border-slate-800/80 bg-slate-950">
        <button
          onClick={onInvestigate}
          className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-red-600 via-orange-600 to-amber-500 hover:from-red-500 hover:via-orange-500 hover:to-amber-400 text-white font-mono font-bold text-xs tracking-wider shadow-lg shadow-red-950/50 flex items-center justify-center gap-2 transition-all group"
        >
          <span className="text-base group-hover:scale-110 transition-transform">🎯</span>
          <span>INVESTIGATE EVENT (AI 3D FLIGHT)</span>
        </button>
      </div>

      {/* Scrollable Intelligence Dossier Cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Phase 6 Analytical Risk Engine Assessment */}
        <RiskCard
          riskScore={risk_assessment?.risk_score ?? classification?.priority_score ?? Math.min(Math.round((event.frp || 10) * 1.2), 95)}
          riskLevel={risk_assessment?.risk_level ?? classification?.priority_level}
          modelVersion={risk_assessment?.risk_model_version || "risk-v1"}
          calculatedAt={risk_assessment?.calculated_at}
          breakdown={risk_assessment?.breakdown}
        />

        {/* ML Classification Card */}
        <ClassificationCard
          classification={classification?.classification || 'Unknown'}
          modelType={classification?.model_type}
          modelVersion={classification?.model_version || 'xgb-v1'}
          modelProbability={classification?.model_probability ?? classification?.confidence_score}
          confidenceScore={classification?.confidence_score}
          isCalibrated={classification?.is_calibrated}
          priorityScore={classification?.priority_score}
          priorityLevel={classification?.priority_level}
          evidenceFactors={classification?.evidence_factors}
          explanation={classification?.explanation}
          probabilities={classification?.probabilities}
          fallback={classification?.fallback}
        />

        {/* Temporal Analysis Card */}
        <TemporalCard
          firstDetected={temporal_analysis?.first_detected}
          lastDetected={temporal_analysis?.last_detected}
          activeDays={temporal_analysis?.active_days}
          detectionsCount={temporal_analysis?.detections_count}
          durationDays={temporal_analysis?.duration_days}
          meanFrp={temporal_analysis?.mean_frp}
          maxFrp={temporal_analysis?.max_frp}
          status={temporal_analysis?.status}
          clusterId={temporal_analysis?.cluster_id}
        />

        {/* Land Cover Context Card */}
        <LandCoverCard
          landCoverClass={land_cover?.land_cover_class}
          landCoverName={land_cover?.land_cover_name}
          category={land_cover?.category}
          source={land_cover?.source}
          datasetVersion={land_cover?.dataset_version}
          tileId={land_cover?.tile_id}
          confidence={land_cover?.confidence}
        />

        {/* Nearby Infrastructure Card */}
        <FacilityContextCard
          facility={nearest_facility}
          nearbyCount={nearby_facilities?.length}
          onInspectFacility={onOpenFacilityModal}
        />

        {/* Satellite Remote Sensing Card */}
        <SatelliteCard
          sceneId={satellite_evidence?.scene_id}
          acquisitionTime={satellite_evidence?.acquisition_time}
          cloudPercentage={satellite_evidence?.cloud_percentage}
          evidenceStatus={satellite_evidence?.evidence_status}
          provider={satellite_evidence?.provider}
          processingLevel={satellite_evidence?.processing_level}
          indices={satellite_evidence?.indices}
          onToggleLayer={onToggleLayer}
          layers={layers}
        />

        {/* Analyst Review & Transition Card */}
        <AnalystReviewCard
          eventId={event.id}
          currentStatus={event.status || 'NEW'}
          initialReviews={reviews}
          originalClassification={classification?.classification}
          onStatusUpdated={onStatusUpdated}
        />

        {/* Side-by-side Compare CTA */}
        <div className="pt-1 space-y-2">
          <button
            onClick={onOpenCompareModal}
            className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-850 border border-slate-700 hover:border-slate-600 text-slate-300 font-mono text-xs flex items-center justify-center gap-2 transition-all shadow"
          >
            <span>⚖️</span>
            <span>Compare with Another Event</span>
          </button>

          {onGenerateReport && (
            <button
              onClick={() => onGenerateReport(event.id)}
              className="w-full py-2 px-3 rounded-lg bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 font-mono text-xs flex items-center justify-center gap-2 transition-all shadow"
            >
              <span>📄</span>
              <span>Generate Incident Dossier (PDF/CSV)</span>
            </button>
          )}
        </div>

        {/* Data Provenance Card */}
        <DataProvenanceCard provenance={provenance} />
      </div>
    </aside>
  );
};
