"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  getAnalyticsOverview,
  getAnalyticsTimeseries,
  getAnalyticsClassifications,
  getAnalyticsRisk,
  getAnalyticsAlerts,
  getAnalyticsFacilities,
  getAnalyticsTrends,
  getAnalyticsAnomalies,
  getAnalyticsComparison,
  KPISummary,
  TimeSeriesResponse,
  TimeSeriesPoint,
  ClassificationAnalyticsResponse,
  RiskAnalyticsResponse,
  AlertAnalyticsResponse,
  FacilityMetric,
  TrendSummary,
  AnomalyItem,
  ComparisonResponse
} from '@/lib/api';

interface AnalyticsDashboardProps {
  onInvestigateEvent: (eventId: number) => void;
  onSelectFacility: (facilityId: number) => void;
  onOpenReportStudio: (type: 'INCIDENT' | 'FACILITY' | 'REGIONAL' | 'EXECUTIVE', targetId?: string) => void;
  onClose?: () => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  onInvestigateEvent,
  onSelectFacility,
  onOpenReportStudio,
  onClose
}) => {
  // Filter States
  const [rangePreset, setRangePreset] = useState<string>('30d');
  const [interval, setInterval] = useState<string>('day');
  const [minFrp, setMinFrp] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // Data States
  const [kpis, setKpis] = useState<KPISummary | null>(null);
  const [timeseries, setTimeseries] = useState<TimeSeriesResponse | null>(null);
  const [classifications, setClassifications] = useState<ClassificationAnalyticsResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskAnalyticsResponse | null>(null);
  const [alertData, setAlertData] = useState<AlertAnalyticsResponse | null>(null);
  const [facilities, setFacilities] = useState<FacilityMetric[]>([]);
  const [trends, setTrends] = useState<Record<string, TrendSummary>>({});
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);

  // Hover state for interactive time-series
  const [hoveredPoint, setHoveredPoint] = useState<TimeSeriesPoint | null>(null);

  // Comparison Modal State
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [compareMode, setCompareMode] = useState<'FACILITY' | 'TIME_PERIOD'>('FACILITY');
  const [facilityAId, setFacilityAId] = useState<number | null>(null);
  const [facilityBId, setFacilityBId] = useState<number | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState<boolean>(false);

  // Load All Analytics Data
  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      const [
        overviewRes,
        tsRes,
        classesRes,
        riskRes,
        alertsRes,
        facRes,
        trendsRes,
        anomaliesRes
      ] = await Promise.all([
        getAnalyticsOverview({ range_preset: rangePreset, min_frp: minFrp }).catch(() => null),
        getAnalyticsTimeseries({ interval, range_preset: rangePreset, min_frp: minFrp }).catch(() => null),
        getAnalyticsClassifications({ range_preset: rangePreset }).catch(() => null),
        getAnalyticsRisk({ range_preset: rangePreset }).catch(() => null),
        getAnalyticsAlerts({ range_preset: rangePreset }).catch(() => null),
        getAnalyticsFacilities({ limit: 15 }).catch(() => []),
        getAnalyticsTrends({ range_preset: rangePreset }).catch(() => ({})),
        getAnalyticsAnomalies({ limit: 10, range_preset: rangePreset }).catch(() => [])
      ]);

      if (overviewRes) setKpis(overviewRes);
      if (tsRes) setTimeseries(tsRes);
      if (classesRes) setClassifications(classesRes);
      if (riskRes) setRiskData(riskRes);
      if (alertsRes) setAlertData(alertsRes);
      if (facRes) setFacilities(facRes);
      if (trendsRes) setTrends(trendsRes);
      if (anomaliesRes) setAnomalies(anomaliesRes);

      // Pre-populate comparison facilities if available
      if (facRes && facRes.length >= 2) {
        setFacilityAId(facRes[0].facility_id);
        setFacilityBId(facRes[1].facility_id);
      }
    } catch (err) {
      console.error('Failed to load analytics dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, [rangePreset, interval, minFrp]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData, refreshTrigger]);

  // Execute Comparison
  const handleExecuteComparison = async () => {
    if (compareMode === 'FACILITY') {
      if (!facilityAId || !facilityBId) return;
      try {
        setCompareLoading(true);
        const res = await getAnalyticsComparison({
          comparison_type: 'FACILITY',
          id_a: facilityAId,
          id_b: facilityBId
        });
        setComparisonResult(res);
      } catch (err) {
        console.error('Facility comparison failed:', err);
      } finally {
        setCompareLoading(false);
      }
    } else {
      // Period vs Period (Current vs Prior Period)
      try {
        setCompareLoading(true);
        const now = new Date();
        const days = rangePreset === '24h' ? 1 : rangePreset === '7d' ? 7 : rangePreset === '90d' ? 90 : 30;
        const currentStart = new Date(now.getTime() - days * 24 * 60 * 60 * 1000).toISOString();
        const currentEnd = now.toISOString();
        const priorStart = new Date(now.getTime() - 2 * days * 24 * 60 * 60 * 1000).toISOString();
        const priorEnd = currentStart;

        const res = await getAnalyticsComparison({
          comparison_type: 'TIME_PERIOD',
          period_a_start: currentStart,
          period_a_end: currentEnd,
          period_b_start: priorStart,
          period_b_end: priorEnd
        });
        setComparisonResult(res);
      } catch (err) {
        console.error('Timeframe comparison failed:', err);
      } finally {
        setCompareLoading(false);
      }
    }
  };

  // Helper: Trend Badge Formatter
  const renderTrendBadge = (trend?: TrendSummary) => {
    if (!trend) return null;
    let color = 'text-slate-400 bg-slate-800/80 border-slate-700';
    let icon = '→';

    if (trend.status === 'INCREASING' || trend.status === 'EMERGING') {
      color = 'text-orange-400 bg-orange-950/40 border-orange-500/30';
      icon = '▲';
    } else if (trend.status === 'DECREASING') {
      color = 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30';
      icon = '▼';
    } else if (trend.status === 'VOLATILE') {
      color = 'text-amber-400 bg-amber-950/40 border-amber-500/30';
      icon = '⚡';
    }

    return (
      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${color}`}>
        <span>{icon}</span>
        <span>{Math.abs(trend.percentage_change).toFixed(1)}%</span>
      </span>
    );
  };

  // Compute SVG Coordinates for Time-Series
  const timeSeriesChartData = useMemo(() => {
    if (!timeseries || !timeseries.data || timeseries.data.length === 0) return null;
    const data = timeseries.data;
    const maxCount = Math.max(...data.map(d => d.count), 1);
    const maxFrp = Math.max(...data.map(d => d.mean_frp), 1);
    const maxAlerts = Math.max(...data.map(d => d.alert_count), 1);

    const width = 800;
    const height = 180;
    const padding = { top: 20, right: 30, bottom: 25, left: 40 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const points = data.map((d, i) => {
      const x = padding.left + (i / Math.max(data.length - 1, 1)) * chartW;
      const yCount = padding.top + chartH - (d.count / maxCount) * chartH;
      const yFrp = padding.top + chartH - (d.mean_frp / maxFrp) * chartH;
      const alertBarH = (d.alert_count / maxAlerts) * (chartH * 0.4);
      return { x, yCount, yFrp, alertBarH, raw: d };
    });

    // Create SVG area and line path for count
    const countPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.yCount.toFixed(1)}`).join(' ');
    const countArea = `${countPath} L ${points[points.length - 1].x.toFixed(1)} ${height - padding.bottom} L ${points[0].x.toFixed(1)} ${height - padding.bottom} Z`;

    // Create SVG line path for mean FRP
    const frpPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.yFrp.toFixed(1)}`).join(' ');

    return {
      width,
      height,
      padding,
      points,
      countPath,
      countArea,
      frpPath,
      maxCount,
      maxFrp,
      maxAlerts
    };
  }, [timeseries]);

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden font-mono select-none">
      {/* 1. Header & Filter Controls Bar */}
      <div className="h-14 border-b border-slate-800 bg-slate-900/80 px-6 flex items-center justify-between shrink-0 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
          <h1 className="text-sm font-bold tracking-wider text-slate-100 uppercase">
            Operational Analytics & Historical Intelligence
          </h1>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700 font-mono">
            ENGINE: ANALYTICS-V1
          </span>
        </div>

        {/* Global Filter Bar */}
        <div className="flex items-center gap-3">
          {/* Preset Buttons */}
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            {['24h', '7d', '30d', '90d', '6m', '1y'].map((p) => (
              <button
                key={p}
                onClick={() => setRangePreset(p)}
                className={`px-2.5 py-1 text-[11px] rounded transition-all font-semibold ${
                  rangePreset === p
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* FRP Filter Dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-950 border border-slate-800 px-2.5 py-1 rounded-lg">
            <span>FRP:</span>
            <select
              value={minFrp ?? ''}
              onChange={(e) => setMinFrp(e.target.value ? Number(e.target.value) : undefined)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="">All Power</option>
              <option value="10">&gt; 10 MW</option>
              <option value="25">&gt; 25 MW</option>
              <option value="50">&gt; 50 MW</option>
              <option value="100">&gt; 100 MW</option>
            </select>
          </div>

          {/* Comparison Mode Trigger */}
          <button
            onClick={() => {
              setIsCompareOpen(true);
              handleExecuteComparison();
            }}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-950/60 border border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/60 transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            <span>Compare</span>
          </button>

          {/* Report Studio Button */}
          <button
            onClick={() => onOpenReportStudio('EXECUTIVE')}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/60 transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Generate Report</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={() => setRefreshTrigger((prev) => prev + 1)}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all disabled:opacity-50"
            title="Refresh Data"
          >
            <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>

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

      {/* 2. Scrollable Dashboard Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Executive KPI Metric Cards Strip */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Card 1: Total Detections */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase tracking-wider">
              <span>Total Events</span>
              {renderTrendBadge(trends['total_events'])}
            </div>
            <div className="text-2xl font-bold text-slate-100 my-1">
              {kpis ? kpis.total_events.toLocaleString() : '—'}
            </div>
            <div className="text-[10px] text-slate-500">
              NASA FIRMS Verified
            </div>
          </div>

          {/* Card 2: Active Ongoing */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase tracking-wider">
              <span>Active Hotspots</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 my-1">
              {kpis ? kpis.active_events.toLocaleString() : '—'}
            </div>
            <div className="text-[10px] text-slate-500">
              Status: UNRESOLVED
            </div>
          </div>

          {/* Card 3: Industrial Ratio */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase tracking-wider">
              <span>Industrial Flares</span>
              {renderTrendBadge(trends['mean_frp'])}
            </div>
            <div className="text-2xl font-bold text-amber-400 my-1">
              {kpis ? kpis.industrial_events.toLocaleString() : '—'}
            </div>
            <div className="text-[10px] text-slate-500">
              {kpis && kpis.total_events > 0
                ? `${((kpis.industrial_events / kpis.total_events) * 100).toFixed(1)}% of total`
                : 'Persistent flares'}
            </div>
          </div>

          {/* Card 4: Radiative Flux (Mean/Peak) */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase tracking-wider">
              <span>Radiative Power</span>
              <span className="text-orange-400 text-[10px]">PEAK: {kpis?.peak_frp ? Math.round(kpis.peak_frp) : 0} MW</span>
            </div>
            <div className="text-2xl font-bold text-orange-400 my-1">
              {kpis?.mean_frp ? kpis.mean_frp.toFixed(1) : '—'}{' '}
              <span className="text-xs text-slate-500 font-normal">MW</span>
            </div>
            <div className="text-[10px] text-slate-500">
              Mean Radiative Flux
            </div>
          </div>

          {/* Card 5: High Risk Volume */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase tracking-wider">
              <span>High / Critical</span>
              {renderTrendBadge(trends['high_risk_count'])}
            </div>
            <div className="text-2xl font-bold text-red-400 my-1">
              {kpis ? kpis.high_risk_count.toLocaleString() : '—'}
            </div>
            <div className="text-[10px] text-slate-500">
              Risk Score &gt;= 70
            </div>
          </div>

          {/* Card 6: Response MTTR */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase tracking-wider">
              <span>Alert MTTR</span>
              <span className="text-cyan-400 text-[10px]">{kpis?.active_alerts ?? 0} ACTIVE</span>
            </div>
            <div className="text-2xl font-bold text-cyan-400 my-1">
              {kpis?.mean_tt_resolve_mins ? `${Math.round(kpis.mean_tt_resolve_mins)}m` : 'N/A'}
            </div>
            <div className="text-[10px] text-slate-500">
              Mean Time To Resolve
            </div>
          </div>
        </div>

        {/* 3. Interactive SVG Time-Series Telemetry */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Chronological Telemetry & Power Excursion
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                  {timeseries?.data.length || 0} intervals
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Thermal event frequency (area), mean FRP output in MW (orange line), and alert volume (purple bars).
              </p>
            </div>

            {/* Time Interval Selector & Legend */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-sm bg-cyan-500/40 border border-cyan-400" />
                  Events
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-0.5 bg-orange-400" />
                  Mean FRP
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-sm bg-purple-500/40" />
                  Alerts
                </span>
              </div>

              <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
                {(['hour', 'day', 'week', 'month'] as const).map((intv) => (
                  <button
                    key={intv}
                    onClick={() => setInterval(intv)}
                    className={`px-2 py-0.5 text-[10px] rounded capitalize transition-all ${
                      interval === intv
                        ? 'bg-slate-800 text-cyan-300 font-semibold shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {intv}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* SVG Chart Rendering */}
          <div className="relative mt-4">
            {timeSeriesChartData ? (
              <div className="relative w-full overflow-x-auto">
                <svg
                  viewBox={`0 0 ${timeSeriesChartData.width} ${timeSeriesChartData.height}`}
                  className="w-full h-48 select-none"
                >
                  <defs>
                    <linearGradient id="eventAreaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Gridlines */}
                  {[0.25, 0.5, 0.75, 1.0].map((ratio) => {
                    const y =
                      timeSeriesChartData.padding.top +
                      (1 - ratio) *
                        (timeSeriesChartData.height -
                          timeSeriesChartData.padding.top -
                          timeSeriesChartData.padding.bottom);
                    return (
                      <line
                        key={ratio}
                        x1={timeSeriesChartData.padding.left}
                        y1={y}
                        x2={timeSeriesChartData.width - timeSeriesChartData.padding.right}
                        y2={y}
                        stroke="#1e293b"
                        strokeDasharray="4 4"
                      />
                    );
                  })}

                  {/* Alert Volume Bars at Bottom */}
                  {timeSeriesChartData.points.map((p, idx) => (
                    <rect
                      key={`alert-${idx}`}
                      x={p.x - 3}
                      y={timeSeriesChartData.height - timeSeriesChartData.padding.bottom - p.alertBarH}
                      width={6}
                      height={p.alertBarH}
                      fill="#a855f7"
                      opacity={0.4}
                      rx={1}
                    />
                  ))}

                  {/* Area Fill for Thermal Events */}
                  <path d={timeSeriesChartData.countArea} fill="url(#eventAreaGrad)" />

                  {/* Stroke Line for Thermal Events */}
                  <path
                    d={timeSeriesChartData.countPath}
                    fill="none"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Stroke Line for Mean FRP */}
                  <path
                    d={timeSeriesChartData.frpPath}
                    fill="none"
                    stroke="#fb923c"
                    strokeWidth={1.8}
                    strokeDasharray="3 3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Interactive Hover Nodes */}
                  {timeSeriesChartData.points.map((p, idx) => (
                    <g
                      key={`pt-${idx}`}
                      className="cursor-pointer"
                      onMouseEnter={() => setHoveredPoint(p.raw)}
                      onMouseLeave={() => setHoveredPoint(null)}
                    >
                      <circle
                        cx={p.x}
                        cy={p.yCount}
                        r={hoveredPoint?.timestamp === p.raw.timestamp ? 5 : 3}
                        fill="#06b6d4"
                        stroke="#0f172a"
                        strokeWidth={2}
                        className="transition-all"
                      />
                    </g>
                  ))}
                </svg>

                {/* Tooltip Card Overlay */}
                {hoveredPoint && (
                  <div className="absolute top-2 right-4 bg-slate-950/95 border border-cyan-500/50 rounded-lg p-2.5 text-xs shadow-xl backdrop-blur-md z-10 pointer-events-none">
                    <div className="text-cyan-400 font-bold border-b border-slate-800 pb-1 mb-1.5">
                      {hoveredPoint.timestamp}
                    </div>
                    <div className="space-y-0.5 text-[11px]">
                      <div className="flex justify-between gap-4">
                        <span className="text-slate-400">Events:</span>
                        <span className="font-bold text-slate-100">{hoveredPoint.count}</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-slate-400">Mean FRP:</span>
                        <span className="font-bold text-orange-400">{hoveredPoint.mean_frp.toFixed(1)} MW</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-slate-400">Peak FRP:</span>
                        <span className="font-bold text-red-400">{hoveredPoint.max_frp.toFixed(1)} MW</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-slate-400">Alerts:</span>
                        <span className="font-bold text-purple-400">{hoveredPoint.alert_count}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-44 flex items-center justify-center text-slate-500 text-xs">
                No time-series data available for the selected parameters.
              </div>
            )}
          </div>
        </div>

        {/* 4. Three-Column Intelligence Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card A: Classification Distribution */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  AI Classification Mix
                </span>
                <span className="text-[10px] text-slate-500">
                  {classifications?.total || 0} classified
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 mb-3">
                XGBoost multiclass telemetry distribution & mean confidence.
              </p>

              <div className="space-y-3">
                {classifications && classifications.breakdown.length > 0 ? (
                  classifications.breakdown.map((item) => (
                    <div key={item.classification} className="text-xs">
                      <div className="flex justify-between items-center text-[11px] mb-1">
                        <span className="font-medium text-slate-300">{item.classification}</span>
                        <span className="text-slate-400">
                          {item.count} ({item.percentage}%) • Conf: {Math.round(item.mean_confidence * 100)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800/80">
                        <div
                          className={`h-full rounded-full ${
                            item.classification.includes('FLARE')
                              ? 'bg-amber-500'
                              : item.classification.includes('WILD')
                              ? 'bg-red-500'
                              : item.classification.includes('AGRIC')
                              ? 'bg-emerald-500'
                              : 'bg-cyan-500'
                          }`}
                          style={{ width: `${Math.min(item.percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-6 text-center text-xs text-slate-500">No classification records found.</div>
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800/80 mt-4 flex items-center justify-between text-[10px] text-slate-500">
              <span>Model: InfernoX-XGB-v1.0</span>
              <span className="text-cyan-400">Multimodal Fusion</span>
            </div>
          </div>

          {/* Card B: Analytical Risk Scoring Distribution */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Risk Tier Distribution
                </span>
                <span className="text-[10px] text-slate-500">
                  Avg: {riskData?.mean_risk_score ? riskData.mean_risk_score.toFixed(1) : 0}/100
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 mb-3">
                Compound severity score based on FRP, land cover, and infrastructure proximity.
              </p>

              {/* Tier Badges */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="bg-slate-950 border border-emerald-500/30 rounded-lg p-2.5">
                  <div className="text-[10px] text-emerald-400 uppercase font-bold">Low Risk (&lt;40)</div>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">
                    {riskData?.tier_counts.LOW || 0}
                  </div>
                </div>
                <div className="bg-slate-950 border border-cyan-500/30 rounded-lg p-2.5">
                  <div className="text-[10px] text-cyan-400 uppercase font-bold">Moderate (40-69)</div>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">
                    {riskData?.tier_counts.MODERATE || 0}
                  </div>
                </div>
                <div className="bg-slate-950 border border-orange-500/30 rounded-lg p-2.5">
                  <div className="text-[10px] text-orange-400 uppercase font-bold">High (70-84)</div>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">
                    {riskData?.tier_counts.HIGH || 0}
                  </div>
                </div>
                <div className="bg-slate-950 border border-red-500/30 rounded-lg p-2.5">
                  <div className="text-[10px] text-red-400 uppercase font-bold">Critical (85+)</div>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">
                    {riskData?.tier_counts.CRITICAL || 0}
                  </div>
                </div>
              </div>

              {/* Histogram Bars */}
              <div className="space-y-1">
                <div className="text-[10px] text-slate-400 uppercase">Score Frequency Histogram:</div>
                <div className="flex items-end gap-2 h-16 pt-2">
                  {riskData?.score_histogram.map((bin) => {
                    const maxBin = Math.max(...riskData.score_histogram.map(b => b.count), 1);
                    const barH = (bin.count / maxBin) * 100;
                    return (
                      <div key={bin.bin} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                        <div
                          className="w-full bg-cyan-500/60 rounded-t transition-all hover:bg-cyan-400"
                          style={{ height: `${Math.max(barH, 4)}%` }}
                          title={`${bin.bin}: ${bin.count} events`}
                        />
                        <span className="text-[9px] text-slate-500">{bin.bin}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800/80 mt-4 flex items-center justify-between text-[10px] text-slate-500">
              <span>Engine: risk-v1</span>
              <span>Deterministic Rules</span>
            </div>
          </div>

          {/* Card C: Alert Lifecycle Funnel */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Alert Lifecycle & Response
                </span>
                <span className="text-[10px] text-slate-500">
                  {alertData?.total_alerts || 0} total
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 mb-3">
                Notification lifecycle, analyst acknowledgement & escalation efficiency.
              </p>

              {/* Lifecycle Funnel Bars */}
              <div className="space-y-2 text-xs">
                {[
                  { label: 'NEW', count: alertData?.status_counts.NEW || 0, color: 'bg-blue-500' },
                  { label: 'ACKNOWLEDGED', count: alertData?.status_counts.ACKNOWLEDGED || 0, color: 'bg-yellow-500' },
                  { label: 'INVESTIGATING', count: alertData?.status_counts.INVESTIGATING || 0, color: 'bg-cyan-500' },
                  { label: 'ESCALATED', count: alertData?.status_counts.ESCALATED || 0, color: 'bg-red-500' },
                  { label: 'RESOLVED', count: alertData?.status_counts.RESOLVED || 0, color: 'bg-emerald-500' },
                  { label: 'DISMISSED', count: alertData?.status_counts.DISMISSED || 0, color: 'bg-slate-600' }
                ].map((st) => (
                  <div key={st.label} className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 w-28">{st.label}</span>
                    <div className="flex-1 mx-2 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full rounded-full ${st.color}`}
                        style={{
                          width: `${
                            alertData && alertData.total_alerts > 0
                              ? Math.min((st.count / alertData.total_alerts) * 100, 100)
                              : 0
                          }%`
                        }}
                      />
                    </div>
                    <span className="text-[11px] font-bold text-slate-200 w-8 text-right">{st.count}</span>
                  </div>
                ))}
              </div>

              {/* Metrics Box */}
              <div className="grid grid-cols-2 gap-2 mt-4 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px]">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Escalation Rate:</span>
                  <div className="text-red-400 font-bold text-sm">
                    {alertData?.escalation_rate_percent.toFixed(1) || 0}%
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Avg Ack Time:</span>
                  <div className="text-cyan-400 font-bold text-sm">
                    {alertData?.mean_tt_acknowledge_mins ? `${Math.round(alertData.mean_tt_acknowledge_mins)}m` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800/80 mt-4 flex items-center justify-between text-[10px] text-slate-500">
              <span>Routing: IN_APP / WEBHOOK</span>
              <span className="text-emerald-400">Guarded Outbound</span>
            </div>
          </div>
        </div>

        {/* 5. Top Industrial Facilities Activity Ranking */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Monitored Industrial Facilities — Thermal Output Ranking
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Refineries, gas flare stacks, chemical complexes & power plants ranked by proximity thermal incidents.
              </p>
            </div>
            <span className="text-[10px] text-slate-500">{facilities.length} monitored facilities</span>
          </div>

          <div className="overflow-x-auto mt-3">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] uppercase text-slate-400 tracking-wider">
                  <th className="py-2 px-3">Facility Name</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3 text-right">Event Count</th>
                  <th className="py-2 px-3 text-right">Mean FRP</th>
                  <th className="py-2 px-3 text-right">Peak FRP</th>
                  <th className="py-2 px-3 text-right">High Risk</th>
                  <th className="py-2 px-3 text-right">Last Detected</th>
                  <th className="py-2 px-3 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {facilities.length > 0 ? (
                  facilities.map((fac) => (
                    <tr key={fac.facility_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">
                        {fac.name}
                        {fac.operator && <span className="block text-[10px] text-slate-500">{fac.operator}</span>}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-sky-300 border border-slate-700">
                          {fac.facility_type}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-100">{fac.event_count}</td>
                      <td className="py-2.5 px-3 text-right text-orange-400 font-mono">
                        {fac.mean_frp.toFixed(1)} MW
                      </td>
                      <td className="py-2.5 px-3 text-right text-red-400 font-mono font-bold">
                        {fac.max_frp.toFixed(1)} MW
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {fac.high_risk_event_count > 0 ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-950/60 text-red-400 border border-red-500/30">
                            {fac.high_risk_event_count}
                          </span>
                        ) : (
                          <span className="text-slate-600">0</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-400 text-[11px]">
                        {fac.last_detected_at ? new Date(fac.last_detected_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => onSelectFacility(fac.facility_id)}
                            className="px-2 py-0.5 rounded text-[10px] bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-900/60 transition-all"
                            title="Inspect Facility"
                          >
                            Inspect
                          </button>
                          <button
                            onClick={() => onOpenReportStudio('FACILITY', fac.facility_id.toString())}
                            className="px-2 py-0.5 rounded text-[10px] bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 transition-all"
                            title="Generate Facility Report"
                          >
                            Dossier
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-6 text-center text-slate-500">
                      No facility detection records found for this period.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* 6. Statistical Anomaly & Power Excursion Feed */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Statistical Anomaly &amp; Thermal Excursion Feed
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Detections where Fire Radiative Power exceeded facility baseline by &gt;= 2.5x or sudden high-intensity flare bursts.
              </p>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-red-950/60 border border-red-500/40 text-red-300">
              {anomalies.length} Excursions Flagged
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
            {anomalies.length > 0 ? (
              anomalies.map((ano) => (
                <div
                  key={ano.event_id}
                  className="bg-slate-950/90 border border-slate-800 hover:border-red-500/40 rounded-lg p-3 transition-all"
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-red-400">#INF-{ano.event_id}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] bg-red-900/30 text-red-300 border border-red-500/30">
                      {ano.excursion_factor.toFixed(1)}x Baseline
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300 font-medium">
                    {ano.facility_name || 'Unassociated Hotspot'}
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 mt-1">
                    <span>Detected: {new Date(ano.detected_at).toLocaleString()}</span>
                    <span className="text-orange-400 font-bold">{Math.round(ano.frp)} MW</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 italic line-clamp-1">
                    {ano.reason}
                  </p>
                  <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500">Baseline: {ano.baseline_mean_frp.toFixed(1)} MW</span>
                    <button
                      onClick={() => onInvestigateEvent(ano.event_id)}
                      className="px-2 py-0.5 rounded text-[10px] bg-slate-800 hover:bg-cyan-950 hover:text-cyan-300 hover:border-cyan-500/40 border border-slate-700 text-slate-300 transition-all"
                    >
                      Investigate
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full py-6 text-center text-xs text-slate-500">
                No statistical anomalies detected in the current filter window.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 7. Comparison Mode Modal */}
      {isCompareOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                  Factual Side-by-Side Comparison Engine
                </h3>
              </div>
              <button
                onClick={() => setIsCompareOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              {/* Mode Selector */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 uppercase">Compare Mode:</span>
                <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
                  <button
                    onClick={() => {
                      setCompareMode('FACILITY');
                      setComparisonResult(null);
                    }}
                    className={`px-3 py-1 text-xs rounded transition-all ${
                      compareMode === 'FACILITY'
                        ? 'bg-indigo-600 text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Facility vs Facility
                  </button>
                  <button
                    onClick={() => {
                      setCompareMode('TIME_PERIOD');
                      setComparisonResult(null);
                    }}
                    className={`px-3 py-1 text-xs rounded transition-all ${
                      compareMode === 'TIME_PERIOD'
                        ? 'bg-indigo-600 text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Current vs Prior Period
                  </button>
                </div>
              </div>

              {/* Facility Selection */}
              {compareMode === 'FACILITY' && (
                <div className="grid grid-cols-2 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">Target Facility A</label>
                    <select
                      value={facilityAId ?? ''}
                      onChange={(e) => setFacilityAId(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      {facilities.map((f) => (
                        <option key={`a-${f.facility_id}`} value={f.facility_id}>
                          {f.name} ({f.facility_type})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">Target Facility B</label>
                    <select
                      value={facilityBId ?? ''}
                      onChange={(e) => setFacilityBId(Number(e.target.value))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      {facilities.map((f) => (
                        <option key={`b-${f.facility_id}`} value={f.facility_id}>
                          {f.name} ({f.facility_type})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Action Trigger */}
              <div className="flex justify-end">
                <button
                  onClick={handleExecuteComparison}
                  disabled={compareLoading}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all disabled:opacity-50"
                >
                  {compareLoading ? 'Computing Comparison...' : 'Run Statistical Comparison'}
                </button>
              </div>

              {/* Comparison Results Card */}
              {comparisonResult && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <span className="font-bold text-xs text-indigo-400">
                      {comparisonResult.label_a} <span className="text-slate-500">vs</span> {comparisonResult.label_b}
                    </span>
                    <span className="text-[10px] text-slate-500">Provenance Verified</span>
                  </div>

                  {/* Metrics Table */}
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="text-[10px] uppercase text-slate-500 border-b border-slate-800/80">
                        <th className="py-1.5">Metric</th>
                        <th className="py-1.5 text-right">{comparisonResult.label_a}</th>
                        <th className="py-1.5 text-right">{comparisonResult.label_b}</th>
                        <th className="py-1.5 text-right">Delta (%)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                      {comparisonResult.metrics.map((m) => (
                        <tr key={m.metric}>
                          <td className="py-2 text-slate-300 font-medium">{m.metric}</td>
                          <td className="py-2 text-right font-bold text-slate-100">{m.value_a}</td>
                          <td className="py-2 text-right font-bold text-slate-100">{m.value_b}</td>
                          <td className="py-2 text-right">
                            {m.delta_percent !== null && m.delta_percent !== undefined ? (
                              <span
                                className={`text-[11px] font-bold ${
                                  m.delta_percent > 0
                                    ? 'text-orange-400'
                                    : m.delta_percent < 0
                                    ? 'text-emerald-400'
                                    : 'text-slate-400'
                                }`}
                              >
                                {m.delta_percent > 0 ? '+' : ''}
                                {m.delta_percent.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* Automated Summary */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-300">
                    <span className="text-slate-500 text-[10px] uppercase block mb-0.5">Automated Intelligence Finding:</span>
                    {comparisonResult.summary}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
