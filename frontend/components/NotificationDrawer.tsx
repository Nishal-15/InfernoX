"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { getNotifications, markNotificationRead, NotificationLogItem } from '@/lib/api';

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectEventId?: (eventId: number) => void;
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  isOpen,
  onClose,
  onSelectEventId
}) => {
  const [notifications, setNotifications] = useState<NotificationLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getNotifications({ unread_only: unreadOnly, limit: 30 });
      setNotifications(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  if (!isOpen) return null;

  const handleMarkAsRead = async (item: NotificationLogItem, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await markNotificationRead(item.id);
      setNotifications(prev =>
        prev.map(n => (n.id === item.id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  const handleClickItem = (item: NotificationLogItem) => {
    const eventId = item.metadata?.event_id;
    if (eventId && onSelectEventId) {
      onSelectEventId(Number(eventId));
      onClose();
    }
  };

  const getSeverityBadge = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return {
          icon: '🛑',
          bg: 'bg-red-950/70 border-red-700/80 text-red-300',
          indicator: 'bg-red-500'
        };
      case 'HIGH':
        return {
          icon: '🔶',
          bg: 'bg-orange-950/70 border-orange-700/80 text-orange-300',
          indicator: 'bg-orange-500'
        };
      case 'MODERATE':
        return {
          icon: '⚠️',
          bg: 'bg-amber-950/70 border-amber-700/80 text-amber-300',
          indicator: 'bg-amber-500'
        };
      default:
        return {
          icon: '🟢',
          bg: 'bg-emerald-950/70 border-emerald-700/80 text-emerald-300',
          indicator: 'bg-emerald-500'
        };
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity select-none font-mono">
      <div 
        className="w-full max-w-md bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-lg">🔔</span>
            <div>
              <div className="text-xs font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <span>In-App Notifications</span>
                {unreadCount > 0 && (
                  <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold">
                    {unreadCount} NEW
                  </span>
                )}
              </div>
              <div className="text-[10px] text-slate-400">
                Audited notification delivery log
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 p-1.5 rounded hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {/* Filter bar */}
        <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-950 flex items-center justify-between text-xs">
          <div className="flex gap-2">
            <button
              onClick={() => setUnreadOnly(false)}
              className={`px-2 py-1 rounded text-[11px] ${!unreadOnly ? 'bg-slate-800 text-cyan-300' : 'text-slate-400 hover:text-slate-200'}`}
            >
              All ({notifications.length})
            </button>
            <button
              onClick={() => setUnreadOnly(true)}
              className={`px-2 py-1 rounded text-[11px] ${unreadOnly ? 'bg-slate-800 text-cyan-300' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Unread ({unreadCount})
            </button>
          </div>

          <button
            onClick={fetchNotifications}
            className="text-[10px] text-slate-400 hover:text-cyan-400 flex items-center gap-1"
          >
            <span>↻ Refresh</span>
          </button>
        </div>

        {/* List of Notifications */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-500">
              <div className="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              Loading notifications...
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 space-y-1">
              <div className="text-2xl mb-1">📭</div>
              <div className="font-semibold text-slate-400">No Notifications</div>
              <div className="text-[10px] text-slate-600">
                New alerts matching configured criteria will appear here in real-time.
              </div>
            </div>
          ) : (
            notifications.map((item) => {
              const badge = getSeverityBadge(item.metadata?.severity);
              const eventId = item.metadata?.event_id;
              const isClickable = Boolean(eventId && onSelectEventId);

              return (
                <div
                  key={item.id}
                  onClick={() => handleClickItem(item)}
                  className={`p-3 rounded-lg border transition-all relative ${
                    isClickable ? 'cursor-pointer hover:border-slate-600' : ''
                  } ${
                    item.is_read
                      ? 'bg-slate-900/40 border-slate-800/60 text-slate-400'
                      : 'bg-slate-900/90 border-slate-700/90 text-slate-200 shadow-md'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{badge.icon}</span>
                      <span className="text-xs font-bold text-slate-200 line-clamp-1">
                        {item.title}
                      </span>
                    </div>

                    {!item.is_read && (
                      <button
                        onClick={(e) => handleMarkAsRead(item, e)}
                        className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 shrink-0"
                        title="Mark as read"
                      >
                        ✓ Mark read
                      </button>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-300 mt-1.5 line-clamp-2">
                    {item.message}
                  </p>

                  <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.2 rounded border ${badge.bg} font-semibold uppercase text-[9px]`}>
                        {item.metadata?.severity || 'LOW'}
                      </span>
                      <span>Channel: {item.channel}</span>
                    </div>
                    <span>{new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>

                  {isClickable && (
                    <div className="mt-1 text-[9px] text-cyan-400 font-semibold flex items-center gap-1">
                      <span>Click to view tactical dossier →</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-slate-800 bg-slate-950 text-[10px] text-slate-500 flex items-center justify-between">
          <span>Provider: InAppNotificationProvider</span>
          <span className="text-emerald-400">● LIVE</span>
        </div>
      </div>
    </div>
  );
};
