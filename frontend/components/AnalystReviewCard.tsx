"use client";

import React, { useState } from 'react';
import { submitAnalystReview, updateEventStatus } from '@/lib/api';

interface ReviewItem {
  id: number;
  analyst_id: string;
  decision: string;
  comment?: string;
  previous_classification?: string;
  final_classification?: string;
  created_at?: string;
}

interface AnalystReviewCardProps {
  eventId: number;
  currentStatus: string;
  initialReviews?: ReviewItem[];
  originalClassification?: string;
  onStatusUpdated?: (newStatus: string) => void;
  onReviewSubmitted?: (review: ReviewItem) => void;
}

export const AnalystReviewCard: React.FC<AnalystReviewCardProps> = ({
  eventId,
  currentStatus = 'NEW',
  initialReviews = [],
  originalClassification,
  onStatusUpdated,
  onReviewSubmitted
}) => {
  const [reviews, setReviews] = useState<ReviewItem[]>(initialReviews);
  const [decision, setDecision] = useState<'CONFIRM' | 'REJECT' | 'NEEDS_INVESTIGATION'>('CONFIRM');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Status Badge Colors
  const statusStyles: Record<string, string> = {
    NEW: 'bg-blue-950 text-blue-400 border-blue-800',
    INVESTIGATING: 'bg-amber-950 text-amber-300 border-amber-700 animate-pulse',
    CONFIRMED: 'bg-emerald-950 text-emerald-400 border-emerald-800',
    REJECTED: 'bg-rose-950 text-rose-400 border-rose-800',
    CLOSED: 'bg-slate-900 text-slate-400 border-slate-700'
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setStatusMessage(null);
      const res = await submitAnalystReview(eventId, {
        decision,
        comment: comment.trim(),
        analyst_id: 'Analyst-01'
      });

      setReviews(prev => [res, ...prev]);
      setComment('');
      setStatusMessage(`Decision recorded: ${decision}`);
      if (onReviewSubmitted) onReviewSubmitted(res);
      
      // Auto update status if confirm or reject
      if (decision === 'CONFIRM') {
        if (onStatusUpdated) onStatusUpdated('CONFIRMED');
      } else if (decision === 'REJECT') {
        if (onStatusUpdated) onStatusUpdated('REJECTED');
      } else if (decision === 'NEEDS_INVESTIGATION') {
        if (onStatusUpdated) onStatusUpdated('INVESTIGATING');
      }
    } catch (err: unknown) {
      console.error('Review submit failed:', err);
      setStatusMessage('Submission error. Check console.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTransition = async (target: string) => {
    try {
      setIsSubmitting(true);
      setStatusMessage(null);
      await updateEventStatus(eventId, target, `Analyst status change to ${target}`);
      if (onStatusUpdated) onStatusUpdated(target);
      setStatusMessage(`Status transitioned to ${target}`);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      setStatusMessage(errorObj.response?.data?.detail || 'Invalid transition');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '';
    try {
      return new Date(isoStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-3 font-mono text-xs">
      {/* Header with Status */}
      <div className="flex items-center justify-between">
        <span className="text-slate-400 uppercase text-[10px] tracking-wider">
          ANALYST REVIEW & AUDIT
        </span>
        <span className={`px-2 py-0.5 rounded text-[10px] border uppercase font-bold ${statusStyles[currentStatus] || statusStyles.NEW}`}>
          {currentStatus}
        </span>
      </div>

      {/* Lifecycle Transition Buttons */}
      <div className="flex items-center gap-1.5 pt-1 border-t border-slate-800/60 text-[10px]">
        <span className="text-slate-500">TRANSITION:</span>
        {currentStatus === 'NEW' && (
          <button
            onClick={() => handleTransition('INVESTIGATING')}
            disabled={isSubmitting}
            className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 hover:bg-amber-900 border border-amber-800"
          >
            Start Investigation
          </button>
        )}
        {currentStatus === 'INVESTIGATING' && (
          <>
            <button
              onClick={() => handleTransition('CONFIRMED')}
              disabled={isSubmitting}
              className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 hover:bg-emerald-900 border border-emerald-800"
            >
              Confirm
            </button>
            <button
              onClick={() => handleTransition('REJECTED')}
              disabled={isSubmitting}
              className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 hover:bg-rose-900 border border-rose-800"
            >
              Reject
            </button>
            <button
              onClick={() => handleTransition('CLOSED')}
              disabled={isSubmitting}
              className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-600"
            >
              Close
            </button>
          </>
        )}
        {(currentStatus === 'CONFIRMED' || currentStatus === 'REJECTED') && (
          <button
            onClick={() => handleTransition('CLOSED')}
            disabled={isSubmitting}
            className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-600"
          >
            Close Incident
          </button>
        )}
        {currentStatus === 'CLOSED' && (
          <button
            onClick={() => handleTransition('INVESTIGATING')}
            disabled={isSubmitting}
            className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 hover:bg-amber-900 border border-amber-800"
          >
            Reopen
          </button>
        )}
      </div>

      {/* Decision Controls Form */}
      <form onSubmit={handleReviewSubmit} className="space-y-2 pt-1 border-t border-slate-800/40">
        <div className="grid grid-cols-3 gap-1.5 text-[10px]">
          <button
            type="button"
            onClick={() => setDecision('CONFIRM')}
            className={`py-1 rounded font-semibold border transition-all ${
              decision === 'CONFIRM'
                ? 'bg-emerald-950 text-emerald-300 border-emerald-700 shadow'
                : 'bg-slate-950 text-slate-400 hover:text-slate-200 border-slate-800'
            }`}
          >
            CONFIRM
          </button>
          <button
            type="button"
            onClick={() => setDecision('REJECT')}
            className={`py-1 rounded font-semibold border transition-all ${
              decision === 'REJECT'
                ? 'bg-rose-950 text-rose-300 border-rose-700 shadow'
                : 'bg-slate-950 text-slate-400 hover:text-slate-200 border-slate-800'
            }`}
          >
            REJECT
          </button>
          <button
            type="button"
            onClick={() => setDecision('NEEDS_INVESTIGATION')}
            className={`py-1 rounded font-semibold border transition-all ${
              decision === 'NEEDS_INVESTIGATION'
                ? 'bg-amber-950 text-amber-300 border-amber-700 shadow'
                : 'bg-slate-950 text-slate-400 hover:text-slate-200 border-slate-800'
            }`}
          >
            INVESTIGATE
          </button>
        </div>

        <div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Analyst observation notes / verification evidence..."
            rows={2}
            className="w-full bg-slate-950 border border-slate-800 rounded p-1.5 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-cyan-600"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-1.5 rounded bg-cyan-700/80 hover:bg-cyan-600 text-white font-semibold text-xs tracking-wider transition-all disabled:opacity-50"
        >
          {isSubmitting ? 'Recording Decision...' : 'SUBMIT REVIEW'}
        </button>

        {statusMessage && (
          <div className="text-[10px] text-center font-medium text-cyan-400">
            {statusMessage}
          </div>
        )}
      </form>

      {/* Review History Audit Trail */}
      {reviews.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">
            Audit Trail ({reviews.length})
          </div>
          <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
            {reviews.map((r, idx) => (
              <div key={idx} className="p-1.5 rounded bg-slate-950/70 border border-slate-800/70 text-[10px] space-y-0.5">
                <div className="flex justify-between items-center text-slate-400">
                  <span className="font-semibold text-slate-300">{r.analyst_id || 'Analyst'}</span>
                  <span>{formatDate(r.created_at)}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`font-bold ${
                    r.decision === 'CONFIRM' ? 'text-emerald-400' : r.decision === 'REJECT' ? 'text-rose-400' : 'text-amber-400'
                  }`}>
                    {r.decision}
                  </span>
                  {r.final_classification && (
                    <span className="text-slate-400">• {r.final_classification}</span>
                  )}
                  {originalClassification && !r.final_classification && (
                    <span className="text-slate-500">• AI: {originalClassification}</span>
                  )}
                </div>
                {r.comment && (
                  <div className="text-slate-400 italic font-sans text-[10px]">
                    &ldquo;{r.comment}&rdquo;
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
