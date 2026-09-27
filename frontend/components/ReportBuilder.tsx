"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  generateReport,
  getIncidentReport,
  getFacilityReport,
  getExecutiveReport,
  getRegionalReport,
  getReportHistory,
  ReportDataPayload,
  ReportListItem,
  ReportGenerateRequest
} from '@/lib/api';

interface ReportBuilderProps {
  initialType?: 'INCIDENT' | 'FACILITY' | 'REGIONAL' | 'EXECUTIVE';
  initialTargetId?: string;
  onInvestigateEvent?: (eventId: number) => void;
  onClose?: () => void;
}

export const ReportBuilder: React.FC<ReportBuilderProps> = ({
  initialType = 'EXECUTIVE',
  initialTargetId = '',
  onClose
}) => {
  // Config & Form State
  const [reportType, setReportType] = useState<'INCIDENT' | 'FACILITY' | 'REGIONAL' | 'EXECUTIVE'>(initialType);
  const [targetId, setTargetId] = useState<string>(initialTargetId);
  const [timeframeDays, setTimeframeDays] = useState<number>(90);
  const [regionName, setRegionName] = useState<string>('National Monitored Corridor');
  const [selectedSections, setSelectedSections] = useState<string[]>([
    'summary',
    'characteristics',
    'infrastructure',
    'satellite',
    'temporal',
    'risk_alerts',
    'provenance'
  ]);

  // Preview & Generation State
  const [previewData, setPreviewData] = useState<ReportDataPayload | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [exportLoading, setExportLoading] = useState<boolean>(false);
  const [exportFormat, setExportFormat] = useState<'PDF' | 'CSV' | 'GEOJSON' | 'JSON'>('PDF');
  const [activeTab, setActiveTab] = useState<'BUILDER' | 'HISTORY'>('BUILDER');
  const [reportHistory, setReportHistory] = useState<ReportListItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Load Live Preview Data
  const loadPreview = useCallback(async () => {
    try {
      setPreviewLoading(true);
      let res: ReportDataPayload | null = null;

      if (reportType === 'INCIDENT') {
        const evId = parseInt(targetId || '1', 10);
        res = await getIncidentReport(isNaN(evId) ? 1 : evId);
      } else if (reportType === 'FACILITY') {
        const facId = parseInt(targetId || '1', 10);
        res = await getFacilityReport(isNaN(facId) ? 1 : facId, timeframeDays);
      } else if (reportType === 'REGIONAL') {
        res = await getRegionalReport(regionName);
      } else {
        res = await getExecutiveReport();
      }

      setPreviewData(res);
    } catch (err) {
      console.error('Failed to load report preview:', err);
      setPreviewData(null);
    } finally {
      setPreviewLoading(false);
    }
  }, [reportType, targetId, timeframeDays, regionName]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  // Load Previously Generated Reports
  const loadHistory = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const res = await getReportHistory({ limit: 50 });
      setReportHistory(res || []);
    } catch (err) {
      console.error('Failed to load report history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'HISTORY') {
      loadHistory();
    }
  }, [activeTab, loadHistory]);

  // Handle Section Toggle
  const toggleSection = (secId: string) => {
    setSelectedSections((prev) =>
      prev.includes(secId) ? prev.filter((s) => s !== secId) : [...prev, secId]
    );
  };

  // Trigger Formal Export (PDF, CSV, GeoJSON, JSON)
  const handleExport = async (format: 'PDF' | 'CSV' | 'GEOJSON' | 'JSON') => {
    try {
      setExportLoading(true);
      setExportFormat(format);

      const request: ReportGenerateRequest = {
        report_type: reportType,
        target_id: targetId || undefined,
        format: format,
        sections_to_include: selectedSections,
        parameters: {
          days: timeframeDays,
          region_name: regionName
        },
        generated_by: 'analyst_active'
      };

      const result = await generateReport(request);

      if (format === 'PDF' || format === 'CSV') {
        // Blob file download
        const blob = result as Blob;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `INF-REPORT-${reportType}-${Date.now()}.${format.toLowerCase()}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        // JSON or GeoJSON file download
        const jsonStr = JSON.stringify(result, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `INF-REPORT-${reportType}-${Date.now()}.${format.toLowerCase()}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }

      // Refresh history
      loadHistory();
    } catch (err) {
      console.error(`Export failed for format ${format}:`, err);
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden font-mono select-none">
      {/* 1. Header Studio Bar */}
      <div className="h-14 border-b border-slate-800 bg-slate-900/80 px-6 flex items-center justify-between shrink-0 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <h1 className="text-sm font-bold tracking-wider text-slate-100 uppercase">
            Intelligence Dossier &amp; Publication Studio
          </h1>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 font-mono">
            STRICT PROVENANCE // CONFIDENTIAL
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Studio vs History Tab Toggle */}
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setActiveTab('BUILDER')}
              className={`px-3 py-1 text-xs rounded transition-all font-semibold ${
                activeTab === 'BUILDER'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Report Builder
            </button>
            <button
              onClick={() => setActiveTab('HISTORY')}
              className={`px-3 py-1 text-xs rounded transition-all font-semibold ${
                activeTab === 'HISTORY'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Audit Archive
            </button>
          </div>

          {/* Quick Export PDF Button */}
          {activeTab === 'BUILDER' && (
            <button
              onClick={() => handleExport('PDF')}
              disabled={exportLoading || !previewData}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-all disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>{exportLoading && exportFormat === 'PDF' ? 'Rendering PDF...' : 'Download PDF'}</span>
            </button>
          )}

          {/* Close / Return Button */}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-red-950/80 hover:text-red-300 text-slate-400 transition-all"
              title="Return to Globe"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* 2. Main Studio Content */}
      {activeTab === 'BUILDER' ? (
        <div className="flex-1 flex overflow-hidden">
          {/* Left Column: Configuration Controls Panel */}
          <div className="w-80 border-r border-slate-800 bg-slate-900/40 p-5 overflow-y-auto space-y-5 shrink-0">
            {/* Report Type Selector */}
            <div>
              <label className="block text-[10px] text-slate-400 uppercase font-bold mb-2">
                1. Select Report Template
              </label>
              <div className="space-y-1.5">
                {[
                  { id: 'INCIDENT', label: 'Incident Investigation', desc: 'Single thermal detection dossier' },
                  { id: 'FACILITY', label: 'Facility Intelligence', desc: 'Monitored infrastructure thermal history' },
                  { id: 'REGIONAL', label: 'Regional Assessment', desc: 'Multi-corridor hotspot aggregation' },
                  { id: 'EXECUTIVE', label: 'Executive Briefing', desc: 'National operations & risk overview' }
                ].map((t) => (
                  <div
                    key={t.id}
                    onClick={() => {
                      setReportType(t.id as 'INCIDENT' | 'FACILITY' | 'REGIONAL' | 'EXECUTIVE');
                    }}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all text-xs ${
                      reportType === t.id
                        ? 'bg-emerald-950/50 border-emerald-500/60 text-white'
                        : 'bg-slate-900/60 border-slate-800 hover:bg-slate-900 text-slate-300'
                    }`}
                  >
                    <div className="font-bold flex items-center justify-between">
                      <span>{t.label}</span>
                      {reportType === t.id && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{t.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Target ID / Parameter Input */}
            <div>
              <label className="block text-[10px] text-slate-400 uppercase font-bold mb-1">
                2. Target Scope Parameters
              </label>
              {reportType === 'INCIDENT' && (
                <div>
                  <span className="text-[10px] text-slate-500">Thermal Event ID:</span>
                  <input
                    type="number"
                    value={targetId}
                    onChange={(e) => setTargetId(e.target.value)}
                    placeholder="e.g. 1"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-emerald-500 mt-1"
                  />
                </div>
              )}

              {reportType === 'FACILITY' && (
                <div className="space-y-2">
                  <div>
                    <span className="text-[10px] text-slate-500">Facility ID:</span>
                    <input
                      type="number"
                      value={targetId}
                      onChange={(e) => setTargetId(e.target.value)}
                      placeholder="e.g. 1"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-emerald-500 mt-1"
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500">History Window (Days):</span>
                    <select
                      value={timeframeDays}
                      onChange={(e) => setTimeframeDays(Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none mt-1"
                    >
                      <option value={30}>30 Days</option>
                      <option value={90}>90 Days (Quarterly)</option>
                      <option value={180}>180 Days (Semi-Annual)</option>
                      <option value={365}>365 Days (Annual)</option>
                    </select>
                  </div>
                </div>
              )}

              {reportType === 'REGIONAL' && (
                <div>
                  <span className="text-[10px] text-slate-500">Monitored Corridor / Region:</span>
                  <input
                    type="text"
                    value={regionName}
                    onChange={(e) => setRegionName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-emerald-500 mt-1"
                  />
                </div>
              )}

              {reportType === 'EXECUTIVE' && (
                <div className="text-[11px] text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  Aggregates all active FIRMS detections, high-risk assets, and alert SLAs nationally.
                </div>
              )}
            </div>

            {/* Section Inclusion Checklist */}
            <div>
              <label className="block text-[10px] text-slate-400 uppercase font-bold mb-2">
                3. Sections to Include
              </label>
              <div className="space-y-1.5 text-xs">
                {[
                  { id: 'summary', label: 'Executive Summary' },
                  { id: 'characteristics', label: 'Thermal & FRP Signatures' },
                  { id: 'infrastructure', label: 'Industrial Proximity' },
                  { id: 'satellite', label: 'ESA WorldCover & Multi-Spectral' },
                  { id: 'temporal', label: 'Temporal Persistence Graphs' },
                  { id: 'risk_alerts', label: 'Risk Scores & Alert Audit Trail' },
                  { id: 'provenance', label: 'Data Provenance & Model Stamp' }
                ].map((s) => (
                  <label
                    key={s.id}
                    className="flex items-center gap-2 p-1.5 rounded hover:bg-slate-800/40 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedSections.includes(s.id)}
                      onChange={() => toggleSection(s.id)}
                      className="rounded bg-slate-950 border-slate-700 text-emerald-500 focus:ring-0"
                    />
                    <span className="text-slate-300 text-[11px]">{s.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Export Multi-Format Triggers */}
            <div className="pt-2 border-t border-slate-800 space-y-2">
              <label className="block text-[10px] text-slate-400 uppercase font-bold mb-1">
                4. Multi-Format Publication
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleExport('PDF')}
                  disabled={exportLoading}
                  className="py-2 px-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/60 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <span>📄</span> PDF
                </button>
                <button
                  onClick={() => handleExport('CSV')}
                  disabled={exportLoading}
                  className="py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 hover:bg-slate-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <span>📊</span> CSV
                </button>
                <button
                  onClick={() => handleExport('GEOJSON')}
                  disabled={exportLoading}
                  className="py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 hover:bg-slate-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <span>🗺️</span> GeoJSON
                </button>
                <button
                  onClick={() => handleExport('JSON')}
                  disabled={exportLoading}
                  className="py-2 px-3 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 hover:bg-slate-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <span>📦</span> JSON
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Live Formal Document Preview */}
          <div className="flex-1 bg-slate-950 p-6 overflow-y-auto">
            {previewLoading ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
                <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs">Assembling live intelligence dossier...</span>
              </div>
            ) : previewData ? (
              <div className="max-w-4xl mx-auto bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
                {/* Document Formal Header Banner */}
                <div className="border-b-2 border-emerald-500/80 pb-4">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2">
                    <span className="font-mono tracking-widest text-emerald-400 font-bold">
                      INFERNOX GEOSPATIAL INTELLIGENCE PLATFORM
                    </span>
                    <span className="px-2 py-0.5 rounded bg-red-950/60 text-red-400 border border-red-500/40 text-[10px] font-bold">
                      {previewData.metadata.classification_level}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-slate-100">{previewData.metadata.title}</h2>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-2">
                    <span>
                      <strong className="text-slate-300">REPORT ID:</strong> {previewData.metadata.report_id}
                    </span>
                    <span>
                      <strong className="text-slate-300">GENERATED:</strong>{' '}
                      {new Date(previewData.metadata.generated_at).toLocaleString()}
                    </span>
                    <span>
                      <strong className="text-slate-300">ANALYST:</strong> {previewData.metadata.generated_by}
                    </span>
                  </div>
                </div>

                {/* Key Metrics KPI Strip */}
                {previewData.kpis && Object.keys(previewData.kpis).length > 0 && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-950 p-4 rounded-xl border border-slate-800">
                    {Object.entries(previewData.kpis).map(([key, val]) => (
                      <div key={key}>
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span className="text-base font-bold text-slate-100">
                          {typeof val === 'number'
                            ? key.includes('frp')
                              ? `${val.toFixed(1)} MW`
                              : val
                            : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Executive Summary */}
                {selectedSections.includes('summary') && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-sm bg-emerald-400" />
                      Executive Summary &amp; Findings
                    </h3>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                      {previewData.executive_summary}
                    </p>
                  </div>
                )}

                {/* Structured Sections */}
                {previewData.sections.map((sec) => (
                  <div key={sec.section_id} className="space-y-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-sm bg-cyan-400" />
                      {sec.title}
                    </h3>
                    {sec.summary && (
                      <p className="text-xs text-slate-400 italic mb-2">{sec.summary}</p>
                    )}

                    {/* Render Tabular Data or Key-Value Pairs */}
                    <div className="bg-slate-950/60 rounded-xl border border-slate-800/80 p-4 overflow-x-auto">
                      {sec.data && typeof sec.data === 'object' && !Array.isArray(sec.data) ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {Object.entries(sec.data as Record<string, unknown>).map(([k, v]) => (
                            <div key={k} className="flex justify-between border-b border-slate-800/60 pb-1">
                              <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}:</span>
                              <span className="font-semibold text-slate-200">
                                {typeof v === 'object' ? JSON.stringify(v) : String(v ?? 'N/A')}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : Array.isArray(sec.data) && sec.data.length > 0 ? (
                        <table className="w-full text-xs text-left">
                          <thead>
                            <tr className="border-b border-slate-800 text-[10px] uppercase text-slate-400">
                              {Object.keys((sec.data[0] as Record<string, unknown>) || {}).map((h) => (
                                <th key={h} className="py-1.5 px-2">
                                  {h.replace(/_/g, ' ')}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/40">
                            {sec.data.slice(0, 10).map((row, idx) => (
                              <tr key={idx} className="hover:bg-slate-800/30">
                                {Object.values((row as Record<string, unknown>) || {}).map((val: unknown, cIdx) => (
                                  <td key={cIdx} className="py-2 px-2 text-slate-300">
                                    {typeof val === 'number' ? val.toFixed(1) : String(val ?? '—')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <div className="text-slate-500 text-xs">No records available for this section.</div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Cryptographic Provenance Block */}
                {selectedSections.includes('provenance') && previewData.provenance && (
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 mt-6">
                    <div className="flex items-center justify-between text-[11px] pb-2 border-b border-slate-800">
                      <span className="text-slate-400 font-bold uppercase">
                        Legal &amp; Scientific Data Provenance
                      </span>
                      <span className="text-emerald-400 font-mono text-[10px]">
                        HASH: {previewData.provenance.tamper_seal_hash.slice(0, 16)}...
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-[10px] text-slate-400">
                      <div>
                        <strong className="text-slate-300">Thermal Source:</strong>{' '}
                        {previewData.provenance.firms_source}
                      </div>
                      <div>
                        <strong className="text-slate-300">Spatial Context:</strong>{' '}
                        {previewData.provenance.osm_source}
                      </div>
                      <div>
                        <strong className="text-slate-300">Land Cover:</strong>{' '}
                        {previewData.provenance.land_cover_source}
                      </div>
                      <div>
                        <strong className="text-slate-300">Satellite Imagery:</strong>{' '}
                        {previewData.provenance.satellite_imagery_source}
                      </div>
                      <div>
                        <strong className="text-slate-300">ML Model:</strong>{' '}
                        {previewData.provenance.ml_model_version}
                      </div>
                      <div>
                        <strong className="text-slate-300">Risk Version:</strong>{' '}
                        {previewData.provenance.risk_engine_version}
                      </div>
                    </div>
                    <div className="text-[9px] text-slate-500 pt-2 border-t border-slate-900 italic">
                      Notice: This intelligence report contains AI heuristic and machine learning model inferences.
                      Thermal anomalies detected by VIIRS/MODIS require ground-truthing before emergency escalation.
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                Select parameters to generate an intelligence preview.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Audit Archive Tab */
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-5xl mx-auto bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                  Report Generation Audit Log
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Complete historical record of generated intelligence briefs, parameters, and format exports.
                </p>
              </div>
              <span className="text-[10px] px-2.5 py-1 rounded bg-slate-800 text-slate-300">
                {reportHistory.length} Dossiers Archived
              </span>
            </div>

            <div className="mt-4 overflow-x-auto">
              {historyLoading ? (
                <div className="py-12 text-center text-slate-500 text-xs">Loading report archive...</div>
              ) : reportHistory.length > 0 ? (
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-[10px] uppercase text-slate-400">
                      <th className="py-2.5 px-3">Report ID</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Title</th>
                      <th className="py-2.5 px-3">Target ID</th>
                      <th className="py-2.5 px-3 text-center">Format</th>
                      <th className="py-2.5 px-3 text-right">Created At</th>
                      <th className="py-2.5 px-3 text-right">Analyst</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {reportHistory.map((rep) => (
                      <tr key={rep.report_id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 px-3 font-mono font-bold text-emerald-400">{rep.report_id}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                            {rep.report_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-200">{rep.title}</td>
                        <td className="py-2.5 px-3 text-slate-400">{rep.target_id || 'Global'}</td>
                        <td className="py-2.5 px-3 text-center">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                            {rep.format}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-400">
                          {new Date(rep.created_at).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-300">{rep.created_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No previous reports found. Generate your first dossier from the builder!
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
