"use client";

import React, { useState, useEffect } from 'react';
import { compareEvents, getEventsList } from '@/lib/api';

interface EventCandidate {
  id: number;
  satellite?: string;
  frp?: number;
}

interface EventComparisonCard {
  id: number;
  frp?: number;
  active_days?: number;
  nearest_facility_name?: string;
  distance_to_facility_meters?: number | null;
  classification?: string;
  model_probability?: number;
  land_cover_category?: string;
  confidence?: number;
  priority_score?: number;
  priority_level?: string;
}

interface ComparisonMetrics {
  frp_ratio_a_to_b?: number;
  active_days_delta?: number;
  distance_delta_meters?: number;
  same_classification?: boolean;
}

interface ComparisonResult {
  event_a: EventComparisonCard;
  event_b: EventComparisonCard;
  comparison_metrics?: ComparisonMetrics;
}

interface EventComparisonModalProps {
  currentEventId: number | null;
  isOpen: boolean;
  onClose: () => void;
}

export const EventComparisonModal: React.FC<EventComparisonModalProps> = ({
  currentEventId,
  isOpen,
  onClose
}) => {
  const [targetId, setTargetId] = useState<number | null>(null);
  const [recentEvents, setRecentEvents] = useState<EventCandidate[]>([]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    // Load available events for comparison
    const loadEvents = async () => {
      try {
        const res = await getEventsList({ limit: 20 });
        const filtered = (res.items || []).filter((e: EventCandidate) => e.id !== currentEventId);
        setRecentEvents(filtered);
        if (filtered.length > 0) {
          setTargetId((prev) => (prev !== null ? prev : filtered[0].id));
        }
      } catch (err) {
        console.error('Failed to load comparison candidates:', err);
      }
    };

    loadEvents();
  }, [isOpen, currentEventId]);

  useEffect(() => {
    if (!currentEventId || !targetId) return;

    const runCompare = async () => {
      try {
        setLoading(true);
        const data = await compareEvents(currentEventId, targetId);
        setComparison(data);
      } catch (err) {
        console.error('Comparison request failed:', err);
      } finally {
        setLoading(false);
      }
    };

    runCompare();
  }, [currentEventId, targetId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-mono select-none">
      <div className="bg-slate-950 border border-slate-800 rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚖️</span>
            <div>
              <h2 className="text-sm font-bold text-slate-100">Analytical Event Comparison</h2>
              <div className="text-[10px] text-slate-400">Side-by-side evidence, persistence, and classification cross-reference</div>
            </div>
          </div>

          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800">
            ✕
          </button>
        </div>

        {/* Selection Bar */}
        <div className="p-3 bg-slate-900/40 border-b border-slate-800/80 flex items-center justify-between text-xs">
          <span className="text-slate-400">Comparing with:</span>
          <select
            value={targetId || ''}
            onChange={(e) => setTargetId(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2.5 py-1 text-xs outline-none focus:border-cyan-500"
          >
            {recentEvents.map((ev) => (
              <option key={ev.id} value={ev.id}>
                Event #{ev.id} — {ev.satellite} (FRP: {Math.round(ev.frp || 0)} MW)
              </option>
            ))}
          </select>
        </div>

        {/* Comparison Table */}
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400">
            <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
            Calculating multi-event comparison metrics...
          </div>
        ) : comparison ? (
          <div className="p-5 space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-4">
              {/* Event A */}
              <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
                  <span className="font-bold text-cyan-300">
                    EVENT A (#{comparison.event_a?.id})
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-400 border border-cyan-800">
                    SELECTED
                  </span>
                </div>

                <div className="space-y-1.5 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Fire Radiative Power:</span>
                    <span className="text-amber-400 font-bold">{comparison.event_a?.frp?.toFixed(1)} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Persistence Active Days:</span>
                    <span className="text-slate-200 font-semibold">{comparison.event_a?.active_days} days</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Nearest Facility:</span>
                    <span className="text-sky-300 truncate max-w-[150px]">{comparison.event_a?.nearest_facility_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Distance to Facility:</span>
                    <span className="text-slate-200">{comparison.event_a?.distance_to_facility_meters ? `${comparison.event_a.distance_to_facility_meters} m` : 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">ML Classification:</span>
                    <span className="text-indigo-400 font-bold">{comparison.event_a?.classification}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Model Probability:</span>
                    <span className="text-slate-200">{Math.round((comparison.event_a?.model_probability || 0.8) * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Land Cover:</span>
                    <span className="text-emerald-400">{comparison.event_a?.land_cover_category}</span>
                  </div>
                </div>
              </div>

              {/* Event B */}
              <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
                  <span className="font-bold text-amber-300">
                    EVENT B (#{comparison.event_b?.id})
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                    COMPARISON
                  </span>
                </div>

                <div className="space-y-1.5 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Fire Radiative Power:</span>
                    <span className="text-amber-400 font-bold">{comparison.event_b?.frp?.toFixed(1)} MW</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Persistence Active Days:</span>
                    <span className="text-slate-200 font-semibold">{comparison.event_b?.active_days} days</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Nearest Facility:</span>
                    <span className="text-sky-300 truncate max-w-[150px]">{comparison.event_b?.nearest_facility_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Distance to Facility:</span>
                    <span className="text-slate-200">{comparison.event_b?.distance_to_facility_meters ? `${comparison.event_b.distance_to_facility_meters} m` : 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">ML Classification:</span>
                    <span className="text-indigo-400 font-bold">{comparison.event_b?.classification}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Model Probability:</span>
                    <span className="text-slate-200">{Math.round((comparison.event_b?.model_probability || 0.8) * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Land Cover:</span>
                    <span className="text-emerald-400">{comparison.event_b?.land_cover_category}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Comparison Metrics Summary */}
            <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="font-semibold text-slate-300 text-xs">Summary Deltas</div>
              <div className="flex justify-between">
                <span>FRP Ratio (A / B):</span>
                <span className="text-amber-400 font-bold">{comparison.comparison_metrics?.frp_ratio_a_to_b}x</span>
              </div>
              <div className="flex justify-between">
                <span>Active Days Delta:</span>
                <span className="text-slate-200">{comparison.comparison_metrics?.active_days_delta} days</span>
              </div>
              <div className="flex justify-between">
                <span>Classification Consistency:</span>
                <span className={comparison.comparison_metrics?.same_classification ? 'text-emerald-400' : 'text-amber-400'}>
                  {comparison.comparison_metrics?.same_classification ? 'MATCHING' : 'DIFFERENT'}
                </span>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
