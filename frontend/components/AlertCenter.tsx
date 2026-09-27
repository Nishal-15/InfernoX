"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  getAlertsList,
  getAlertStatsSummary,
  acknowledgeAlert,
  investigateAlert,
  escalateAlert,
  resolveAlert,
  dismissAlert,
  AlertData,
  AlertStats
} from '@/lib/api';

interface AlertCenterProps {
  onInvestigateEvent: (eventId: number) => void;
  onClose?: () => void;
}

export const AlertCenter: React.FC<AlertCenterProps> = ({ onInvestigateEvent, onClose }) => {
  // State
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<AlertData | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [actionComment, setActionComment] = useState<string>('');
  const [submittingAction, setSubmittingAction] = useState(false);

  // Load Alerts & Stats
  const loadAlertsData = useCallback(async () => {
    try {
      setLoading(true);
      const params: { severity?: string; status?: string; limit: number } = { limit: 50 };
      if (filterSeverity !== 'ALL') params.severity = filterSeverity;
      if (filterStatus !== 'ALL') params.status = filterStatus;

      const [alertsRes, statsRes] = await Promise.all([
        getAlertsList(params),
        getAlertStatsSummary()
      ]);

      const items: AlertData[] = alertsRes.items || [];
      setAlerts(items);
      setStats(statsRes);

      if (items.length > 0 && !selectedAlert) {
        setSelectedAlert(items[0]);
      } else if (selectedAlert) {
        const refreshed = items.find((a: AlertData) => a.id === selectedAlert.id);
        if (refreshed) setSelectedAlert(refreshed);
      }
    } catch (err) {
      console.error('Failed to load alert center data:', err);
    } finally {
      setLoading(false);
    }
  }, [filterSeverity, filterStatus, selectedAlert]);

  useEffect(() => {
    loadAlertsData();
  }, [loadAlertsData]);

  // Handle Lifecycle Action
  const handleLifecycleAction = async (action: 'acknowledge' | 'investigate' | 'escalate' | 'resolve' | 'dismiss') => {
    if (!selectedAlert) return;
    try {
      setSubmittingAction(true);
      let updated: AlertData;
      if (action === 'acknowledge') {
        updated = await acknowledgeAlert(selectedAlert.id, 'analyst_active', actionComment || undefined);
      } else if (action === 'investigate') {
        updated = await investigateAlert(selectedAlert.id, 'analyst_active', actionComment || undefined);
        onInvestigateEvent(selectedAlert.event_id);
      } else if (action === 'escalate') {
        updated = await escalateAlert(selectedAlert.id, 'analyst_active', actionComment || undefined);
      } else if (action === 'resolve') {
        updated = await resolveAlert(selectedAlert.id, 'analyst_active', actionComment || undefined);
      } else {
        updated = await dismissAlert(selectedAlert.id, 'analyst_active', actionComment || undefined);
      }

      setSelectedAlert(updated);
      setActionComment('');
      loadAlertsData();
    } catch (err) {
      console.error(`Failed to execute ${action} on alert:`, err);
    } finally {
      setSubmittingAction(false);
    }
  };

  // Filter alerts by search query
  const filteredAlerts = alerts.filter(a => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.alert_code.toLowerCase().includes(q) ||
      a.title.toLowerCase().includes(q) ||
      a.message.toLowerCase().includes(q) ||
      a.event_id.toString().includes(q)
    );
  });

  const severityConfigs: Record<string, { bg: string; text: string; border: string; icon: string }> = {
    CRITICAL: { bg: 'bg-red-950/70', text: 'text-red-400', border: 'border-red-800', icon: '🛑' },
    HIGH: { bg: 'bg-orange-950/70', text: 'text-orange-400', border: 'border-orange-800', icon: '🔶' },
    MODERATE: { bg: 'bg-amber-950/70', text: 'text-amber-400', border: 'border-amber-800', icon: '⚠️' },
    LOW: { bg: 'bg-emerald-950/70', text: 'text-emerald-400', border: 'border-emerald-800', icon: '🟢' }
  };

  const statusColors: Record<string, string> = {
    NEW: 'bg-sky-950 text-sky-400 border-sky-800',
    ACKNOWLEDGED: 'bg-blue-950 text-blue-400 border-blue-800',
    INVESTIGATING: 'bg-indigo-950 text-indigo-400 border-indigo-800 animate-pulse',
    ESCALATED: 'bg-red-950 text-red-400 border-red-800 font-bold',
    RESOLVED: 'bg-emerald-950 text-emerald-400 border-emerald-800',
    DISMISSED: 'bg-slate-800 text-slate-400 border-slate-700'
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 font-mono select-none overflow-hidden">
      {/* 1. Top KPI Summary Banners */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/40 flex-shrink-0">
        <div className="flex items-center justify-between pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">🚨</span>
            <div>
              <h1 className="text-base font-bold text-white tracking-wider">
                INCIDENT RESPONSE & ALERT CENTER
              </h1>
              <p className="text-[11px] text-slate-400">
                Continuous analytical risk evaluation, automated rule triggers, and notification routing
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300"
            >
              Back to Map
            </button>
          )}
        </div>

        {/* Severity Stat Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          <div
            onClick={() => setFilterSeverity(filterSeverity === 'CRITICAL' ? 'ALL' : 'CRITICAL')}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              filterSeverity === 'CRITICAL'
                ? 'bg-red-950/80 border-red-500 shadow-lg shadow-red-950/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-red-800'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-bold text-red-400">
                <span>🛑</span> CRITICAL
              </span>
              <span className="text-[10px] text-slate-500">SEV-1</span>
            </div>
            <div className="text-2xl font-bold text-red-400 mt-1">
              {stats?.critical_count ?? 0}
            </div>
          </div>

          <div
            onClick={() => setFilterSeverity(filterSeverity === 'HIGH' ? 'ALL' : 'HIGH')}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              filterSeverity === 'HIGH'
                ? 'bg-orange-950/80 border-orange-500 shadow-lg shadow-orange-950/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-orange-800'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-bold text-orange-400">
                <span>🔶</span> HIGH
              </span>
              <span className="text-[10px] text-slate-500">SEV-2</span>
            </div>
            <div className="text-2xl font-bold text-orange-400 mt-1">
              {stats?.high_count ?? 0}
            </div>
          </div>

          <div
            onClick={() => setFilterSeverity(filterSeverity === 'MODERATE' ? 'ALL' : 'MODERATE')}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              filterSeverity === 'MODERATE'
                ? 'bg-amber-950/80 border-amber-500 shadow-lg shadow-amber-950/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-amber-800'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-bold text-amber-400">
                <span>⚠️</span> MODERATE
              </span>
              <span className="text-[10px] text-slate-500">SEV-3</span>
            </div>
            <div className="text-2xl font-bold text-amber-400 mt-1">
              {stats?.moderate_count ?? 0}
            </div>
          </div>

          <div
            onClick={() => setFilterSeverity(filterSeverity === 'LOW' ? 'ALL' : 'LOW')}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              filterSeverity === 'LOW'
                ? 'bg-emerald-950/80 border-emerald-500 shadow-lg shadow-emerald-950/50'
                : 'bg-slate-900/60 border-slate-800 hover:border-emerald-800'
            }`}
          >
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-bold text-emerald-400">
                <span>🟢</span> LOW
              </span>
              <span className="text-[10px] text-slate-500">SEV-4</span>
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {stats?.low_count ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Filter & Search Controls */}
      <div className="px-4 py-2.5 bg-slate-900/30 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs flex-shrink-0">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search alerts (e.g. ALT-2026, refinery, fire)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-500"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 text-[11px]">Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2 py-1 text-xs outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="NEW">NEW</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="ESCALATED">ESCALATED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="DISMISSED">DISMISSED</option>
            </select>
          </div>

          <button
            onClick={loadAlertsData}
            disabled={loading}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1"
          >
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      {/* 3. Main Workspace: Master-Detail Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Alert List */}
        <div className="w-1/2 md:w-5/12 border-r border-slate-800 overflow-y-auto p-3 space-y-2.5">
          {loading && alerts.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              Loading incident alerts...
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No alerts match the active filters.
            </div>
          ) : (
            filteredAlerts.map((a) => {
              const cfg = severityConfigs[a.severity] || severityConfigs.LOW;
              const isSelected = selectedAlert?.id === a.id;

              return (
                <div
                  key={a.id}
                  onClick={() => setSelectedAlert(a)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all space-y-2 ${
                    isSelected
                      ? 'bg-slate-900 border-cyan-400 shadow-md'
                      : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-900 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs">{cfg.icon}</span>
                      <span className={`px-1.5 py-0.2 rounded font-bold uppercase border text-[10px] ${cfg.bg} ${cfg.text} ${cfg.border}`}>
                        {a.severity}
                      </span>
                      <span className="text-slate-400 font-bold">{a.alert_code}</span>
                    </div>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] border uppercase ${statusColors[a.status] || statusColors.NEW}`}>
                      {a.status}
                    </span>
                  </div>

                  <div className="text-xs font-semibold text-slate-200 line-clamp-1">
                    {a.title}
                  </div>

                  <div className="text-[10px] text-slate-400 line-clamp-1">
                    {a.message}
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-800/60">
                    <span>Target: #INF-2026-{a.event_id.toString().padStart(6, '0')}</span>
                    <span>{new Date(a.created_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} UTC</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Pane: Incident Dossier & Lifecycle Actions */}
        <div className="w-1/2 md:w-7/12 overflow-y-auto p-5 space-y-5 bg-slate-950">
          {selectedAlert ? (
            <div className="space-y-5">
              {/* Incident Header */}
              <div className="space-y-2 pb-3 border-b border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">
                      {severityConfigs[selectedAlert.severity]?.icon}
                    </span>
                    <div>
                      <h2 className="text-base font-bold text-white">
                        {selectedAlert.alert_code}
                      </h2>
                      <div className="text-[11px] text-slate-400">
                        Associated Thermal Event: <span className="text-cyan-400">#INF-2026-{selectedAlert.event_id.toString().padStart(6, '0')}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold border uppercase ${statusColors[selectedAlert.status] || statusColors.NEW}`}>
                      {selectedAlert.status}
                    </span>
                  </div>
                </div>

                <div className="text-sm font-semibold text-slate-200">
                  {selectedAlert.title}
                </div>
                <div className="text-xs text-slate-400 leading-relaxed">
                  {selectedAlert.message}
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 space-y-2">
                <div className="text-[10px] text-slate-400 uppercase font-semibold">
                  INCIDENT TRIAGE & LIFECYCLE ACTIONS
                </div>

                <div className="flex flex-wrap gap-2">
                  {selectedAlert.status === 'NEW' && (
                    <button
                      onClick={() => handleLifecycleAction('acknowledge')}
                      disabled={submittingAction}
                      className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center gap-1"
                    >
                      <span>✓</span> Acknowledge Alert
                    </button>
                  )}

                  {['NEW', 'ACKNOWLEDGED'].includes(selectedAlert.status) && (
                    <button
                      onClick={() => handleLifecycleAction('investigate')}
                      disabled={submittingAction}
                      className="px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs flex items-center gap-1 shadow-md shadow-sky-950/50"
                    >
                      <span>🎯</span> Investigate in 3D
                    </button>
                  )}

                  {['NEW', 'ACKNOWLEDGED', 'INVESTIGATING'].includes(selectedAlert.status) && (
                    <button
                      onClick={() => handleLifecycleAction('escalate')}
                      disabled={submittingAction}
                      className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white font-bold text-xs flex items-center gap-1"
                    >
                      <span>🚨</span> Escalate
                    </button>
                  )}

                  {['ACKNOWLEDGED', 'INVESTIGATING', 'ESCALATED'].includes(selectedAlert.status) && (
                    <button
                      onClick={() => handleLifecycleAction('resolve')}
                      disabled={submittingAction}
                      className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1"
                    >
                      <span>🏁</span> Mark Resolved
                    </button>
                  )}

                  {['ACKNOWLEDGED', 'INVESTIGATING', 'ESCALATED'].includes(selectedAlert.status) && (
                    <button
                      onClick={() => handleLifecycleAction('dismiss')}
                      disabled={submittingAction}
                      className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1"
                    >
                      <span>✕</span> Dismiss False Positive
                    </button>
                  )}
                </div>

                {/* Optional Comment Input */}
                <input
                  type="text"
                  placeholder="Optional analyst operational note or comment..."
                  value={actionComment}
                  onChange={(e) => setActionComment(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-300 outline-none focus:border-cyan-500 mt-2"
                />
              </div>

              {/* Incident Report Payload Details */}
              {selectedAlert.incident_payload && (
                <div className="space-y-3">
                  <div className="text-[10px] text-slate-400 uppercase font-semibold">
                    INCIDENT REPORT PAYLOAD
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase">Risk Evaluation</div>
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">
                          {selectedAlert.incident_payload.risk_score as number ?? 0}/100
                        </span>
                        <span className="text-[10px] text-cyan-400 font-semibold">
                          {selectedAlert.incident_payload.risk_level as string}
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 space-y-1">
                      <div className="text-[10px] text-slate-500 uppercase">Classification</div>
                      <div className="font-bold text-indigo-300">
                        {selectedAlert.incident_payload.classification as string}
                      </div>
                    </div>
                  </div>

                  {/* Routing Recommendation */}
                  {Boolean(selectedAlert.incident_payload.routing) && (
                    <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 space-y-2">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold flex justify-between">
                        <span>RECOMMENDED RESPONSE ROUTING</span>
                        <span className="text-cyan-400 font-mono">
                          {(selectedAlert.incident_payload.routing as Record<string, unknown>).routing_status as string}
                        </span>
                      </div>

                      <div className="text-xs font-bold text-slate-200">
                        {(selectedAlert.incident_payload.routing as Record<string, unknown>).recommended_recipient as string}
                      </div>

                      <div className="text-[11px] text-slate-400">
                        {(selectedAlert.incident_payload.routing as Record<string, unknown>).routing_reason as string}
                      </div>

                      <div className="text-[10px] p-2 rounded bg-slate-950/80 border border-slate-800 text-amber-300">
                        <span className="font-bold">Recommended Action: </span>
                        {(selectedAlert.incident_payload.routing as Record<string, unknown>).recommended_action as string}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Audit Log Trail */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase font-semibold">
                  AUDIT LOG & TIMELINE ({selectedAlert.audit_logs?.length || 0} entries)
                </div>

                <div className="space-y-1.5">
                  {(selectedAlert.audit_logs || []).map((log) => (
                    <div
                      key={log.id}
                      className="p-2 rounded bg-slate-900/40 border border-slate-800/80 flex items-start justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-cyan-400">{log.action}</span>
                          <span className="text-[10px] text-slate-500">by {log.actor}</span>
                        </div>
                        {log.comment && (
                          <div className="text-[10px] text-slate-400 italic">
                            &ldquo;{log.comment}&rdquo;
                          </div>
                        )}
                      </div>
                      <div className="text-[9px] text-slate-500">
                        {new Date(log.timestamp).toLocaleString('en-GB')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs">
              Select an alert from the feed to view incident report and audit timeline.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
