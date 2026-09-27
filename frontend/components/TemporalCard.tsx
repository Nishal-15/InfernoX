"use client";

import React from 'react';

interface TemporalCardProps {
  firstDetected?: string;
  lastDetected?: string;
  activeDays?: number;
  detectionsCount?: number;
  durationDays?: number;
  meanFrp?: number;
  maxFrp?: number;
  status?: string;
  clusterId?: string;
}

export const TemporalCard: React.FC<TemporalCardProps> = ({
  firstDetected,
  lastDetected,
  activeDays = 1,
  detectionsCount = 1,
  durationDays = 1,
  meanFrp = 25.0,
  maxFrp = 35.0,
  status = 'NEW',
  clusterId
}) => {
  const statusColors: Record<string, string> = {
    ABNORMAL: 'bg-red-950 text-red-400 border-red-800 animate-pulse',
    PERSISTENT: 'bg-orange-950 text-orange-400 border-orange-800',
    RECURRING: 'bg-amber-950 text-amber-400 border-amber-800',
    NEW: 'bg-blue-950 text-blue-400 border-blue-800'
  };

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-2.5 font-mono text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400 uppercase text-[10px] tracking-wider">
            TEMPORAL INTELLIGENCE
          </span>
          {clusterId && (
            <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
              #{clusterId}
            </span>
          )}
        </div>
        <span className={`px-1.5 py-0.5 rounded text-[10px] border uppercase font-semibold ${statusColors[status] || statusColors.NEW}`}>
          {status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/60">
        <div>
          <div className="text-[10px] text-slate-500 uppercase">First Detected</div>
          <div className="text-slate-200 font-semibold">{formatDate(firstDetected)}</div>
        </div>
        <div>
          <div className="text-[10px] text-slate-500 uppercase">Last Detected</div>
          <div className="text-slate-200 font-semibold">{formatDate(lastDetected)}</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800/40 text-[11px]">
        <div>
          <div className="text-[9px] text-slate-500 uppercase">Active Days</div>
          <div className="text-cyan-300 font-semibold">{activeDays} d</div>
        </div>
        <div>
          <div className="text-[9px] text-slate-500 uppercase">Detections</div>
          <div className="text-cyan-300 font-semibold">{detectionsCount}</div>
        </div>
        <div>
          <div className="text-[9px] text-slate-500 uppercase">Duration</div>
          <div className="text-cyan-300 font-semibold">{durationDays} d</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800/40">
        <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/60">
          <div className="text-[9px] text-slate-500 uppercase">Mean FRP</div>
          <div className="text-amber-400 font-bold text-sm leading-none mt-0.5">
            {meanFrp ? meanFrp.toFixed(1) : '0.0'} <span className="text-[10px] font-normal text-slate-400">MW</span>
          </div>
        </div>
        <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/60">
          <div className="text-[9px] text-slate-500 uppercase">Max FRP</div>
          <div className="text-red-400 font-bold text-sm leading-none mt-0.5">
            {maxFrp ? maxFrp.toFixed(1) : '0.0'} <span className="text-[10px] font-normal text-slate-400">MW</span>
          </div>
        </div>
      </div>
    </div>
  );
};
