"use client";

import React from 'react';

interface ClassificationCardProps {
  classification: string;
  modelType?: string;
  modelVersion?: string;
  modelProbability?: number;
  confidenceScore?: number;
  confidenceType?: string;
  isCalibrated?: boolean;
  priorityScore?: number;
  priorityLevel?: string;
  evidenceFactors?: string[];
  explanation?: Array<string | { text?: string; factor?: string }>;
  probabilities?: Record<string, number>;
  fallback?: boolean;
}

export const ClassificationCard: React.FC<ClassificationCardProps> = ({
  classification,
  modelType = 'xgboost',
  modelVersion = 'xgb-v1',
  modelProbability,
  confidenceScore,
  confidenceType = 'raw_model_probability',
  isCalibrated = false,
  priorityScore = 50,
  priorityLevel = 'MEDIUM',
  evidenceFactors = [],
  explanation = [],
  probabilities = {},
  fallback = false
}) => {
  const displayProbability = modelProbability ?? confidenceScore ?? 0.85;
  const probPercent = Math.round(displayProbability * (displayProbability <= 1 ? 100 : 1));

  // Determine priority color
  const priorityColors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/40',
    HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
    MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
    LOW: 'bg-blue-500/20 text-blue-400 border-blue-500/40'
  };

  // Extract explanation text
  const cleanExplanation: string[] = [];
  if (evidenceFactors && evidenceFactors.length > 0) {
    cleanExplanation.push(...evidenceFactors);
  } else if (explanation && explanation.length > 0) {
    explanation.forEach(e => {
      if (typeof e === 'string') cleanExplanation.push(e);
      else if (e && e.text) cleanExplanation.push(e.text);
    });
  }

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-3 font-mono">
      {/* Top Bar: Model Type + Priority */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span className="text-slate-400 uppercase text-[10px]">AI CLASSIFICATION</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-800" title={`Model Type: ${modelType}`}>
            {modelType}:{modelVersion}
          </span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] border uppercase font-semibold ${priorityColors[priorityLevel] || priorityColors.MEDIUM}`} title={`Score: ${priorityScore}/100`}>
            {priorityLevel} ({priorityScore})
          </span>
        </div>
      </div>

      {/* Target Classification & Probability */}
      <div className="flex items-end justify-between pt-1 border-t border-slate-800/60">
        <div>
          <div className="text-[10px] text-slate-500 uppercase">PREDICTED TARGET</div>
          <div className="text-sm font-bold text-slate-100 tracking-wide">
            {classification.replace(/_/g, ' ')}
          </div>
          {fallback && (
            <div className="text-[9px] text-amber-400 mt-0.5">
              ⚠️ Prototype heuristic engine (fallback)
            </div>
          )}
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase">MODEL PROBABILITY</div>
          <div className="text-lg font-bold text-cyan-300 leading-none">
            {probPercent}%
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">
            {isCalibrated ? 'Calibrated' : confidenceType.replace(/_/g, ' ')}
          </div>
        </div>
      </div>

      {/* Probability Breakdown Horizontal Bars */}
      {probabilities && Object.keys(probabilities).length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            Class Probabilities
          </div>
          <div className="space-y-1">
            {Object.entries(probabilities)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 5)
              .map(([cls, val]) => {
                const percent = Math.round(val * 100);
                const isWinner = cls.toLowerCase() === classification.toLowerCase();
                return (
                  <div key={cls} className="space-y-0.5">
                    <div className="flex justify-between text-[10px]">
                      <span className={isWinner ? 'text-cyan-300 font-semibold' : 'text-slate-400'}>
                        {cls.replace(/_/g, ' ')}
                      </span>
                      <span className={isWinner ? 'text-cyan-300 font-semibold' : 'text-slate-500'}>
                        {percent}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          isWinner ? 'bg-gradient-to-r from-cyan-500 to-indigo-500' : 'bg-slate-600'
                        }`}
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Model Evidence Factors */}
      {cleanExplanation.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            Evidence Attributions
          </div>
          <div className="space-y-1">
            {cleanExplanation.slice(0, 5).map((factor, idx) => {
              const isNegative = factor.startsWith('-') || factor.toLowerCase().includes('no ') || factor.toLowerCase().includes('limited');
              return (
                <div key={idx} className="flex items-start gap-1.5 text-[11px] leading-tight text-slate-300">
                  <span className={isNegative ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
                    {isNegative ? '•' : '✓'}
                  </span>
                  <span>{factor.replace(/^[+-]\s*/, '')}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
