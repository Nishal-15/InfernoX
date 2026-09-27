"use client";

import React, { useState, useEffect } from 'react';
import { getFacilityInvestigation, getFacilityTimeline } from '@/lib/api';

interface FacilityMetrics {
  risk_level: string;
  total_thermal_events: number;
  persistent_sources_count: number;
  max_frp: number;
  mean_frp: number;
}

interface FacilityInvestigationData {
  facility: {
    id: number;
    name: string;
    facility_type: string;
    operator?: string;
    latitude: number;
    longitude: number;
  };
  metrics: FacilityMetrics;
  nearby_clusters?: Array<{
    cluster_id: string;
    detection_count: number;
    distance_meters: number;
  }>;
}

interface WeeklyActivity {
  week_label: string;
  count: number;
  mean_frp: number;
}

interface FacilityTimelineData {
  total_detections: number;
  weekly_activity: WeeklyActivity[];
}

interface FacilityModalProps {
  facilityId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onFlyToFacility: (longitude: number, latitude: number) => void;
  onGenerateReport?: (facilityId: number) => void;
}

export const FacilityModal: React.FC<FacilityModalProps> = ({
  facilityId,
  isOpen,
  onClose,
  onFlyToFacility,
  onGenerateReport
}) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<FacilityInvestigationData | null>(null);
  const [timeline, setTimeline] = useState<FacilityTimelineData | null>(null);

  useEffect(() => {
    if (!isOpen || !facilityId) return;

    const fetchDetails = async () => {
      try {
        setLoading(true);
        const [inv, time] = await Promise.all([
          getFacilityInvestigation(facilityId),
          getFacilityTimeline(facilityId, 30)
        ]);
        setData(inv);
        setTimeline(time);
      } catch (err) {
        console.error('Failed to load facility investigation:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [facilityId, isOpen]);

  if (!isOpen) return null;

  const riskColors: Record<string, string> = {
    CRITICAL: 'bg-red-950 text-red-400 border-red-800 animate-pulse',
    ELEVATED: 'bg-orange-950 text-orange-400 border-orange-800',
    MODERATE: 'bg-amber-950 text-amber-400 border-amber-800',
    NOMINAL: 'bg-emerald-950 text-emerald-400 border-emerald-800'
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 font-mono select-none">
      <div className="bg-slate-950 border border-slate-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-start justify-between bg-slate-900/60">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🏭</span>
              <h2 className="text-sm font-bold text-slate-100">
                {data?.facility?.name || 'Industrial Facility Context'}
              </h2>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {data?.facility?.facility_type} • Operator: {data?.facility?.operator || 'Unknown'}
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400">
            <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
            Loading facility telemetry & historical cluster analysis...
          </div>
        ) : data ? (
          <div className="p-5 space-y-4 text-xs">
            {/* Telemetry Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Risk Level</div>
                <div className={`mt-1 inline-block px-1.5 py-0.5 rounded text-[10px] font-bold border ${riskColors[data.metrics?.risk_level] || riskColors.NOMINAL}`}>
                  {data.metrics?.risk_level}
                </div>
              </div>

              <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Thermal Detections</div>
                <div className="text-base font-bold text-cyan-300 mt-0.5">
                  {data.metrics?.total_thermal_events}
                </div>
              </div>

              <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Persistent Sources</div>
                <div className="text-base font-bold text-amber-300 mt-0.5">
                  {data.metrics?.persistent_sources_count}
                </div>
              </div>

              <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">Max FRP</div>
                <div className="text-base font-bold text-red-400 mt-0.5">
                  {data.metrics?.max_frp} MW
                </div>
              </div>
            </div>

            {/* 30-Day Activity Bar Chart */}
            {timeline?.weekly_activity && (
              <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="flex justify-between items-center text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-300">FACILITY THERMAL HISTORY (LAST 30 DAYS)</span>
                  <span>{timeline.total_detections} total anomalies</span>
                </div>

                <div className="grid grid-cols-4 gap-2 pt-2">
                  {timeline.weekly_activity.map((w: WeeklyActivity, idx: number) => {
                    const count = w.count;
                    const maxCount = Math.max(...timeline.weekly_activity.map((x: WeeklyActivity) => x.count), 1);
                    const heightPercent = Math.max(15, Math.round((count / maxCount) * 100));

                    return (
                      <div key={idx} className="flex flex-col items-center gap-1.5">
                        <div className="text-[10px] text-cyan-400 font-bold">{count}</div>
                        <div className="w-full bg-slate-950 h-24 rounded flex items-end p-1">
                          <div
                            className="w-full bg-gradient-to-t from-orange-600 to-amber-400 rounded-sm transition-all"
                            style={{ height: `${heightPercent}%` }}
                            title={`Avg FRP: ${w.mean_frp} MW`}
                          />
                        </div>
                        <div className="text-[10px] text-slate-400">{w.week_label}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <div className="text-[10px] text-slate-500">
                Coords: {data.facility.latitude.toFixed(4)}, {data.facility.longitude.toFixed(4)}
              </div>

              <div className="flex items-center gap-2">
                {onGenerateReport && (
                  <button
                    onClick={() => {
                      onGenerateReport(data.facility.id);
                      onClose();
                    }}
                    className="px-3 py-2 rounded-lg bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 font-bold text-xs flex items-center gap-1.5 transition-all"
                  >
                    <span>📄 Facility Report</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    onFlyToFacility(data.facility.longitude, data.facility.latitude);
                    onClose();
                  }}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-lg shadow-sky-950/50 flex items-center gap-1.5 transition-all"
                >
                  <span>🎯 Investigate in 3D</span>
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
