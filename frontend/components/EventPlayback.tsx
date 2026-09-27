"use client";

import React, { useState, useEffect, useRef } from 'react';

interface EventPlaybackProps {
  totalSteps: number;
  currentStepIndex: number;
  onStepChange: (index: number) => void;
  isPlaying: boolean;
  onTogglePlay: (play: boolean) => void;
}

export const EventPlayback: React.FC<EventPlaybackProps> = ({
  totalSteps,
  currentStepIndex,
  onStepChange,
  isPlaying,
  onTogglePlay
}) => {
  const [speed, setSpeed] = useState<number>(1);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const speeds = [0.5, 1, 2, 5, 10];

  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(250, 1500 / speed);
      timerRef.current = setInterval(() => {
        onStepChange((currentStepIndex + 1) % totalSteps);
      }, intervalMs);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isPlaying, currentStepIndex, totalSteps, speed, onStepChange]);

  return (
    <div className="flex items-center gap-2 font-mono text-xs select-none">
      {/* Play/Pause Button */}
      <button
        onClick={() => onTogglePlay(!isPlaying)}
        className={`px-3 py-1.5 rounded-md font-bold transition-all flex items-center gap-1.5 ${
          isPlaying
            ? 'bg-amber-600 text-white shadow-lg shadow-amber-950/50'
            : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/50'
        }`}
        title={isPlaying ? 'Pause Playback' : 'Play Historical Progression'}
      >
        <span>{isPlaying ? '⏸' : '▶'}</span>
        <span>{isPlaying ? 'PAUSE' : 'PLAY HISTORY'}</span>
      </button>

      {/* Speed Selector */}
      <div className="flex items-center gap-1 bg-slate-900/90 border border-slate-800 rounded-md p-0.5">
        {speeds.map((s) => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
              speed === s
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
};
