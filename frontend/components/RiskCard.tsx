"use client";

import React, { useState } from 'react';

interface RiskFactor {
  category: string;
  contribution_points: number;
  max_points: number;
  description: string;
}

export interface RiskAssessmentData {
  risk_score: number;
  risk_level: string;
  risk_model_version?: string;
  calculated_at?: string;
  breakdown?: {
    factors?: RiskFactor[];
    total_score?: number;
    risk_level?: string;
    model_version?: string;
    classification_score?: number;
    intensity_score?: number;
    temporal_score?: number;
    infrastructure_score?: number;
    evidence_score?: number;
    explanation?: string[];
  };
}

export interface RiskCardProps {
  riskData?: RiskAssessmentData | null;
  riskScore?: number;
  riskLevel?: string;
  modelVersion?: string;
  calculatedAt?: string;
  breakdown?: {
    factors?: RiskFactor[];
    classification_score?: number;
    intensity_score?: number;
    temporal_score?: number;
    infrastructure_score?: number;
    evidence_score?: number;
    explanation?: string[];
  } | null;
  onViewHistory?: () => void;
}

export const RiskCard: React.FC<RiskCardProps> = ({
  riskData,
  riskScore,
  riskLevel,
  modelVersion,
  breakdown,
  onViewHistory
}) => {
  const [expanded, setExpanded] = useState(false);

  const score = riskData?.risk_score ?? riskScore ?? 0;
  const level = (riskData?.risk_level ?? riskLevel ?? (score >= 75 ? 'CRITICAL' : score >= 50 ? 'HIGH' : score >= 25 ? 'MODERATE' : 'LOW')).toUpperCase();
  const effectiveModelVersion = riskData?.risk_model_version ?? modelVersion ?? 'risk-v1';
  
  const rawBreakdown = riskData?.breakdown ?? breakdown;
  const factors: RiskFactor[] = rawBreakdown?.factors ? [...rawBreakdown.factors] : [];

  if (factors.length === 0 && rawBreakdown) {
    if (rawBreakdown.classification_score !== undefined) {
      factors.push({
        category: 'Classification Impact',
        contribution_points: rawBreakdown.classification_score,
        max_points: 25,
        description: 'Analytical risk weighting assigned based on event classification'
      });
    }
    if (rawBreakdown.intensity_score !== undefined) {
      factors.push({
        category: 'Thermal Radiative Power (FRP)',
        contribution_points: rawBreakdown.intensity_score,
        max_points: 25,
        description: 'Radiative intensity and peak power excursion above background'
      });
    }
    if (rawBreakdown.temporal_score !== undefined) {
      factors.push({
        category: 'Temporal Behavior & Persistence',
        contribution_points: rawBreakdown.temporal_score,
        max_points: 20,
        description: 'Cluster detection count, duration days, and persistent reactivation'
      });
    }
    if (rawBreakdown.infrastructure_score !== undefined) {
      factors.push({
        category: 'Infrastructure & Hazard Proximity',
        contribution_points: rawBreakdown.infrastructure_score,
        max_points: 20,
        description: 'Geospatial proximity to industrial plant, refinery, or pipeline'
      });
    }
    if (rawBreakdown.evidence_score !== undefined) {
      factors.push({
        category: 'Satellite Remote Sensing Confirmation',
        contribution_points: rawBreakdown.evidence_score,
        max_points: 10,
        description: 'Spectral validation from Sentinel-2 MSI and SWIR indices'
      });
    }
  }

  const explanations: string[] = rawBreakdown?.explanation || [];

  const levelConfigs: Record<string, { bg: string; text: string; border: string; icon: string; ring: string }> = {
    CRITICAL: {
      bg: 'bg-red-950/60',
      text: 'text-red-400',
      border: 'border-red-800',
      icon: '🛑',
      ring: 'stroke-red-500'
    },
    HIGH: {
      bg: 'bg-orange-950/60',
      text: 'text-orange-400',
      border: 'border-orange-800',
      icon: '🔶',
      ring: 'stroke-orange-500'
    },
    MODERATE: {
      bg: 'bg-amber-950/60',
      text: 'text-amber-400',
      border: 'border-amber-800',
      icon: '⚠️',
      ring: 'stroke-amber-500'
    },
    LOW: {
      bg: 'bg-emerald-950/60',
      text: 'text-emerald-400',
      border: 'border-emerald-800',
      icon: '🟢',
      ring: 'stroke-emerald-500'
    }
  };

  const currentCfg = levelConfigs[level] || levelConfigs.LOW;
  const circumference = 2 * Math.PI * 28;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-3 font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400 uppercase text-[10px] tracking-wider">
            ANALYTICAL RISK ENGINE
          </span>
          <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400">
            {effectiveModelVersion}
          </span>
        </div>
        {onViewHistory && (
          <button
            onClick={onViewHistory}
            className="text-[10px] text-cyan-400 hover:text-cyan-300 underline"
          >
            History
          </button>
        )}
      </div>

      {/* Main Score & Radial Gauge */}
      <div className="flex items-center gap-4 pt-1 border-t border-slate-800/60">
        <div className="relative w-16 h-16 flex items-center justify-center flex-shrink-0">
          <svg className="w-16 h-16 transform -rotate-90">
            <circle
              cx="32"
              cy="32"
              r="28"
              className="stroke-slate-800"
              strokeWidth="5"
              fill="transparent"
            />
            <circle
              cx="32"
              cy="32"
              r="28"
              className={`${currentCfg.ring} transition-all duration-700 ease-out`}
              strokeWidth="5"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
            />
          </svg>
          <div className="absolute text-center leading-none">
            <span className="text-base font-bold text-slate-100">{Math.round(score)}</span>
            <div className="text-[8px] text-slate-500">/100</div>
          </div>
        </div>

        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-1.5">
            <span className="text-sm">{currentCfg.icon}</span>
            <span className={`px-2 py-0.5 rounded text-[11px] font-bold border uppercase ${currentCfg.bg} ${currentCfg.text} ${currentCfg.border}`}>
              {level} RISK
            </span>
          </div>
          <div className="text-[10px] text-slate-400 leading-relaxed">
            Analytical severity assessment based on thermal intensity, spatial proximity, and persistence.
          </div>
        </div>
      </div>

      {/* Factor Breakdown Accordion */}
      {factors.length > 0 && (
        <div className="pt-2 border-t border-slate-800/60">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between text-[10px] text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span>FACTOR BREAKDOWN ({factors.length} dimensions)</span>
            <span>{expanded ? '▲ Hide' : '▼ View Breakdown'}</span>
          </button>

          {expanded && (
            <div className="mt-2 space-y-2 pt-1 border-t border-slate-800/40">
              {factors.map((f, idx) => (
                <div key={idx} className="bg-slate-950/60 p-2 rounded border border-slate-800/60 space-y-1">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="font-semibold text-slate-300">{f.category}</span>
                    <span className="text-cyan-400 font-bold">
                      +{f.contribution_points} / {f.max_points} pts
                    </span>
                  </div>
                  <div className="text-[9px] text-slate-400">{f.description}</div>
                  <div className="w-full bg-slate-900 h-1 rounded overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded transition-all"
                      style={{ width: `${Math.min(100, Math.round((f.contribution_points / f.max_points) * 100))}%` }}
                    />
                  </div>
                </div>
              ))}

              {explanations.length > 0 && (
                <div className="pt-2 border-t border-slate-800/50 space-y-1">
                  <div className="text-[9px] uppercase tracking-wider text-slate-400 font-bold">
                    Analytical Explanations:
                  </div>
                  {explanations.map((exp, eIdx) => (
                    <div key={eIdx} className="text-[9px] text-slate-300 flex items-start gap-1">
                      <span className="text-cyan-400 font-bold">•</span>
                      <span>{exp}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Advisory Disclaimer */}
      <div className="text-[9px] text-slate-500 italic pt-1 border-t border-slate-800/40">
        * InfernoX analytical risk calculation. Not an official emergency response determination.
      </div>
    </div>
  );
};
