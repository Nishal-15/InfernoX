"use client";

import React, { useState } from 'react';

interface ProvenanceCardProps {
  provenance?: {
    thermal_source?: string;
    infrastructure_source?: string;
    land_cover_source?: string;
    satellite_source?: string;
    ml_model_version?: string;
    feature_schema_version?: string;
    analysis_timestamp?: string;
  };
}

export const DataProvenanceCard: React.FC<ProvenanceCardProps> = ({ provenance }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-slate-900/60 rounded-lg border border-slate-800/80 font-mono text-xs overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-slate-400 hover:text-slate-200 transition-colors text-left"
      >
        <span className="text-[10px] uppercase tracking-wider font-semibold">
          Data Provenance & Traceability
        </span>
        <svg className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="p-3 pt-1 border-t border-slate-800/60 space-y-1.5 text-[10px] text-slate-400">
          <div className="flex justify-between">
            <span className="text-slate-500">Thermal Detection:</span>
            <span className="text-slate-300">{provenance?.thermal_source || 'NASA FIRMS NRT (VIIRS/MODIS)'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Infrastructure DB:</span>
            <span className="text-slate-300">{provenance?.infrastructure_source || 'OpenStreetMap (OSM) PostGIS'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Land Cover Provider:</span>
            <span className="text-slate-300">{provenance?.land_cover_source || 'ESA WorldCover 10m v200'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Satellite Remote Sensing:</span>
            <span className="text-slate-300">{provenance?.satellite_source || 'Copernicus Sentinel-2 MSI L2A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Inference Engine:</span>
            <span className="text-indigo-400 font-semibold">{provenance?.ml_model_version || 'XGBoost v1 (xgb-v1)'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Feature Schema:</span>
            <span className="text-slate-300">{provenance?.feature_schema_version || 'v2.0'}</span>
          </div>
          {provenance?.analysis_timestamp && (
            <div className="flex justify-between pt-1 border-t border-slate-800/40 text-slate-500">
              <span>Timestamp:</span>
              <span>{provenance.analysis_timestamp}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
