"use client";

import React from 'react';
import { 
  X, 
  Flame, 
  AlertTriangle, 
  CheckCircle2, 
  Cpu, 
  ShieldCheck, 
  Globe2, 
  Satellite, 
  Database, 
  ArrowRight 
} from 'lucide-react';

export interface SihLandingExplainerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartDemo: () => void;
}

export const SihLandingExplainerModal: React.FC<SihLandingExplainerModalProps> = ({
  isOpen,
  onClose,
  onStartDemo
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md select-none animate-fadeIn">
      <div className="relative w-full max-w-3xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Glow accent */}
        <div className="h-1.5 bg-gradient-to-r from-orange-500 via-amber-400 to-rose-600"></div>

        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-orange-600 to-red-500 flex items-center justify-center shadow-lg shadow-orange-950/50">
              <span className="text-white text-base">🔥</span>
            </div>
            <div>
              <h2 className="text-base font-bold font-mono text-white tracking-wide flex items-center gap-2">
                INFERNO<span className="text-orange-400">X</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-950/80 text-orange-300 border border-orange-700/60 uppercase">
                  SIH Defense Brief
                </span>
              </h2>
              <p className="text-xs font-mono text-slate-400">
                AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-300 text-xs font-sans">
          {/* Section 1: The Core Scientific Problem */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-4 space-y-2.5">
            <div className="flex items-center gap-2 text-rose-400 font-mono font-bold text-xs uppercase tracking-wider">
              <AlertTriangle size={15} />
              <span>1. The Problem with Raw Satellite Thermal Anomaly Data</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              NASA FIRMS (Fire Information for Resource Management System) detects pixel-level infrared thermal anomalies globally using satellites like VIIRS and MODIS. 
              However, <strong>a raw thermal detection does not indicate what is burning</strong>:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
              <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                ⚠️ Petrochemical Gas Flare
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                ⚠️ Wildfire / Forest Fire
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                ⚠️ Agricultural Stubble Burn
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                ⚠️ Steel / Kiln Furnace
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                ⚠️ Open-Cast Coal Mine
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                ⚠️ Solar / Roof Glint Artifact
              </div>
            </div>
            <p className="text-slate-400 text-[11px] italic">
              Without spatial enrichment and machine learning, emergency responders suffer from massive false-alarm fatigue, sending fire units to operational industrial flare stacks.
            </p>
          </div>

          {/* Section 2: The InfernoX Solution Architecture */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-4 space-y-3">
            <div className="flex items-center gap-2 text-amber-400 font-mono font-bold text-xs uppercase tracking-wider">
              <CheckCircle2 size={15} />
              <span>2. The InfernoX Multi-Modal Intelligence Solution</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              InfernoX bridges raw satellite observations to actionable emergency decision-making through a deterministic 7-step intelligence pipeline:
            </p>

            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] text-slate-200">
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700">DETECT</span>
              <ArrowRight size={12} className="text-amber-400" />
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700">ENRICH (OSM)</span>
              <ArrowRight size={12} className="text-amber-400" />
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700">CLASSIFY (ML)</span>
              <ArrowRight size={12} className="text-amber-400" />
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700">INVESTIGATE</span>
              <ArrowRight size={12} className="text-amber-400" />
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700">SCORE RISK</span>
              <ArrowRight size={12} className="text-amber-400" />
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700">ALERT</span>
              <ArrowRight size={12} className="text-amber-400" />
              <span className="px-2 py-1 rounded bg-amber-950 border border-amber-600 text-amber-300 font-bold">MONITOR</span>
            </div>
          </div>

          {/* Section 3: Defensible Technology Stack */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-4 space-y-3">
            <div className="flex items-center gap-2 text-cyan-400 font-mono font-bold text-xs uppercase tracking-wider">
              <Cpu size={15} />
              <span>3. Defensible Technology Stack & Data Sources</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px] font-mono">
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Flame size={14} className="text-orange-400" />
                  <span>NASA FIRMS NRT API</span>
                </div>
                <p className="text-slate-400 text-[10px]">
                  Official operational domain: <code className="text-cyan-300">firms.modaps.eosdis.nasa.gov</code>. Near real-time VIIRS 375m & MODIS 1km active fire feeds.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Database size={14} className="text-emerald-400" />
                  <span>PostgreSQL + PostGIS</span>
                </div>
                <p className="text-slate-400 text-[10px]">
                  Enterprise spatial indexing via GIST, ST_DWithin 2km proximity calculations, and ON CONFLICT deduplication.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Satellite size={14} className="text-indigo-400" />
                  <span>Sentinel-2 & WorldCover</span>
                </div>
                <p className="text-slate-400 text-[10px]">
                  AWS Earth Search STAC for SWIR/NIR combustion verification + ESA WorldCover 10m global land classification.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                <div className="flex items-center gap-2 text-white font-semibold">
                  <Globe2 size={14} className="text-cyan-400" />
                  <span>CesiumJS 3D Mission Control</span>
                </div>
                <p className="text-slate-400 text-[10px]">
                  GPU-instanced digital-twin geospatial globe with autonomous camera fly-to, cluster heatmaps, and spatial rings.
                </p>
              </div>
            </div>
          </div>

          {/* Section 4: Production SaaS Governance */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-4 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 font-mono font-bold text-xs uppercase tracking-wider">
              <ShieldCheck size={15} />
              <span>4. Production SaaS & Security Posture</span>
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Built as a multi-tenant platform with Argon2id password hashing, PyJWT tokens, 4-tier RBAC authorization, SHA-256 hashed API keys, HMAC-signed webhooks, Razorpay billing integration, and tenant-partitioned WebSockets.
            </p>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-800/80 flex items-center justify-between bg-slate-950/80">
          <div className="text-[11px] font-mono text-slate-500">
            Smart India Hackathon • Problem Statement SIH-2024
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs transition-colors"
            >
              Explore Freely
            </button>
            <button
              onClick={() => {
                onClose();
                onStartDemo();
              }}
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-400 hover:to-amber-400 text-slate-950 font-bold font-mono text-xs shadow-lg shadow-orange-950/50 transition-all flex items-center gap-1.5"
            >
              <span>Launch 18-Step Guided Demo</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
