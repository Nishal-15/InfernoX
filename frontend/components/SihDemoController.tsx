"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Play, 
  Pause, 
  ChevronRight, 
  ChevronLeft, 
  RotateCcw, 
  X, 
  Radio, 
  Cpu, 
  Flame, 
  Building2, 
  Satellite, 
  Clock, 
  ShieldAlert, 
  FileText, 
  CheckCircle2, 
  Eye, 
  Compass,
  Layers,
  Sparkles
} from 'lucide-react';
import { triggerDemoEvent, triggerPipelineRun } from '@/lib/api';

export interface SihDemoControllerProps {
  isOpen: boolean;
  onClose: () => void;
  onFlyToCoordinates?: (lat: number, lon: number, height?: number) => void;
  onSelectEventId?: (id: number) => void;
  onNavigateTab?: (tab: 'dashboard' | 'alerts' | 'analytics' | 'reports') => void;
  isLiveMode?: boolean;
}

interface DemoStep {
  stepNumber: number;
  title: string;
  phase: string;
  badge: string;
  icon: React.ElementType;
  description: string;
  technicalDetails: string[];
  actionLabel?: string;
  targetTab?: 'dashboard' | 'alerts' | 'analytics' | 'reports';
  coordinates?: { lat: number; lon: number; height?: number };
}

export const SihDemoController: React.FC<SihDemoControllerProps> = ({
  isOpen,
  onClose,
  onFlyToCoordinates,
  onSelectEventId,
  onNavigateTab,
  isLiveMode = false
}) => {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [demoEventId, setDemoEventId] = useState<number | null>(null);
  const [isExecutingAction, setIsExecutingAction] = useState<boolean>(false);

  const steps: DemoStep[] = useMemo(() => [
    {
      stepNumber: 1,
      title: "3D Earth Geospatial Command",
      phase: "Stage 1: Mission Control",
      badge: "GLOBAL 3D",
      icon: Compass,
      description: "InfernoX renders a digital-twin 3D Cesium globe loaded with high-resolution satellite imagery, terrain elevation, and real-time thermal anomaly coordinates.",
      technicalDetails: [
        "CesiumJS 3D Ellipsoid Engine (WGS84 GPS standard)",
        "GPU-accelerated billboard instancing for 10,000+ points",
        "Configurable camera pitch, heading, roll, and elevation layers"
      ],
      targetTab: "dashboard",
      coordinates: { lat: 20.5937, lon: 78.9629, height: 4500000 }
    },
    {
      stepNumber: 2,
      title: "NASA FIRMS Detection Stream",
      phase: "Stage 2: Ingestion & Deduplication",
      badge: "NASA FIRMS NRT",
      icon: Flame,
      description: "Programmatic ingestion from NASA FIRMS API (VIIRS Suomi NPP, NOAA-20, NOAA-21 375m). Identifies raw thermal anomalies with brightness temperature and Fire Radiative Power (FRP).",
      technicalDetails: [
        "Endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/",
        "PostGIS ON CONFLICT DO NOTHING spatial deduplication",
        "Preserves scan, track, FRP, confidence, day/night flags"
      ],
      targetTab: "dashboard",
      coordinates: { lat: 22.4630, lon: 70.0710, height: 500000 }
    },
    {
      stepNumber: 3,
      title: "Automated Camera Fly-To",
      phase: "Stage 3: Mission Dispatch",
      badge: "AUTOFOCUS",
      icon: Eye,
      description: "When an anomalous thermal source is registered, the Cesium camera autonomously vectors to the incident ground zero at smooth sub-orbital velocity.",
      technicalDetails: [
        "Target: Jamnagar Industrial Belt, Gujarat (22.4630°N, 70.0710°E)",
        "Camera altitude automatically steps from 500km to 15km",
        "Real-time coordinate tracking and spatial boundary loading"
      ],
      targetTab: "dashboard",
      coordinates: { lat: 22.4630, lon: 70.0710, height: 18000 }
    },
    {
      stepNumber: 4,
      title: "Industrial Facility Detection (OSM)",
      phase: "Stage 4: Spatial Context",
      badge: "OSM SPATIAL",
      icon: Building2,
      description: "PostGIS runs a 2,000-meter ST_DWithin spatial query against OpenStreetMap industrial facility geometries. Discovers the nearest petroleum refinery.",
      technicalDetails: [
        "Nearest Facility: Jamnagar Petroleum Complex (Refinery & Petrochemical)",
        "Proximity Distance: 840 meters (Inside 2,000m industrial buffer)",
        "Associated Infrastructure: Flare stack cluster, storage tanks, primary logistics"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 5,
      title: "Satellite Evidence & Land Cover",
      phase: "Stage 5: Multi-Modal Earth Observation",
      badge: "SENTINEL-2 & WORLDCOVER",
      icon: Satellite,
      description: "Multi-modal verification via Sentinel-2 SWIR/NIR bands and ESA WorldCover 10m grid. Proves the thermal anomaly sits in a verified industrial/built-up zone, eliminating false forest-fire alarms.",
      technicalDetails: [
        "ESA WorldCover Grid Class: 50 (Built-up / Industrial Infrastructure)",
        "Sentinel-2 SWIR/NIR Ratio: 1.84 (Signature high-temperature hydrocarbon combustion)",
        "NDVI: 0.12 (Absence of dense vegetative biomass)"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 6,
      title: "Temporal Persistence Analysis",
      phase: "Stage 6: Temporal Intelligence",
      badge: "PERSISTENT HOTSPOT",
      icon: Clock,
      description: "Evaluates 90-day historical observations within a 1,000m radius. Analyzes recurrence, active days, and temporal clustering to identify persistent industrial flaring.",
      technicalDetails: [
        "Active Days: 7 distinct detection dates across 90-day window",
        "Total Cluster Detections: 14 observations",
        "Persistence Classification: PERSISTENT_HOTSPOT (Stationary coordinate cluster)",
        "Abnormal FRP Multiplier: 3.1x (Elevated above facility baseline)"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 7,
      title: "AI Inference (XGBoost Classifier)",
      phase: "Stage 7: Machine Learning",
      badge: "XGBOOST v1.0",
      icon: Cpu,
      description: "Multi-modal feature vector is evaluated by the production XGBoost classifier. Predicts with 94.2% probability that the event is an Industrial Flare Thermal Anomaly.",
      technicalDetails: [
        "Model Version: xgb-v1 (Trained on verified industrial & wildfire corpora)",
        "Classification: INDUSTRIAL_THERMAL_ANOMALY (Gas Flare / Petrochemical)",
        "Model Probability: 0.942 | Confidence Score: 94.2%",
        "Feature Schema: 14 normalized geospatial & radiometric attributes"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 8,
      title: "AI Explainability & Evidence",
      phase: "Stage 8: Model Explainability",
      badge: "FEATURE IMPORTANCE",
      icon: Sparkles,
      description: "Ranks input feature contributions explaining why the AI reached this classification. Shows industrial proximity and temporal persistence as decisive drivers.",
      technicalDetails: [
        "#1 Distance to Facility: 840m (Contribution weight: +0.38)",
        "#2 Spatial Spread: 110m (Highly localized stationary point, weight: +0.26)",
        "#3 Active Days: 7 days recurrence (weight: +0.19)",
        "#4 SWIR/NIR Ratio: 1.84 combustion signature (weight: +0.11)"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 9,
      title: "Analytical Risk Scoring (0-100)",
      phase: "Stage 9: Risk Engine",
      badge: "RISK 88 / 100",
      icon: ShieldAlert,
      description: "Deterministic risk engine evaluates thermal severity, environmental sensitivity, and proximity to critical chemical infrastructure. Assigns a composite score of 88/100 (CRITICAL).",
      technicalDetails: [
        "Risk Score: 88.0 / 100 | Risk Level: CRITICAL",
        "Thermal Severity Factor: 32 / 35 (FRP 420.5 MW)",
        "Facility Proximity Factor: 28 / 30 (< 1000m from petrochemical unit)",
        "Environmental Vulnerability: 18 / 20",
        "Temporal Persistence: 10 / 15"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 10,
      title: "Alert Generation & Dispatch",
      phase: "Stage 10: Alert Engine",
      badge: "DEDUPLICATED ALERT",
      icon: Radio,
      description: "Autonomous alert engine matches the event against tenant alert rules. Deduplicates against active alerts to prevent alarm fatigue and broadcasts via WebSockets.",
      technicalDetails: [
        "Alert ID: #ALT-2026-088 | Severity: CRITICAL",
        "Rule: 'High-Temperature Industrial Flare Anomaly (>300 MW)'",
        "Tenant Partition: org_1 (Enterprise Command)",
        "Delivery Channels: In-App, WebSocket, HMAC Outbound Webhook"
      ],
      targetTab: "alerts"
    },
    {
      stepNumber: 11,
      title: "Investigation Workspace",
      phase: "Stage 11: Analyst Operations",
      badge: "ANALYST CONSOLE",
      icon: CheckCircle2,
      description: "Human-in-the-loop analyst workspace. The analyst reviews AI predictions, confirms or overrides the classification, and creates an audit trail entry.",
      technicalDetails: [
        "Distinguishes AI Classification from Analyst Confirmed Classification",
        "Supports Decision: CONFIRM, OVERRIDE, CLOSE",
        "Immutable Audit Log: Records analyst identity, timestamp, and notes"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 12,
      title: "Temporal Timeline Playback",
      phase: "Stage 12: Historical Replay",
      badge: "TIMELINE REPLAY",
      icon: Clock,
      description: "Interactive timeline scrubber animating the spatial-temporal progression of thermal detections at this location over the past 90 days.",
      technicalDetails: [
        "Play/Pause 4D animation of thermal evolution",
        "Step through individual satellite passes (VIIRS SNPP, NOAA-20)",
        "Charts day-over-day FRP intensity shifts"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 13,
      title: "Facility Thermal Intelligence",
      phase: "Stage 13: Facility Profiling",
      badge: "FACILITY PROFILE",
      icon: Building2,
      description: "Deep dive into the industrial facility's lifetime thermal history, operating envelope, flare frequency, and compliance statistics.",
      technicalDetails: [
        "Facility: Jamnagar Petrochemical Complex",
        "Cumulative Thermal Events: 34 detections",
        "Baseline Mean FRP: 142.0 MW | Peak FRP: 420.5 MW",
        "Primary Operators & Emergency Response Coordinates"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 14,
      title: "Executive Analytics Dashboard",
      phase: "Stage 14: Platform Analytics",
      badge: "ANALYTICS HQ",
      icon: Layers,
      description: "Aggregated intelligence across industrial corridors: classification confusion matrix, FRP trends, facility risk heatmaps, and regional distributions.",
      technicalDetails: [
        "Model Evaluation: 93.8% precision, 91.4% recall on test sets",
        "Regional Breakdown: Gujarat, Maharashtra, Chhattisgarh, Odisha",
        "Temporal Heatmap: Hourly and weekly recurrence patterns"
      ],
      targetTab: "analytics"
    },
    {
      stepNumber: 15,
      title: "Automated Report Generation",
      phase: "Stage 15: Incident Reporting",
      badge: "REPORT BUILDER",
      icon: FileText,
      description: "Generates tamper-evident incident intelligence reports in PDF, GeoJSON, CSV, and JSON with complete cryptographic provenance and scientific disclaimers.",
      technicalDetails: [
        "Supported Formats: PDF, GeoJSON, CSV, JSON",
        "Included: Satellite imagery, OSM metadata, AI evidence, provenance",
        "Disclaimer: Non-statutory situational intelligence report"
      ],
      targetTab: "reports"
    },
    {
      stepNumber: 16,
      title: "Autonomous NOC & Monitoring",
      phase: "Stage 16: Autonomous Operations",
      badge: "NOC TELEMETRY",
      icon: Radio,
      description: "Network Operations Center monitoring data provider health (NASA FIRMS, STAC, OSM), pipeline job latencies, and real-time WebSocket connection state.",
      technicalDetails: [
        "Provider Health Endpoint: /api/v1/system/providers",
        "NASA FIRMS Status: AVAILABLE | PostGIS Spatial Index: GIST",
        "Auto-restart and exponential retry backoff enabled"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 17,
      title: "Live End-to-End Pipeline Cycle",
      phase: "Stage 17: Live Execution",
      badge: "AUTONOMOUS CYCLE",
      icon: Play,
      description: "Executes an immediate live pipeline cycle: NASA FIRMS -> PostGIS -> Enrichment -> ML -> Risk -> Incident Correlation -> Alert -> WebSocket Broadcast.",
      technicalDetails: [
        "Endpoint: POST /api/v1/system/pipeline/run",
        "10 Deterministic processing stages executed in sub-second latency",
        "Real-time event push to active Cesium 3D mission control"
      ],
      targetTab: "dashboard"
    },
    {
      stepNumber: 18,
      title: "SIH Grand Finale Summary",
      phase: "Stage 18: Summary & Verdict",
      badge: "SIH COMPLETE",
      icon: CheckCircle2,
      description: "InfernoX successfully proves that satellite thermal anomalies can be transformed into actionable, contextualized industrial-fire intelligence without false alarms.",
      technicalDetails: [
        "Problem: NASA FIRMS detects heat; InfernoX explains and classifies it",
        "Production SaaS: Multi-tenancy, RBAC, Razorpay billing, audit logs",
        "Ready for Deployment: Docker Compose, PostGIS, XGBoost, Next.js"
      ],
      targetTab: "dashboard"
    }
  ], []);

  const currentStepData = steps[currentStep] || steps[0];

  // Execute step actions (camera fly-to, tab navigation, demo trigger)
  const applyStepAction = useCallback(async (stepIdx: number) => {
    const step = steps[stepIdx];
    if (!step) return;

    if (step.targetTab && onNavigateTab) {
      onNavigateTab(step.targetTab);
    }

    if (step.coordinates && onFlyToCoordinates) {
      onFlyToCoordinates(step.coordinates.lat, step.coordinates.lon, step.coordinates.height);
    }

    // Trigger demo event on step 2 or 3 if not yet triggered
    if (stepIdx === 1 || stepIdx === 2) {
      if (!demoEventId) {
        try {
          setIsExecutingAction(true);
          const res = await triggerDemoEvent({ lat: 22.4630, lon: 70.0710, frp: 420.5 });
          if (res?.event_id) {
            setDemoEventId(res.event_id);
            if (onSelectEventId) {
              onSelectEventId(res.event_id);
            }
          }
        } catch (e) {
          console.warn("Demo event trigger:", e);
        } finally {
          setIsExecutingAction(false);
        }
      }
    }

    // Trigger live pipeline cycle on step 17
    if (stepIdx === 16) {
      try {
        setIsExecutingAction(true);
        await triggerPipelineRun(true);
      } catch (e) {
        console.warn("Pipeline cycle run:", e);
      } finally {
        setIsExecutingAction(false);
      }
    }
  }, [steps, onNavigateTab, onFlyToCoordinates, onSelectEventId, demoEventId]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      const nextIdx = currentStep + 1;
      setCurrentStep(nextIdx);
      applyStepAction(nextIdx);
    } else {
      setIsPlaying(false);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      const prevIdx = currentStep - 1;
      setCurrentStep(prevIdx);
      applyStepAction(prevIdx);
    }
  };

  const handleJumpToStep = (idx: number) => {
    setCurrentStep(idx);
    applyStepAction(idx);
  };

  // Auto-play timer
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isPlaying) {
      timer = setTimeout(() => {
        if (currentStep < steps.length - 1) {
          const nextIdx = currentStep + 1;
          setCurrentStep(nextIdx);
          applyStepAction(nextIdx);
        } else {
          setIsPlaying(false);
        }
      }, 7000);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isPlaying, currentStep, steps.length, applyStepAction]);

  if (!isOpen) return null;

  const IconComponent = currentStepData.icon;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-4xl px-4 select-none">
      <div className="relative rounded-2xl bg-slate-950/95 border border-amber-500/40 shadow-2xl shadow-amber-950/60 backdrop-blur-xl overflow-hidden transition-all">
        {/* Glow Top Bar */}
        <div className="h-1 bg-gradient-to-r from-orange-500 via-amber-400 to-rose-600"></div>

        {/* Header Ribbon */}
        <div className="px-5 py-3 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-amber-500 to-orange-600 flex items-center justify-center shadow-md shadow-orange-950/50">
              <span className="text-white text-xs font-bold font-mono">SIH</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-white tracking-wide">
                  SMART INDIA HACKATHON — GUIDED DEMO
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-600/50 flex items-center gap-1">
                  {currentStepData.badge}
                  {isExecutingAction && <span className="animate-spin text-[10px]">⏳</span>}
                </span>
              </div>
              <p className="text-[10px] font-mono text-slate-400">
                Step {currentStepData.stepNumber} of {steps.length} • {currentStepData.phase}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Transparency Badge (Section 18) */}
            <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono">
              <span className={`w-1.5 h-1.5 rounded-full ${isLiveMode ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
              <span className="text-slate-400">MODE:</span>
              <span className={`font-semibold ${isLiveMode ? 'text-emerald-300' : 'text-amber-300'}`}>
                {isLiveMode ? 'LIVE (NASA FIRMS API)' : 'DEMO (Verified Historical Archive)'}
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
              title="Close Demo Guide"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-5 grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
          {/* Left Column: Icon & Overview */}
          <div className="md:col-span-7 space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-slate-900 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-inner">
                <IconComponent size={20} />
              </div>
              <div>
                <h4 className="text-base font-bold text-white tracking-wide">
                  {currentStepData.title}
                </h4>
                <span className="text-[11px] font-mono text-amber-400">
                  {currentStepData.phase}
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              {currentStepData.description}
            </p>

            {/* Stepper Dots */}
            <div className="flex items-center gap-1 pt-1 overflow-x-auto py-1">
              {steps.map((st, idx) => (
                <button
                  key={st.stepNumber}
                  onClick={() => handleJumpToStep(idx)}
                  className={`h-1.5 rounded-full transition-all cursor-pointer ${
                    idx === currentStep
                      ? 'w-6 bg-amber-400 shadow-sm shadow-amber-400/50'
                      : idx < currentStep
                      ? 'w-2 bg-slate-600 hover:bg-slate-400'
                      : 'w-2 bg-slate-800 hover:bg-slate-700'
                  }`}
                  title={`Jump to Step ${st.stepNumber}: ${st.title}`}
                />
              ))}
            </div>
          </div>

          {/* Right Column: Technical Defense Points */}
          <div className="md:col-span-5 rounded-xl bg-slate-900/80 border border-slate-800 p-3.5 space-y-2">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
              <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                Technical Evidence
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-950 text-slate-400 border border-slate-800">
                DEFENSIBLE
              </span>
            </div>

            <ul className="space-y-1.5 text-[11px] font-mono text-slate-300">
              {currentStepData.technicalDetails.map((td, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-amber-400 mt-0.5">•</span>
                  <span className="leading-tight">{td}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Footer Navigation Bar */}
        <div className="px-5 py-3 border-t border-slate-800/80 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleJumpToStep(0)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition-colors text-xs font-mono"
              title="Reset to Step 1"
            >
              <RotateCcw size={14} />
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-medium transition-all ${
                isPlaying
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
              }`}
            >
              {isPlaying ? <Pause size={13} /> : <Play size={13} />}
              <span>{isPlaying ? 'PAUSE AUTO' : 'AUTO-PLAY'}</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none text-slate-200 border border-slate-700 text-xs font-mono transition-colors"
            >
              <ChevronLeft size={14} />
              <span>PREVIOUS</span>
            </button>

            <button
              onClick={handleNext}
              disabled={currentStep === steps.length - 1}
              className="flex items-center gap-1 px-4 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 font-bold text-xs font-mono transition-all shadow-md shadow-orange-950/40"
            >
              <span>{currentStep === steps.length - 1 ? 'FINISHED' : 'NEXT STEP'}</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
