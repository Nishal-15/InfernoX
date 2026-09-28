"use client";

import React, { useState, useEffect } from 'react';
import { getIncidents, updateIncidentStatus, getIncidentDetail, ThermalIncidentResponse } from '@/lib/api';

interface IncidentsViewProps {
  onFlyToIncident?: (lon: number, lat: number) => void;
  onInspectEvent?: (eventId: number) => void;
}

export const IncidentsView: React.FC<IncidentsViewProps> = ({
  onFlyToIncident,
  onInspectEvent
}) => {
  const [incidents, setIncidents] = useState<ThermalIncidentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeCount, setActiveCount] = useState<number>(0);
  const [criticalCount, setCriticalCount] = useState<number>(0);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  // Selected Incident for Detail Drawer
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);
  const [incidentDetail, setIncidentDetail] = useState<{
    incident: ThermalIncidentResponse;
    events: any[];
    alerts: any[];
  } | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [analystNote, setAnalystNote] = useState<string>('');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState<boolean>(false);

  const fetchIncidents = async () => {
    try {
      setLoading(true);
      const res = await getIncidents();
      const items = res?.items || (Array.isArray(res) ? res : []);
      setIncidents(items);
      setActiveCount(res?.active_count ?? items.filter((i: any) => i.status === 'ACTIVE' || i.status === 'MONITORING').length);
      setCriticalCount(res?.critical_count ?? items.filter((i: any) => i.severity === 'CRITICAL').length);
    } catch (err) {
      console.error("Failed to load incidents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const openIncidentDetail = async (id: number) => {
    setSelectedIncidentId(id);
    setLoadingDetail(true);
    try {
      const data = await getIncidentDetail(id);
      setIncidentDetail(data);
    } catch (err) {
      console.error("Failed to load incident detail:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleStatusChange = async (incidentId: number, newStatus: string) => {
    try {
      setIsUpdatingStatus(true);
      const updated = await updateIncidentStatus(incidentId, newStatus, analystNote || undefined);
      setIncidents(prev => prev.map(inc => inc.id === incidentId ? { ...inc, status: updated.status } : inc));
      if (incidentDetail && incidentDetail.incident.id === incidentId) {
        setIncidentDetail(prev => prev ? {
          ...prev,
          incident: { ...prev.incident, status: updated.status }
        } : null);
      }
      setAnalystNote('');
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const filteredIncidents = incidents.filter(inc => {
    const matchesStatus = statusFilter === 'ALL' || inc.status === statusFilter;
    const matchesSeverity = severityFilter === 'ALL' || inc.severity === severityFilter;
    return matchesStatus && matchesSeverity;
  });

  const getSeverityBadge = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-red-400 border border-red-800 animate-pulse">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-950 text-orange-400 border border-orange-800">HIGH</span>;
      case 'MODERATE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-950 text-yellow-400 border border-yellow-800">MODERATE</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">LOW</span>;
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'ACTIVE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-900/80 text-red-200 border border-red-700">ACTIVE</span>;
      case 'MONITORING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-700">MONITORING</span>;
      case 'CONTAINED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-700">CONTAINED</span>;
      case 'RESOLVED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">RESOLVED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">{status || 'UNKNOWN'}</span>;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden font-mono">
      {/* Top Header */}
      <div className="px-6 py-4 bg-slate-900/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide">CORRELATED THERMAL INCIDENTS</h1>
            <span className="px-2 py-0.5 text-[11px] rounded bg-purple-950 text-purple-300 border border-purple-800">
              {incidents.length} Multi-Pass Incidents
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            DBSCAN spatial clustering and temporal tracking engine synthesizing repeated satellite passes into actionable incidents
          </p>
        </div>

        {/* Quick KPI stats */}
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs">
            <span className="text-slate-500">Active: </span>
            <span className="font-bold text-cyan-400">{activeCount}</span>
          </div>
          <div className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs">
            <span className="text-slate-500">Critical: </span>
            <span className="font-bold text-red-400">{criticalCount}</span>
          </div>
          <button
            onClick={fetchIncidents}
            disabled={loading}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700 transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Ribbon */}
      <div className="px-6 py-3 bg-slate-900/40 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="MONITORING">MONITORING</option>
              <option value="CONTAINED">CONTAINED</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MODERATE">MODERATE</option>
              <option value="LOW">LOW</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main View Area (Table + Detail Drawer) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table of Incidents */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="h-64 flex flex-col items-center justify-center gap-3 text-slate-500">
              <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs">Correlating thermal event clusters...</p>
            </div>
          ) : filteredIncidents.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center gap-2 text-slate-500 bg-slate-900/30 border border-slate-800 rounded-xl p-8">
              <p className="text-sm font-semibold text-slate-400">No thermal incidents found matching filter</p>
            </div>
          ) : (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-4">Incident Code</th>
                    <th className="py-3 px-4">Title / Target</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Pass Count</th>
                    <th className="py-3 px-4">Peak FRP</th>
                    <th className="py-3 px-4">Centroid</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredIncidents.map((inc) => {
                    const lat = inc.centroid_latitude ?? inc.centroid_lat ?? 0;
                    const lon = inc.centroid_longitude ?? inc.centroid_lon ?? 0;
                    const isSelected = selectedIncidentId === inc.id;

                    return (
                      <tr
                        key={inc.id}
                        className={`hover:bg-slate-800/40 transition-colors cursor-pointer ${
                          isSelected ? 'bg-slate-800/60 border-l-2 border-cyan-400' : ''
                        }`}
                        onClick={() => openIncidentDetail(inc.id)}
                      >
                        <td className="py-3 px-4 font-bold text-amber-300">
                          {inc.incident_code || `#INC-2026-${inc.id.toString().padStart(4, '0')}`}
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-slate-200 line-clamp-1">{inc.title}</div>
                          {inc.primary_facility_name && (
                            <div className="text-[10px] text-cyan-400">Near: {inc.primary_facility_name}</div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {getStatusBadge(inc.status)}
                        </td>
                        <td className="py-3 px-4">
                          {getSeverityBadge(inc.severity)}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                            {inc.event_count || inc.observation_count || 1} observations
                          </span>
                        </td>
                        <td className="py-3 px-4 font-bold text-orange-400">
                          {inc.peak_frp ? `${inc.peak_frp.toFixed(1)} MW` : 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-slate-400 text-[11px]">
                          {lat.toFixed(3)}°, {lon.toFixed(3)}°
                        </td>
                        <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => openIncidentDetail(inc.id)}
                              className="px-2.5 py-1 rounded bg-purple-950 hover:bg-purple-900 text-purple-300 border border-purple-800 text-[11px] font-semibold transition"
                            >
                              Details
                            </button>
                            {lat && lon && onFlyToIncident && (
                              <button
                                onClick={() => onFlyToIncident(lon, lat)}
                                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[11px] transition"
                              >
                                Fly
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Incident Detail / Analyst Workflow Drawer */}
        {selectedIncidentId && (
          <div className="w-96 border-l border-slate-800 bg-slate-900/90 p-5 overflow-y-auto shrink-0 flex flex-col justify-between">
            {loadingDetail ? (
              <div className="h-48 flex items-center justify-center text-slate-500">
                <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : incidentDetail ? (
              <div className="space-y-4">
                <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                  <div>
                    <span className="text-[10px] text-cyan-400 font-bold uppercase">
                      {incidentDetail.incident.incident_code}
                    </span>
                    <h2 className="text-sm font-bold text-slate-100 mt-0.5">
                      {incidentDetail.incident.title}
                    </h2>
                  </div>
                  <button
                    onClick={() => setSelectedIncidentId(null)}
                    className="text-slate-400 hover:text-white text-xs p-1"
                  >
                    ✕
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-slate-950/80 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">STATUS</span>
                    {getStatusBadge(incidentDetail.incident.status)}
                  </div>
                  <div className="p-2 rounded bg-slate-950/80 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">SEVERITY</span>
                    {getSeverityBadge(incidentDetail.incident.severity)}
                  </div>
                </div>

                {/* Human-in-the-loop lifecycle transition buttons */}
                <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 space-y-2">
                  <div className="text-[11px] font-bold text-cyan-400 flex items-center justify-between">
                    <span>ANALYST STATUS ACTION</span>
                    {isUpdatingStatus && <span className="text-amber-400 text-[10px]">Updating...</span>}
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Transition incident lifecycle. Action will be audited in autonomous ledger.
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 pt-1">
                    <button
                      onClick={() => handleStatusChange(incidentDetail.incident.id, 'MONITORING')}
                      disabled={isUpdatingStatus}
                      className="py-1 px-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] border border-slate-700 transition"
                    >
                      Set Monitoring
                    </button>
                    <button
                      onClick={() => handleStatusChange(incidentDetail.incident.id, 'CONTAINED')}
                      disabled={isUpdatingStatus}
                      className="py-1 px-2 rounded bg-amber-950 hover:bg-amber-900 text-amber-300 text-[11px] border border-amber-800 transition"
                    >
                      Mark Contained
                    </button>
                    <button
                      onClick={() => handleStatusChange(incidentDetail.incident.id, 'RESOLVED')}
                      disabled={isUpdatingStatus}
                      className="py-1 px-2 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 text-[11px] border border-emerald-800 transition col-span-2"
                    >
                      Resolve Incident
                    </button>
                  </div>

                  <div className="pt-2">
                    <input
                      type="text"
                      value={analystNote}
                      onChange={(e) => setAnalystNote(e.target.value)}
                      placeholder="Optional analyst note..."
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>

                {/* Correlated Thermal Events */}
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                    Correlated Detections ({incidentDetail.events.length})
                  </h4>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {incidentDetail.events.map((ev) => (
                      <div
                        key={ev.id}
                        onClick={() => onInspectEvent && onInspectEvent(ev.id)}
                        className="p-2 rounded bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 text-xs flex justify-between items-center cursor-pointer transition"
                      >
                        <div>
                          <div className="font-bold text-amber-300">{ev.event_code}</div>
                          <div className="text-[10px] text-slate-500">{ev.detected_at?.slice(0, 19)}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-orange-400">{ev.frp?.toFixed(1)} MW</div>
                          <div className="text-[10px] text-slate-400">{ev.satellite}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};
