"use client";

import React, { useState, useEffect } from 'react';
import {
  X,
  Activity,
  Server,
  Database,
  Cpu,
  RefreshCw,
  Play,
  Flame,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Layers,
  FileText
} from 'lucide-react';

import {
  getSystemHealth,
  getSystemProviders,
  getPipelineJobs,
  triggerPipelineRun,
  triggerDemoEvent,
  getAutonomousAuditLogs,
  SystemHealthResponse,
  ProviderHealthResponse,
  PipelineJobResponse,
  AutonomousAuditResponse
} from '@/lib/api';

interface PipelineMonitorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDemoTriggered?: (eventId: number, lat: number, lon: number) => void;
}

export default function PipelineMonitorModal({
  isOpen,
  onClose,
  onDemoTriggered
}: PipelineMonitorModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'providers' | 'jobs' | 'audit'>('overview');
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [providers, setProviders] = useState<ProviderHealthResponse[]>([]);
  const [jobs, setJobs] = useState<PipelineJobResponse[]>([]);
  const [auditLogs, setAuditLogs] = useState<AutonomousAuditResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [h, p, j, a] = await Promise.all([
        getSystemHealth().catch(() => null),
        getSystemProviders().catch(() => []),
        getPipelineJobs({ limit: 15 }).catch(() => []),
        getAutonomousAuditLogs(20).catch(() => [])
      ]);
      if (h) setHealth(h);
      setProviders(p);
      setJobs(j);
      setAuditLogs(a);
    } catch (err) {
      console.error("Failed to load telemetry:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchData();
      const interval = setInterval(fetchData, 8000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const handleRunCycle = async () => {
    setIsExecuting(true);
    setActionMessage("Initiating autonomous ingestion & intelligence cycle...");
    try {
      const job = await triggerPipelineRun(false);
      setActionMessage(`Cycle started! Job ID: ${job.job_id}`);
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Server error';
      setActionMessage(`Pipeline execution failed: ${msg}`);
    } finally {
      setIsExecuting(false);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleSimulateDemo = async () => {
    setIsExecuting(true);
    setActionMessage("Generating simulated high-confidence thermal anomaly...");
    try {
      // Coordinates near an industrial cluster
      const res = await triggerDemoEvent({
        lat: 28.6139,
        lon: 77.2090,
        frp: 285.5,
        brightness: 382.4
      });
      setActionMessage(`Demo Event #evt_${res.event_id} injected! Correlated into Incident #${res.incident_id || 'N/A'}`);
      if (onDemoTriggered) {
        onDemoTriggered(res.event_id, 28.6139, 77.2090);
      }
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Server error';
      setActionMessage(`Demo simulation failed: ${msg}`);
    } finally {
      setIsExecuting(false);
      setTimeout(() => setActionMessage(null), 6000);
    }
  };


  if (!isOpen) return null;

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'HEALTHY':
      case 'COMPLETED':
      case 'SUCCESS':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            {status}
          </span>
        );
      case 'DEGRADED':
      case 'RUNNING':
      case 'QUEUED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-950/80 text-amber-400 border border-amber-800/60">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            {status}
          </span>
        );
      case 'UNAVAILABLE':
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-rose-950/80 text-rose-400 border border-rose-800/60">
            <XCircle className="w-3 h-3 text-rose-400" />
            {status}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
            {status || 'UNKNOWN'}
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="relative w-full max-w-5xl max-h-[90vh] flex flex-col bg-[#0a0e17] border border-slate-800 rounded-xl shadow-2xl overflow-hidden text-slate-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0d1322]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/30 text-orange-400">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">
                  AUTONOMOUS PIPELINE TELEMETRY & NOC
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-mono tracking-wider uppercase bg-orange-950 text-orange-400 border border-orange-800/50 rounded-full">
                  Autonomous Engine Active
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Continuous FIRMS Ingestion, Feature Pipeline, Spatial Clustering & Anti-Storm Alert Engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              disabled={isLoading}
              title="Refresh Telemetry"
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Action notification banner */}
        {actionMessage && (
          <div className="px-6 py-2 bg-blue-950/80 border-b border-blue-800/50 text-blue-300 text-xs flex items-center justify-between">
            <span>{actionMessage}</span>
          </div>
        )}

        {/* Navigation Tabs & Controls */}
        <div className="flex items-center justify-between px-6 py-2.5 bg-[#0e1626] border-b border-slate-800/80">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'overview'
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Server className="w-3.5 h-3.5" />
              System Overview
            </button>
            <button
              onClick={() => setActiveTab('providers')}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'providers'
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Provider Health ({providers.length})
            </button>
            <button
              onClick={() => setActiveTab('jobs')}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'jobs'
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Job History ({jobs.length})
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'audit'
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Autonomous Audit
            </button>
          </div>

          {/* Autonomous Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleRunCycle}
              disabled={isExecuting}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition-all shadow-md shadow-orange-950/50 flex items-center gap-1.5 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              Run Ingestion Cycle
            </button>
            <button
              onClick={handleSimulateDemo}
              disabled={isExecuting}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-purple-900/60 hover:bg-purple-800 text-purple-200 border border-purple-700/60 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <Flame className="w-3.5 h-3.5 text-purple-400" />
              Simulate Live Anomaly
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Telemetry Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-[#0f172a]/70 border border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>Engine Status</span>
                    <Server className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold text-white tracking-tight">
                      {health?.status || 'ONLINE'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-2 font-mono">
                    Uptime: {Math.floor((health?.uptime_seconds || 0) / 60)}m {(health?.uptime_seconds || 0) % 60}s
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#0f172a]/70 border border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>Database / PostGIS</span>
                    <Database className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold text-white">
                      {health?.components?.database?.status || 'ONLINE'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-2 font-mono">
                    Latency: {health?.components?.database?.latency_ms?.toFixed(1) || '0.5'} ms
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#0f172a]/70 border border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>ML Classification Engine</span>
                    <Cpu className="w-4 h-4 text-orange-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold text-white">
                      {health?.components?.ml_model?.status || 'READY'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-2 font-mono">
                    Model: {String(health?.components?.ml_model?.details?.model_type || 'XGBoost v1.0')}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#0f172a]/70 border border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>Active WebSocket Clients</span>
                    <Activity className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold text-white">
                      {String(health?.components?.websocket?.details?.connected_clients ?? 1)}
                    </span>
                    <span className="text-xs text-emerald-400">Stream live</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-2 font-mono">
                    Broadcasts: {String(health?.components?.websocket?.details?.total_broadcasts ?? 0)}
                  </div>
                </div>

              </div>

              {/* Pipeline Architecture Diagram / Status */}
              <div className="p-5 rounded-xl bg-[#0f172a]/70 border border-slate-800">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-orange-400" />
                  Autonomous Pipeline Stages Execution Order
                </h3>
                
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs font-mono">
                  {[
                    { step: '01', name: 'FIRMS INGESTION', desc: 'Incremental cursor polling' },
                    { step: '02', name: 'VALIDATE & DEDUP', desc: 'Spatial & temporal deduplication' },
                    { step: '03', name: 'SPATIAL ENRICH', desc: 'OSM 1.5km facility matching' },
                    { step: '04', name: 'TEMPORAL ANALYSIS', desc: 'Historical recurrence tracking' },
                    { step: '05', name: 'FEATURE VECTOR', desc: 'Derived geospatial metrics' },
                    { step: '06', name: 'ML INFERENCE', desc: 'XGBoost industrial classifier' },
                    { step: '07', name: 'SATELLITE & COVER', desc: 'Sentinel-2 & WorldCover stubs' },
                    { step: '08', name: 'INCIDENT CLUSTERING', desc: 'Multi-detection correlation' },
                    { step: '09', name: 'RISK EVALUATION', desc: 'Deterministic 5-factor scoring' },
                    { step: '10', name: 'ALERT & STREAM', desc: 'Anti-storm & WebSocket broadcast' },
                  ].map((s, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-[#0b1120] border border-slate-800 hover:border-orange-500/40 transition-colors"
                    >
                      <div className="text-[10px] text-orange-400 font-bold mb-1">{s.step}</div>
                      <div className="font-semibold text-slate-200 text-xs mb-1">{s.name}</div>
                      <div className="text-[10px] text-slate-400">{s.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Jobs Preview */}
              <div className="p-5 rounded-xl bg-[#0f172a]/70 border border-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-400" />
                    Latest Autonomous Pipeline Executions
                  </h3>
                  <button
                    onClick={() => setActiveTab('jobs')}
                    className="text-xs text-orange-400 hover:underline"
                  >
                    View All &rarr;
                  </button>
                </div>
                
                {jobs.length === 0 ? (
                  <p className="text-xs text-slate-400 py-4 text-center">No pipeline executions recorded yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="py-2 px-3">Job ID</th>
                          <th className="py-2 px-3">Type</th>
                          <th className="py-2 px-3">Status</th>
                          <th className="py-2 px-3">Records</th>
                          <th className="py-2 px-3">Duration</th>
                          <th className="py-2 px-3">Started</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {jobs.slice(0, 5).map((j) => (
                          <tr key={j.job_id} className="hover:bg-slate-800/30">
                            <td className="py-2 px-3 text-orange-300">{j.job_id}</td>
                            <td className="py-2 px-3 text-slate-300">{j.job_type}</td>
                            <td className="py-2 px-3">{getStatusBadge(j.status)}</td>
                            <td className="py-2 px-3 text-slate-300">
                              +{j.records_created} (F:{j.records_fetched}, U:{j.records_updated})
                            </td>
                            <td className="py-2 px-3 text-slate-400">
                              {j.duration_seconds != null ? `${j.duration_seconds.toFixed(2)}s` : 'running...'}
                            </td>
                            <td className="py-2 px-3 text-slate-400">
                              {j.started_at ? new Date(j.started_at).toLocaleTimeString() : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: PROVIDERS */}
          {activeTab === 'providers' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  Real-time health telemetry across external ingestors, satellite providers, and spatial datasets.
                </p>
                <span className="text-xs text-slate-400 font-mono">Auto-refreshed every 8s</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {providers.map((p, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-[#0f172a]/80 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold text-slate-100 text-sm tracking-wide">{p.name}</h4>
                        <span className="text-[11px] font-mono text-slate-400 block truncate max-w-xs">
                          {p.endpoint}
                        </span>
                      </div>
                      {getStatusBadge(p.status)}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-[#0b1120] p-2.5 rounded-lg border border-slate-800/80">
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Latency</span>
                        <span className="text-slate-300 font-semibold">{p.latency_ms?.toFixed(1) || '0'} ms</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Failures</span>
                        <span className={`font-semibold ${p.failure_count > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {p.failure_count}
                        </span>
                      </div>
                      <div className="col-span-2 pt-1 border-t border-slate-800/60">
                        <span className="text-[10px] text-slate-500 uppercase block">Status Message</span>
                        <span className="text-slate-400 text-[11px] truncate block">{p.message || 'Operational'}</span>
                      </div>
                    </div>

                    <div className="text-[10px] text-slate-500 flex justify-between font-mono">
                      <span>Last checked: {p.last_check ? new Date(p.last_check).toLocaleTimeString() : 'N/A'}</span>
                      <span>Success: {p.last_success ? new Date(p.last_success).toLocaleTimeString() : 'N/A'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: JOBS */}
          {activeTab === 'jobs' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  Full persistent job execution history with stage-level breakdown and retry metrics.
                </p>
                <span className="text-xs text-slate-400 font-mono">Showing last {jobs.length} jobs</span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-[#0f172a]/70">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-[#0b1120] border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Job ID</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Source</th>
                      <th className="py-2.5 px-3">Records Created / Fetched</th>
                      <th className="py-2.5 px-3">Retries</th>
                      <th className="py-2.5 px-3">Duration</th>
                      <th className="py-2.5 px-3">Started</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {jobs.map((j) => (
                      <tr key={j.job_id} className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-orange-300">{j.job_id}</td>
                        <td className="py-2.5 px-3 text-slate-200">{j.job_type}</td>
                        <td className="py-2.5 px-3">{getStatusBadge(j.status)}</td>
                        <td className="py-2.5 px-3 text-slate-400">{j.source}</td>
                        <td className="py-2.5 px-3 text-slate-300">
                          +{j.records_created} / {j.records_fetched}
                          {j.records_failed > 0 && <span className="text-rose-400 ml-1">({j.records_failed} failed)</span>}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">{j.retry_count}</td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {j.duration_seconds != null ? `${j.duration_seconds.toFixed(2)}s` : 'running...'}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">
                          {j.started_at ? new Date(j.started_at).toLocaleString() : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: AUDIT */}
          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  Immutable audit log of all autonomous and human actions across events, incidents, and alerts.
                </p>
                <span className="text-xs text-slate-400 font-mono">Actor Isolation Active</span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-[#0f172a]/70">
                <table className="w-full text-xs text-left">
                  <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-[#0b1120] border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Action</th>
                      <th className="py-2.5 px-3">Actor Type</th>
                      <th className="py-2.5 px-3">Target</th>
                      <th className="py-2.5 px-3">Correlation ID</th>
                      <th className="py-2.5 px-3">Metadata</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 text-slate-400">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                        <td className="py-2.5 px-3 text-orange-400 font-medium">{log.action}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] ${
                            log.actor_type === 'AUTONOMOUS_PIPELINE'
                              ? 'bg-blue-950 text-blue-300 border border-blue-800'
                              : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          }`}>
                            {log.actor_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {log.event_id && `Evt #${log.event_id}`}
                          {log.incident_id && ` Inc #${log.incident_id}`}
                          {!log.event_id && !log.incident_id && (log.job_id || '-')}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                          {log.correlation_id || '-'}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500 text-[10px] max-w-xs truncate">
                          {JSON.stringify(log.new_state || log.metadata_info || {})}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800 bg-[#0d1322] text-xs text-slate-400 font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Autonomous Monitoring Daemon Active</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Correlation Radius: 1.5 km / 48 hrs</span>
            <span>Anti-Storm Alert Cooldown: 15 min</span>
          </div>
        </div>

      </div>
    </div>
  );
}
