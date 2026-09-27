"use client";

import React from 'react';
import { EventPlayback } from './EventPlayback';

export interface TimelineDetection {
  id: number;
  detected_at?: string;
  frp?: number;
  brightness_temperature?: number;
  confidence?: number;
  latitude: number;
  longitude: number;
  is_current?: boolean;
}

interface TemporalTimelineProps {
  timeline: TimelineDetection[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  isPlaying: boolean;
  onTogglePlay: (play: boolean) => void;
}

export const TemporalTimeline: React.FC<TemporalTimelineProps> = ({
  timeline = [],
  selectedIndex,
  onSelectIndex,
  isPlaying,
  onTogglePlay
}) => {
  if (!timeline || timeline.length === 0) return null;

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
    } catch {
      return '';
    }
  };

  const formatTime = (isoStr?: string) => {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="h-20 bg-slate-950/95 border-t border-slate-800/80 px-4 py-2.5 flex items-center justify-between z-20 backdrop-blur-xl font-mono select-none">
      {/* Playback Controls Left */}
      <div className="flex items-center gap-3 pr-4 border-r border-slate-800/80">
        <EventPlayback
          totalSteps={timeline.length}
          currentStepIndex={selectedIndex}
          onStepChange={onSelectIndex}
          isPlaying={isPlaying}
          onTogglePlay={onTogglePlay}
        />
        <div className="hidden sm:block text-[11px] text-slate-400">
          <span className="text-cyan-400 font-bold">{selectedIndex + 1}</span> of {timeline.length} detections
        </div>
      </div>

      {/* Horizontal Scroller of Timeline Nodes */}
      <div className="flex-1 flex items-center gap-3 overflow-x-auto px-4 py-1 scrollbar-none">
        {timeline.map((item, idx) => {
          const isSelected = idx === selectedIndex;
          const isTargetEvent = item.is_current;
          const frp = item.frp ? Math.round(item.frp) : 0;

          return (
            <div
              key={item.id}
              onClick={() => onSelectIndex(idx)}
              className={`flex-shrink-0 cursor-pointer p-1.5 rounded-lg border transition-all duration-150 text-center min-w-[76px] ${
                isSelected
                  ? 'bg-slate-800 border-cyan-400 shadow-md shadow-cyan-950/40 ring-1 ring-cyan-400'
                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900'
              }`}
            >
              <div className="text-[10px] text-slate-400 font-medium">
                {formatDate(item.detected_at)}
              </div>
              <div className="flex items-center justify-center gap-1 my-0.5">
                <span className={`w-2 h-2 rounded-full ${
                  isTargetEvent ? 'bg-red-500 animate-ping' : isSelected ? 'bg-cyan-400' : 'bg-amber-400'
                }`} />
                <span className={`text-xs font-bold ${isSelected ? 'text-cyan-300' : 'text-slate-200'}`}>
                  {frp} MW
                </span>
              </div>
              <div className="text-[9px] text-slate-500">
                {formatTime(item.detected_at)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
