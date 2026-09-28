"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getEventsList } from '@/lib/api';

export interface ThermalEventTableRow {
  id: number;
  latitude?: number;
  longitude?: number;
  frp?: number;
  confidence?: number;
  detected_at?: string;
  satellite?: string;
  status?: string;
  classification?: string;
  class?: string;
  notes?: string;
  [key: string]: unknown;
}

interface LiveEventsViewProps {
  onSelectEvent: (eventId: number, flyTo?: boolean) => void;
  onFlyTo?: (lon: number, lat: number) => void;
  onOpenReport?: (eventId: number) => void;
}

export const LiveEventsView: React.FC<LiveEventsViewProps> = ({
  onSelectEvent,
  onFlyTo,
  onOpenReport
}) => {
  const [events, setEvents] = useState<ThermalEventTableRow[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [classificationFilter, setClassificationFilter] = useState<string>('ALL');
  const [satelliteFilter, setSatelliteFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'time' | 'frp' | 'confidence'>('time');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getEventsList({
        limit: 100,
        offset: (page - 1) * pageSize
      });
      const items = res?.items || (Array.isArray(res) ? res : []);
      setEvents(items);
      setTotalCount(res?.total || items.length);
    } catch (err) {
      console.error("Failed to load events:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      const classification = (e.classification || e.class || 'UNCLASSIFIED').toUpperCase();
      const satellite = (e.satellite || '').toUpperCase();
      const code = `INF-2026-${e.id.toString().padStart(6, '0')}`.toLowerCase();
      const query = searchQuery.toLowerCase();

      const matchesSearch = !query || 
        code.includes(query) || 
        (e.satellite && e.satellite.toLowerCase().includes(query)) ||
        (e.notes && e.notes.toLowerCase().includes(query));

      const matchesClassification = classificationFilter === 'ALL' || 
        classification.includes(classificationFilter);

      const matchesSatellite = satelliteFilter === 'ALL' || 
        satellite.includes(satelliteFilter);

      return matchesSearch && matchesClassification && matchesSatellite;
    }).sort((a, b) => {
      if (sortBy === 'frp') return (b.frp || 0) - (a.frp || 0);
      if (sortBy === 'confidence') return (b.confidence || 0) - (a.confidence || 0);
      return new Date(b.detected_at || 0).getTime() - new Date(a.detected_at || 0).getTime();
    });
  }, [events, searchQuery, classificationFilter, satelliteFilter, sortBy]);

  const getClassificationBadge = (classification?: string) => {
    const cls = (classification || 'UNCLASSIFIED').toUpperCase();
    if (cls.includes('INDUSTRIAL') || cls.includes('REFINERY') || cls.includes('POWER') || cls.includes('STEEL')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950/80 text-red-400 border border-red-800/80 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
          INDUSTRIAL FIRE
        </span>
      );
    }
    if (cls.includes('FLARE') || cls.includes('PERSISTENT')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950/80 text-purple-300 border border-purple-800/80 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          GAS FLARE
        </span>
      );
    }
    if (cls.includes('WILD') || cls.includes('FOREST')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          WILDFIRE
        </span>
      );
    }
    if (cls.includes('AGRICULT') || cls.includes('CROP') || cls.includes('STUBBLE')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-800/80 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          AGRICULTURAL
        </span>
      );
    }
    if (cls.includes('MINING') || cls.includes('QUARRY')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-950/80 text-orange-400 border border-orange-800/80 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-orange-400"></span>
          MINING
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
        {classification || 'EVALUATING'}
      </span>
    );
  };

  const exportCSV = () => {
    if (filteredEvents.length === 0) return;
    const headers = ["Event_ID", "Detected_At", "Latitude", "Longitude", "FRP_MW", "Confidence", "Satellite", "Classification"];
    const rows = filteredEvents.map(e => [
      `INF-2026-${e.id.toString().padStart(6, '0')}`,
      e.detected_at || '',
      e.latitude ?? '',
      e.longitude ?? '',
      e.frp ?? 0,
      e.confidence ?? 0,
      e.satellite ?? '',
      e.classification || 'UNCLASSIFIED'
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `infernox_thermal_events_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden font-mono">
      {/* Header bar */}
      <div className="px-6 py-4 bg-slate-900/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide">LIVE THERMAL EVENTS EXPLORER</h1>
            <span className="px-2 py-0.5 text-[11px] rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              {totalCount} Verified Anomalies
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Spaceborne thermal observations ingested from NASA FIRMS NRT feeds with multi-criteria spatial enrichment
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchEvents}
            disabled={loading}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700 transition flex items-center gap-1.5"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={exportCSV}
            className="px-3 py-1.5 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 text-xs border border-cyan-700 transition flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter and control ribbon */}
      <div className="px-6 py-3 bg-slate-900/40 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search ID, satellite, coordinates..."
              className="w-64 bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1.5 text-xs text-slate-400 hover:text-white"
              >
                ✕
              </button>
            )}
          </div>

          {/* Classification Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Class:</span>
            <select
              value={classificationFilter}
              onChange={(e) => setClassificationFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Classifications</option>
              <option value="INDUSTRIAL">Industrial Fire</option>
              <option value="FLARE">Gas Flare / Persistent</option>
              <option value="WILD">Wildfire / Natural</option>
              <option value="AGRICULT">Agricultural Burning</option>
              <option value="MINING">Mining / Quarry</option>
            </select>
          </div>

          {/* Satellite Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Feed:</span>
            <select
              value={satelliteFilter}
              onChange={(e) => setSatelliteFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Sensors</option>
              <option value="VIIRS">VIIRS (SNPP / NOAA-20 / NOAA-21)</option>
              <option value="MODIS">MODIS (Aqua / Terra)</option>
            </select>
          </div>
        </div>

        {/* Sort selector */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>Sort By:</span>
          <div className="flex rounded border border-slate-700 overflow-hidden bg-slate-900">
            <button
              onClick={() => setSortBy('time')}
              className={`px-2.5 py-1 text-xs transition ${sortBy === 'time' ? 'bg-cyan-950 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              Recent
            </button>
            <button
              onClick={() => setSortBy('frp')}
              className={`px-2.5 py-1 text-xs transition ${sortBy === 'frp' ? 'bg-cyan-950 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              FRP Peak
            </button>
            <button
              onClick={() => setSortBy('confidence')}
              className={`px-2.5 py-1 text-xs transition ${sortBy === 'confidence' ? 'bg-cyan-950 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'}`}
            >
              Confidence
            </button>
          </div>
        </div>
      </div>

      {/* Main Table Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs">Querying database for thermal detections...</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center gap-2 text-slate-500 bg-slate-900/30 border border-slate-800 rounded-xl p-8">
            <svg className="w-10 h-10 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm font-semibold text-slate-400">No thermal events match current filters</p>
            <p className="text-xs text-slate-500">Try loosening your search terms or classification filters</p>
          </div>
        ) : (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Event Code</th>
                  <th className="py-3 px-4">Classification</th>
                  <th className="py-3 px-4">Thermal FRP</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Sensor / Feed</th>
                  <th className="py-3 px-4">Coordinates</th>
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredEvents.map((ev) => {
                  const eventCode = `INF-2026-${ev.id.toString().padStart(6, '0')}`;
                  const isHighFrp = (ev.frp || 0) >= 50;

                  return (
                    <tr 
                      key={ev.id} 
                      className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                      onClick={() => onSelectEvent(ev.id, false)}
                    >
                      <td className="py-3 px-4 font-bold text-amber-300 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                        {eventCode}
                      </td>
                      <td className="py-3 px-4">
                        {getClassificationBadge(ev.classification || ev.class)}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`font-bold ${isHighFrp ? 'text-red-400' : 'text-orange-400'}`}>
                          {ev.frp !== undefined && ev.frp !== null ? `${Number(ev.frp).toFixed(1)} MW` : 'N/A'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${
                                (ev.confidence || 0) >= 80 ? 'bg-emerald-400' : (ev.confidence || 0) >= 50 ? 'bg-amber-400' : 'bg-slate-500'
                              }`}
                              style={{ width: `${Math.min(100, ev.confidence || 0)}%` }}
                            />
                          </div>
                          <span className="text-slate-300 font-medium">
                            {ev.confidence ? `${Math.round(ev.confidence)}%` : 'N/A'}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] text-cyan-300">
                          {ev.satellite || 'VIIRS'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {ev.latitude !== undefined && ev.longitude !== undefined 
                          ? `${Number(ev.latitude).toFixed(4)}°, ${Number(ev.longitude).toFixed(4)}°`
                          : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {ev.detected_at ? new Date(ev.detected_at).toLocaleString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => onSelectEvent(ev.id, true)}
                            className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-[11px] font-semibold transition"
                            title="Inspect in workspace"
                          >
                            Inspect
                          </button>
                          {ev.latitude !== undefined && ev.longitude !== undefined && onFlyTo && (
                            <button
                              onClick={() => onFlyTo(ev.longitude!, ev.latitude!)}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[11px] transition"
                              title="Fly to coordinate on globe"
                            >
                              Fly
                            </button>
                          )}
                          {onOpenReport && (
                            <button
                              onClick={() => onOpenReport(ev.id)}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[11px] transition"
                              title="Generate intelligence dossier"
                            >
                              Dossier
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Pagination Controls */}
            <div className="p-3 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <span>Showing Page {page} of {Math.max(1, Math.ceil(totalCount / pageSize))}</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(prev => Math.max(1, prev - 1))}
                  disabled={page <= 1}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(prev => prev + 1)}
                  disabled={page * pageSize >= totalCount}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
