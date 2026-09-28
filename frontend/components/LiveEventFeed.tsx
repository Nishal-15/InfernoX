"use client";

import React, { useState, useMemo } from 'react';

export interface FeedEventItem {
  id: number;
  latitude?: number;
  longitude?: number;
  frp?: number;
  confidence?: number;
  detected_at?: string;
  satellite?: string;
  status?: string;
  classification?: string;
  facility_distance_m?: number;
  nearest_facility_name?: string;
  persistence_days?: number;
  risk_level?: string;
  risk_score?: number;
}

interface LiveEventFeedProps {
  events: FeedEventItem[];
  selectedEventId?: number | null;
  onSelectEvent: (eventId: number, flyTo?: boolean) => void;
  onFlyTo?: (lon: number, lat: number) => void;
  onOpenReport?: (eventId: number) => void;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({
  events,
  selectedEventId,
  onSelectEvent,
  onFlyTo,
  onOpenReport
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'INDUSTRIAL' | 'FLARE' | 'WILD'>('ALL');
  const [search, setSearch] = useState('');

  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      const cls = (e.classification || '').toUpperCase();
      const risk = (e.risk_level || (e.frp && e.frp >= 80 ? 'CRITICAL' : 'MODERATE')).toUpperCase();
      const code = `INF-2026-${e.id.toString().padStart(6, '0')}`.toLowerCase();
      const query = search.toLowerCase();

      const matchesSearch = !query || code.includes(query) || (e.nearest_facility_name && e.nearest_facility_name.toLowerCase().includes(query));

      if (!matchesSearch) return false;

      if (filter === 'CRITICAL') return risk === 'CRITICAL' || (e.frp || 0) >= 80;
      if (filter === 'INDUSTRIAL') return cls.includes('INDUSTRIAL') || cls.includes('REFINERY') || cls.includes('POWER');
      if (filter === 'FLARE') return cls.includes('FLARE') || cls.includes('PERSISTENT');
      if (filter === 'WILD') return cls.includes('WILD') || cls.includes('FOREST');

      return true;
    });
  }, [events, filter, search]);

  const getClassificationBadge = (clsName?: string) => {
    const c = (clsName || 'UNCLASSIFIED').toUpperCase();
    if (c.includes('INDUSTRIAL') || c.includes('REFINERY')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-950/80 text-red-400 border border-red-800/80 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
          Industrial Fire
        </span>
      );
    }
    if (c.includes('FLARE') || c.includes('PERSISTENT')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-950/80 text-purple-300 border border-purple-800/80 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          Gas Flare
        </span>
      );
    }
    if (c.includes('WILD') || c.includes('FOREST')) {
      return (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          Wildfire
        </span>
      );
    }
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
        Thermal Source
      </span>
    );
  };

  const getRiskBadge = (frp: number = 0, riskLevel?: string) => {
    const r = (riskLevel || (frp >= 80 ? 'CRITICAL' : frp >= 40 ? 'HIGH' : 'MODERATE')).toUpperCase();
    if (r === 'CRITICAL') {
      return <span className="text-[10px] font-bold text-red-400 bg-red-950/60 px-1.5 py-0.5 rounded border border-red-800 animate-pulse">CRITICAL RISK</span>;
    }
    if (r === 'HIGH') {
      return <span className="text-[10px] font-bold text-orange-400 bg-orange-950/60 px-1.5 py-0.5 rounded border border-orange-800">HIGH RISK</span>;
    }
    return <span className="text-[10px] font-semibold text-yellow-400 bg-yellow-950/40 px-1.5 py-0.5 rounded border border-yellow-800/60">MODERATE RISK</span>;
  };

  if (isCollapsed) {
    return (
      <div className="absolute top-16 right-4 z-20 font-mono">
        <button
          onClick={() => setIsCollapsed(false)}
          className="bg-slate-950/90 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/60 text-slate-200 text-xs px-3 py-2 rounded-xl shadow-2xl backdrop-blur-md flex items-center gap-2 transition"
          title="Expand Live Thermal Feed"
        >
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
          <span className="font-bold">LIVE FEED</span>
          <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-cyan-400">{events.length}</span>
          <span>◀</span>
        </button>
      </div>
    );
  }

  return (
    <div className="absolute top-16 right-4 bottom-20 z-20 w-80 lg:w-88 bg-slate-950/90 border border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl flex flex-col font-mono text-slate-100 overflow-hidden transition-all animate-in fade-in slide-in-from-right-4 duration-200">
      {/* Feed Header */}
      <div className="p-3.5 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
          <h2 className="text-xs font-bold text-slate-100 tracking-wider">LIVE THERMAL FEED</h2>
          <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 text-[10px] border border-cyan-800">
            {events.length} Active
          </span>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          className="text-slate-400 hover:text-white text-xs px-1.5 py-0.5 rounded hover:bg-slate-800 transition"
          title="Collapse Feed"
        >
          ▶
        </button>
      </div>

      {/* Quick Search & Filters */}
      <div className="p-2.5 border-b border-slate-800/60 bg-slate-950/40 space-y-2 shrink-0">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter code, facility..."
          className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
        />

        <div className="flex items-center gap-1 overflow-x-auto text-[10px]">
          {(['ALL', 'CRITICAL', 'INDUSTRIAL', 'FLARE', 'WILD'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-2 py-0.5 rounded border transition shrink-0 ${
                filter === tab
                  ? 'bg-cyan-950 text-cyan-300 border-cyan-700 font-bold'
                  : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Event Cards Scrollable Feed */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2.5">
        {filteredEvents.length === 0 ? (
          <div className="h-40 flex flex-col items-center justify-center text-slate-500 text-xs text-center p-4">
            <p>No thermal events match current filter</p>
          </div>
        ) : (
          filteredEvents.map(ev => {
            const isSelected = selectedEventId === ev.id;
            const code = `INF-2026-${ev.id.toString().padStart(6, '0')}`;
            const frp = ev.frp || 0;
            const facilityDist = ev.facility_distance_m !== undefined 
              ? (ev.facility_distance_m < 1000 ? `${Math.round(ev.facility_distance_m)}m from facility` : `${(ev.facility_distance_m / 1000).toFixed(1)}km from facility`)
              : 'Near Industrial Zone';

            return (
              <div
                key={ev.id}
                onClick={() => onSelectEvent(ev.id, false)}
                className={`p-3 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/90 border-cyan-400 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-400'
                    : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                }`}
              >
                {/* Header row */}
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-amber-300">{code}</span>
                  {getRiskBadge(frp, ev.risk_level)}
                </div>

                {/* Classification and Confidence */}
                <div className="mt-2 flex items-center justify-between gap-1">
                  {getClassificationBadge(ev.classification)}
                  <span className="text-[10px] text-slate-400 font-medium">
                    {ev.confidence ? `${Math.round(ev.confidence)}% conf` : '92% conf'}
                  </span>
                </div>

                {/* FRP and Facility Proximity */}
                <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-slate-300">
                  <div>
                    <span className="text-slate-500 block text-[9px]">FRP PEAK</span>
                    <span className="font-bold text-orange-400">{frp.toFixed(1)} MW</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px]">PERSISTENCE</span>
                    <span className="text-purple-300 font-medium">{ev.persistence_days || 8} days</span>
                  </div>
                </div>

                {/* Facility Context snippet */}
                <div className="mt-1.5 text-[10px] text-slate-400 flex items-center gap-1 truncate">
                  <svg className="w-3 h-3 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                  <span className="truncate">{ev.nearest_facility_name ? `${ev.nearest_facility_name} (${facilityDist})` : facilityDist}</span>
                </div>

                {/* Footer and Actions */}
                <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                  <span className="text-slate-500">{ev.satellite || 'VIIRS NOAA-21'}</span>
                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => onSelectEvent(ev.id, true)}
                      className="px-2 py-0.5 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 font-bold transition"
                    >
                      Investigate
                    </button>
                    {ev.latitude && ev.longitude && onFlyTo && (
                      <button
                        onClick={() => onFlyTo(ev.longitude!, ev.latitude!)}
                        className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                      >
                        Fly
                      </button>
                    )}
                    {onOpenReport && (
                      <button
                        onClick={() => onOpenReport(ev.id)}
                        className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                        title="Generate Report"
                      >
                        Dossier
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
