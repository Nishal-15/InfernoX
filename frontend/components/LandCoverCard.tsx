"use client";

import React from 'react';

interface LandCoverCardProps {
  landCoverClass?: number;
  landCoverName?: string;
  category?: string;
  source?: string;
  datasetVersion?: string;
  tileId?: string;
  confidence?: number;
}

export const LandCoverCard: React.FC<LandCoverCardProps> = ({
  landCoverClass,
  landCoverName = 'Built-up',
  category = 'INDUSTRIAL/BUILT',
  source = 'ESA WorldCover 10m',
  datasetVersion = 'v200 (2021)',
  tileId,
  confidence = 0.85
}) => {
  const categoryColors: Record<string, string> = {
    'INDUSTRIAL/BUILT': 'text-amber-300 bg-amber-950/60 border-amber-800',
    'URBAN': 'text-sky-300 bg-sky-950/60 border-sky-800',
    'FOREST': 'text-emerald-300 bg-emerald-950/60 border-emerald-800',
    'AGRICULTURE': 'text-yellow-300 bg-yellow-950/60 border-yellow-800',
    'WATER': 'text-blue-300 bg-blue-950/60 border-blue-800',
    'BARE_LAND': 'text-orange-300 bg-orange-950/60 border-orange-800',
    'OTHER': 'text-slate-300 bg-slate-900 border-slate-700'
  };

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-2 font-mono text-xs">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 uppercase text-[10px] tracking-wider">
          LAND COVER CONTEXT
        </span>
        <span className="text-[10px] text-slate-500">
          {source} {datasetVersion}
        </span>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
        <div>
          <div className="text-[10px] text-slate-500 uppercase">Class & Name</div>
          <div className="text-sm font-semibold text-slate-200">
            {landCoverName} {landCoverClass !== undefined ? `(${landCoverClass})` : ''}
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] border uppercase font-semibold ${categoryColors[category] || categoryColors.OTHER}`}>
          {category}
        </span>
      </div>

      <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1 border-t border-slate-800/40">
        <span>Classification Confidence:</span>
        <span className="text-slate-300 font-mono">{(confidence * 100).toFixed(0)}%</span>
      </div>

      {tileId && (
        <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1 border-t border-slate-800/40">
          <span>ESA Tile Index:</span>
          <span className="text-slate-300 font-mono">{tileId}</span>
        </div>
      )}
    </div>
  );
};
