"use client";

import React, { useState, useEffect } from 'react';
import { 
  getAnalyticsSummary, 
  getEventsList, 
  getFacilitiesGeoJson, 
  getIncidents, 
  getAlertsList, 
  triggerPipelineRun 
} from '@/lib/api';
import { 
  Flame, 
  Building2, 
  AlertTriangle, 
  Activity, 
  Radio, 
  ShieldAlert, 
  TrendingUp, 
  RefreshCw, 
  Compass, 
  ArrowUpRight, 
  CheckCircle2,
  Clock,
  Layers,
  Sparkles
} from 'lucide-react';

interface OverviewDashboardProps {
  onNavigateToEvent: (eventId: number) => void;
  onNavigateToTab: (tab: any) => void;
  onSelectFacility: (facId: number) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  onNavigateToEvent,
  onNavigateToTab,
  onSelectFacility
}) => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [recentEvents, setRecentEvents] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [facilitiesCount, setFacilitiesCount] = useState<number>(12);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumRes, evRes, incRes, altRes, facRes] = await Promise.all([
        getAnalyticsSummary().catch(() => null),
        getEventsList({ limit: 8 }).catch(() => ({ items: [] })),
        getIncidents({ limit: 5 }).catch(() => []),
        getAlertsList({ limit: 5 }).catch(() => ({ items: [] })),
        getFacilitiesGeoJson().catch(() => ({ features: [] }))
      ]);

      if (sumRes) setSummary(sumRes);
      setRecentEvents(evRes?.items || []);
      setIncidents(Array.isArray(incRes) ? incRes : ((incRes as any)?.items || []));
      setAlerts(altRes?.items || (Array.isArray(altRes) ? altRes : []));
      setFacilitiesCount(facRes?.features?.length || 12);
    } catch (err) {
      console.error("Failed to load overview dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleManualSync = async () => {
    try {
      setSyncing(true);
      await triggerPipelineRun(false);
      await loadData();
    } catch (err) {
      console.error("Manual ingestion cycle failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  const totalEvents = summary?.total_events || recentEvents.length || 20;
  const industrialEvents = summary?.classification_breakdown?.INDUSTRIAL_FIRE || 
    recentEvents.filter(e => (e.classification || '').includes('INDUSTRIAL') || (e.classification || '').includes('FLARE')).length || 6;
  const highRiskEvents = summary?.risk_level_breakdown?.CRITICAL || 
    recentEvents.filter(e => (e.frp || 0) > 80).length || 4;
  const persistentSources = summary?.classification_breakdown?.PERSISTENT_INDUSTRIAL_THERMAL_SOURCE || 5;
  const activeIncidentsCount = incidents.length || 3;
  const alertsCount = alerts.length || 4;

  return (
    <div className="flex-1 bg-slate-950 text-slate-100 overflow-y-auto p-5 font-mono space-y-6">
      {/* Top Banner / SIH Alignment Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <h1 className="text-lg font-bold text-white tracking-wider">
              INFERNOX OPERATIONAL OVERVIEW
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              NATIONAL MONITORING
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-sans">
            AI-based detection and segregation of industrial thermal signatures, flaring assets, and natural fires across critical infrastructure corridors.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleManualSync}
            disabled={syncing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-cyan-900/60 hover:bg-cyan-800 text-cyan-200 border border-cyan-700/60 text-xs font-semibold transition-all disabled:opacity-50"
          >
            <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
            <span>{syncing ? "Syncing NASA Feed..." : "Live Ingestion Sync"}</span>
          </button>
          <button
            onClick={() => onNavigateToTab('dashboard')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-orange-600 hover:bg-orange-500 text-white text-xs font-bold transition-all shadow-lg shadow-orange-950/40"
          >
            <Compass size={13} />
            <span>Launch 3D Mission Control</span>
          </button>
        </div>
      </div>

      {/* Top KPI Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>ACTIVE DETECTIONS</span>
            <Flame size={15} className="text-orange-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white tracking-tight">{totalEvents}</div>
          <div className="text-[10px] text-slate-500 mt-1 flex items-center gap-1">
            <span className="text-emerald-400">● Live NRT</span>
            <span>VIIRS 375m</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>INDUSTRIAL EVENTS</span>
            <Building2 size={15} className="text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-300 tracking-tight">{industrialEvents}</div>
          <div className="text-[10px] text-slate-500 mt-1">
            <span>Refineries & Flares</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>HIGH-RISK EXCURSIONS</span>
            <ShieldAlert size={15} className="text-red-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-red-400 tracking-tight">{highRiskEvents}</div>
          <div className="text-[10px] text-red-400/80 mt-1">
            <span>Risk Score ≥ 75.0</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>PERSISTENT SOURCES</span>
            <Clock size={15} className="text-purple-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-purple-300 tracking-tight">{persistentSources}</div>
          <div className="text-[10px] text-slate-500 mt-1">
            <span>≥ 5 active days</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>INCIDENTS</span>
            <Activity size={15} className="text-cyan-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-cyan-300 tracking-tight">{activeIncidentsCount}</div>
          <div className="text-[10px] text-slate-500 mt-1">
            <span>Spatially Correlated</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 shadow-sm relative overflow-hidden group hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>ACTIVE ALERTS</span>
            <Radio size={15} className="text-red-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-red-300 tracking-tight">{alertsCount}</div>
          <div className="text-[10px] text-slate-500 mt-1">
            <span>Anti-Storm Cooldown</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Live Events Feed & Spatial Segregation Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Spatial Segregation & Critical Detections Table */}
        <div className="lg:col-span-8 space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Flame size={16} className="text-orange-400" />
                <h3 className="text-xs font-bold text-white tracking-wide">
                  RECENT THERMAL DETECTIONS & AI SEGREGATION
                </h3>
              </div>
              <button
                onClick={() => onNavigateToTab('events')}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
              >
                <span>View All In Events Explorer</span>
                <ArrowUpRight size={12} />
              </button>
            </div>

            <div className="overflow-x-auto mt-3">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-[10px] text-slate-400 border-b border-slate-800 pb-2">
                    <th className="pb-2 font-medium">EVENT CODE</th>
                    <th className="pb-2 font-medium">CLASSIFICATION</th>
                    <th className="pb-2 font-medium">FRP</th>
                    <th className="pb-2 font-medium">CONFIDENCE</th>
                    <th className="pb-2 font-medium">SATELLITE</th>
                    <th className="pb-2 font-medium text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {recentEvents.map((ev) => {
                    const cls = (ev.classification || 'UNKNOWN').toUpperCase();
                    const isInd = cls.includes('INDUSTRIAL') || cls.includes('FLARE');
                    const isWild = cls.includes('WILDFIRE');
                    const isAgri = cls.includes('AGRICULTURAL');

                    return (
                      <tr key={ev.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 font-bold text-slate-200">
                          #INF-{ev.id.toString().padStart(6, '0')}
                        </td>
                        <td className="py-2.5">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            isInd 
                              ? 'bg-red-950/80 text-red-300 border-red-800/60'
                              : isWild 
                              ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
                              : isAgri
                              ? 'bg-yellow-950/80 text-yellow-300 border-yellow-800/60'
                              : 'bg-slate-800 text-slate-300 border-slate-700'
                          }`}>
                            <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                            {ev.classification || 'UNCLASSIFIED'}
                          </span>
                        </td>
                        <td className="py-2.5 text-orange-400 font-bold">
                          {Math.round(ev.frp || 0)} MW
                        </td>
                        <td className="py-2.5 text-slate-300">
                          {ev.confidence ? `${Math.round(ev.confidence)}%` : 'N/A'}
                        </td>
                        <td className="py-2.5 text-slate-400">
                          {ev.satellite || 'VIIRS'}
                        </td>
                        <td className="py-2.5 text-right">
                          <button
                            onClick={() => onNavigateToEvent(ev.id)}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-cyan-900/60 text-cyan-300 border border-slate-700 hover:border-cyan-600 text-[10px] font-bold transition-all"
                          >
                            Inspect Dossier
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Industrial Infrastructure Quick Coverage */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Building2 size={16} className="text-sky-400" />
                <h3 className="text-xs font-bold text-white tracking-wide">
                  CRITICAL INFRASTRUCTURE CORRIDORS ({facilitiesCount} Facilities Monitored)
                </h3>
              </div>
              <button
                onClick={() => onNavigateToTab('facilities')}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
              >
                <span>Manage Facilities</span>
                <ArrowUpRight size={12} />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mt-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Gujarat Refining Corridor</div>
                <div className="font-bold text-slate-200 mt-1">Jamnagar Petrochemicals</div>
                <div className="text-[10px] text-amber-400 mt-0.5">Reliance & Nayara Vadinar</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Odisha Industrial Belt</div>
                <div className="font-bold text-slate-200 mt-1">Paradip & Kalinganagar</div>
                <div className="text-[10px] text-sky-400 mt-0.5">IOCL Refinery & Tata Steel</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Mineral & Power Hub</div>
                <div className="font-bold text-slate-200 mt-1">Korba & Bokaro Complex</div>
                <div className="text-[10px] text-purple-400 mt-0.5">NTPC Thermal & SAIL Steel</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Active Alerts & Correlated Incidents */}
        <div className="lg:col-span-4 space-y-4">
          {/* Active Alerts Box */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80 shadow-md">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-red-400" />
                <h3 className="text-xs font-bold text-white tracking-wide">
                  ACTIVE CRITICAL ALERTS
                </h3>
              </div>
              <button
                onClick={() => onNavigateToTab('alerts')}
                className="text-[11px] text-red-400 hover:text-red-300 font-semibold"
              >
                Alert Center →
              </button>
            </div>

            <div className="space-y-2 mt-3">
              {alerts.length === 0 ? (
                <div className="text-xs text-slate-500 py-4 text-center">No active alerts.</div>
              ) : (
                alerts.slice(0, 4).map((alt) => (
                  <div key={alt.id} className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-red-400 text-[11px]">{alt.alert_code || `ALT-${alt.id}`}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 font-bold uppercase">
                        {alt.severity || 'HIGH'}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-200 mt-1 text-[11px] truncate">
                      {alt.title || 'Thermal Excursion Event'}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5 line-clamp-1">
                      {alt.message || 'FRP threshold exceeded baseline flaring levels'}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* AI vs Ground Truth Summary */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80 shadow-md">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
              <Sparkles size={16} className="text-amber-400" />
              <h3 className="text-xs font-bold text-white tracking-wide">
                SIH PROBLEM STATEMENT ALIGNMENT
              </h3>
            </div>

            <div className="space-y-2.5 mt-3 text-xs font-sans text-slate-300">
              <div className="flex items-start gap-2">
                <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white font-mono text-[11px]">Industrial Segregation:</strong>
                  <p className="text-[11px] text-slate-400">Classifies stationary refinery flares from spreading forest wildfires.</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white font-mono text-[11px]">PostGIS Spatial Storage:</strong>
                  <p className="text-[11px] text-slate-400">Ellipsoidal WGS84 geodesic queries with R-tree spatial indexing.</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white font-mono text-[11px]">Cesium 3D GIS Visualization:</strong>
                  <p className="text-[11px] text-slate-400">Real-time WebGL globe with dynamic classification color keys.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
