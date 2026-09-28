import React from 'react';
import { NavTab } from '@/components/SidebarNav';

interface MissionControlHudBarProps {
  eventCount: number;
  criticalCount: number;
  facilityCount: number;
  incidentCount: number;
  onNavigateTab: (tab: NavTab) => void;
  onTriggerSync?: () => void;
  isSyncing?: boolean;
}

export const MissionControlHudBar: React.FC<MissionControlHudBarProps> = ({
  eventCount,
  criticalCount,
  facilityCount,
  incidentCount,
  onNavigateTab,
  onTriggerSync,
  isSyncing = false
}) => {
  return (
    <div className="absolute bottom-4 left-4 right-4 z-20 pointer-events-none font-mono">
      <div className="max-w-7xl mx-auto bg-slate-950/90 border border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 pointer-events-auto text-xs">
        {/* Metric Pills */}
        <div className="flex items-center gap-2 overflow-x-auto">
          {/* Live Events Pill */}
          <button
            onClick={() => onNavigateTab('events')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/50 transition group"
            title="Inspect all live thermal events"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400 group-hover:animate-ping"></span>
            <span className="text-slate-400 text-[11px]">EVENTS:</span>
            <span className="font-bold text-cyan-300">{eventCount}</span>
          </button>

          {/* Critical Risk Excursions */}
          <button
            onClick={() => onNavigateTab('alerts')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-950/40 hover:bg-red-950/70 border border-red-900/60 hover:border-red-600 transition group"
            title="Inspect active high-risk alerts"
          >
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            <span className="text-red-300 text-[11px]">CRITICAL:</span>
            <span className="font-bold text-red-400">{criticalCount}</span>
          </button>

          {/* Monitored Strategic Facilities */}
          <button
            onClick={() => onNavigateTab('facilities')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-sky-500/50 transition"
            title="View monitored industrial complexes"
          >
            <span className="w-2 h-2 rounded-full bg-sky-400"></span>
            <span className="text-slate-400 text-[11px]">FACILITIES:</span>
            <span className="font-bold text-sky-300">{facilityCount}</span>
          </button>

          {/* Correlated Incidents */}
          <button
            onClick={() => onNavigateTab('incidents')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-950/30 hover:bg-purple-950/60 border border-purple-900/50 hover:border-purple-600 transition"
            title="Open correlated incidents command board"
          >
            <span className="w-2 h-2 rounded-full bg-purple-400"></span>
            <span className="text-slate-400 text-[11px]">INCIDENTS:</span>
            <span className="font-bold text-purple-300">{incidentCount}</span>
          </button>
        </div>

        {/* System Telemetry & Pipeline Action */}
        <div className="hidden md:flex items-center gap-3 text-[11px]">
          <div className="flex items-center gap-2 text-slate-400">
            <span className="text-slate-500">FEED:</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              NASA FIRMS NRT (VIIRS)
            </span>
          </div>

          <div className="h-4 w-px bg-slate-800"></div>

          <div className="flex items-center gap-2 text-slate-400">
            <span className="text-slate-500">MODEL:</span>
            <span className="text-purple-300 font-semibold">XGBoost v1.0 (94.2% F1)</span>
          </div>

          {onTriggerSync && (
            <>
              <div className="h-4 w-px bg-slate-800"></div>
              <button
                onClick={onTriggerSync}
                disabled={isSyncing}
                className="px-2.5 py-1 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-[11px] font-bold transition flex items-center gap-1.5"
                title="Trigger immediate NASA FIRMS incremental ingest"
              >
                <svg className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {isSyncing ? 'Syncing...' : 'Sync Cycle'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
