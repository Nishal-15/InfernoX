"use client";

import React, { useState, useEffect } from 'react';
import { getNotificationPreferences, saveNotificationPreferences, NotificationPreferences } from '@/lib/api';

interface AlertPreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AlertPreferencesModal: React.FC<AlertPreferencesModalProps> = ({
  isOpen,
  onClose
}) => {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    user_id: 'Analyst-01',
    channels: ['in_app'],
    subscribed_severities: ['CRITICAL', 'HIGH'],
    subscribed_classifications: ['Industrial Fire', 'Gas Flare', 'Wildfire'],
    min_risk_score: 50,
    quiet_hours_enabled: false
  });
  const [loading, setLoading] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      getNotificationPreferences('Analyst-01')
        .then((res: Record<string, unknown>) => {
          if (res) {
            setPreferences((prev: NotificationPreferences) => ({
              ...prev,
              channels: (res.channels as string[]) || prev.channels,
              subscribed_severities: (res.subscribed_severities as string[]) || prev.subscribed_severities,
              subscribed_classifications: (res.subscribed_categories as string[]) || (res.subscribed_classifications as string[]) || prev.subscribed_classifications,
              min_risk_score: (res.min_risk_score as number) ?? prev.min_risk_score,
              quiet_hours_enabled: (res.quiet_hours_enabled as boolean) ?? prev.quiet_hours_enabled
            }));
          }
        })
        .catch((err) => console.warn('Could not load preferences:', err))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleToggleSeverity = (sev: string) => {
    setPreferences((prev: NotificationPreferences) => {
      const current = prev.subscribed_severities || [];
      const updated = current.includes(sev)
        ? current.filter((s: string) => s !== sev)
        : [...current, sev];
      return { ...prev, subscribed_severities: updated };
    });
  };

  const handleToggleClassification = (cls: string) => {
    setPreferences((prev: NotificationPreferences) => {
      const current = prev.subscribed_classifications || [];
      const updated = current.includes(cls)
        ? current.filter((c: string) => c !== cls)
        : [...current, cls];
      return { ...prev, subscribed_classifications: updated };
    });
  };

  const handleToggleChannel = (ch: string) => {
    setPreferences((prev: NotificationPreferences) => {
      const current = prev.channels || [];
      const updated = current.includes(ch)
        ? current.filter((c: string) => c !== ch)
        : [...current, ch];
      return { ...prev, channels: updated };
    });
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await saveNotificationPreferences(preferences);
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 900);
    } catch (err) {
      console.error('Failed to save preferences:', err);
    } finally {
      setLoading(false);
    }
  };

  const severities = [
    { id: 'CRITICAL', label: 'Critical Risk', badge: '🛑 CRITICAL' },
    { id: 'HIGH', label: 'High Priority', badge: '🔶 HIGH' },
    { id: 'MODERATE', label: 'Moderate', badge: '⚠️ MODERATE' },
    { id: 'LOW', label: 'Low Significance', badge: '🟢 LOW' }
  ];

  const classifications = [
    'Industrial Fire',
    'Gas Flare',
    'Wildfire',
    'Agricultural Burning',
    'Persistent Thermal Source'
  ];

  const channels = [
    { id: 'in_app', label: 'In-App Telemetry Banner', status: 'ACTIVE' },
    { id: 'email', label: 'Email Digest (Stubbed)', status: 'GUARDED' },
    { id: 'webhook', label: 'Enterprise Webhook (Stubbed)', status: 'GUARDED' },
    { id: 'sms', label: 'SMS Notification (Stubbed)', status: 'GUARDED' }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-mono select-none">
      <div 
        className="w-full max-w-xl bg-slate-950 border border-slate-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/70 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">⚙️</span>
            <div>
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Alert & Notification Preferences
              </h2>
              <div className="text-[10px] text-slate-400">
                Configure analytical alert thresholds and recipient channels
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 p-1.5 rounded hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 space-y-5 max-h-[75vh] overflow-y-auto text-xs">
          {/* Subscribed Severities */}
          <div>
            <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">
              1. Minimum Alert Severity Subscriptions
            </label>
            <div className="grid grid-cols-2 gap-2">
              {severities.map((sev) => {
                const checked = preferences.subscribed_severities?.includes(sev.id);
                return (
                  <label
                    key={sev.id}
                    className={`flex items-center gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-all ${
                      checked
                        ? 'bg-slate-900 border-cyan-500/70 text-slate-200'
                        : 'bg-slate-900/40 border-slate-800/80 text-slate-500 hover:border-slate-700'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleSeverity(sev.id)}
                      className="accent-cyan-500 w-4 h-4 rounded"
                    />
                    <span className="font-semibold text-xs">{sev.badge}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Subscribed Classifications */}
          <div>
            <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">
              2. Subscribed Event Classifications
            </label>
            <div className="space-y-1.5">
              {classifications.map((cls) => {
                const checked = preferences.subscribed_classifications?.includes(cls);
                return (
                  <label
                    key={cls}
                    className={`flex items-center justify-between p-2 rounded-md border cursor-pointer transition-all ${
                      checked
                        ? 'bg-slate-900/80 border-slate-700 text-slate-200'
                        : 'bg-slate-950 border-slate-800/60 text-slate-500'
                    }`}
                  >
                    <span className="font-mono text-xs">{cls}</span>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleClassification(cls)}
                      className="accent-cyan-500 w-4 h-4 rounded"
                    />
                  </label>
                );
              })}
            </div>
          </div>

          {/* Minimum Risk Score Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                3. Analytical Risk Floor
              </label>
              <span className="text-cyan-400 font-bold font-mono">
                {preferences.min_risk_score} / 100
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="90"
              step="5"
              value={preferences.min_risk_score ?? 50}
              onChange={(e) => setPreferences((prev: NotificationPreferences) => ({ ...prev, min_risk_score: Number(e.target.value) }))}
              className="w-full accent-cyan-500 bg-slate-800 rounded-lg cursor-pointer h-2"
            />
            <div className="text-[10px] text-slate-500 mt-1 flex justify-between">
              <span>0 (All Events)</span>
              <span>50 (High Risk Only)</span>
              <span>75 (Critical Only)</span>
            </div>
          </div>

          {/* Delivery Channels */}
          <div>
            <label className="block text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-2">
              4. Notification Channels & Safe Gateways
            </label>
            <div className="space-y-2">
              {channels.map((ch) => {
                const checked = preferences.channels?.includes(ch.id);
                return (
                  <div
                    key={ch.id}
                    className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/50 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-slate-200 font-medium">{ch.label}</div>
                      <div className="text-[10px] text-slate-500">
                        {ch.id === 'in_app'
                          ? 'Real-time WebSocket & Mission Control in-app notification feed'
                          : 'Channel requires authorized integration credentials to activate'}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold border ${
                        ch.status === 'ACTIVE'
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                          : 'bg-amber-950 text-amber-400 border-amber-800'
                      }`}>
                        {ch.status}
                      </span>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => handleToggleChannel(ch.id)}
                        disabled={ch.id === 'in_app'}
                        className="accent-cyan-500 w-4 h-4 rounded cursor-pointer"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Safety Disclaimer */}
          <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-800/40 text-[10px] text-amber-300/80 leading-relaxed">
            <strong className="text-amber-200">Safety Notice:</strong> External notification dispatches (Email/SMS/Webhook) require explicit operator authorization and verified recipient configuration. InfernoX does not perform autonomous emergency dispatch.
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <div className="text-[10px] text-slate-500">
            User: <span className="text-slate-300 font-semibold">{preferences.user_id}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-md border border-slate-700 hover:bg-slate-800 text-slate-300 text-xs font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-4 py-1.5 rounded-md bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-cyan-950/50 flex items-center gap-1.5"
            >
              {loading ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Saving...</span>
                </>
              ) : savedSuccess ? (
                <span>✓ Preferences Saved!</span>
              ) : (
                <span>Save Preferences</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
