"use client";

import React from 'react';

export type NavTab = 
  | 'overview' 
  | 'dashboard' 
  | 'events' 
  | 'incidents' 
  | 'alerts' 
  | 'facilities' 
  | 'analytics' 
  | 'reports' 
  | 'monitoring';

interface SidebarNavProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  eventCount?: number;
  facilityCount?: number;
  criticalAlertCount?: number;
  incidentCount?: number;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  activeTab,
  onTabChange,
  eventCount = 0,
  facilityCount = 0,
  criticalAlertCount = 0,
  incidentCount = 0
}) => {
  const navItems = [
    {
      id: 'overview' as NavTab,
      label: 'Mission Overview',
      shortLabel: 'Overview',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      )
    },
    {
      id: 'dashboard' as NavTab,
      label: 'Mission Control',
      shortLabel: 'Globe',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    {
      id: 'events' as NavTab,
      label: 'Live Events',
      shortLabel: 'Events',
      badge: eventCount > 0 ? eventCount : undefined,
      badgeColor: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
        </svg>
      )
    },
    {
      id: 'incidents' as NavTab,
      label: 'Incidents NOC',
      shortLabel: 'Incidents',
      badge: incidentCount > 0 ? incidentCount : undefined,
      badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      )
    },
    {
      id: 'alerts' as NavTab,
      label: 'Active Alerts',
      shortLabel: 'Alerts',
      badge: criticalAlertCount > 0 ? criticalAlertCount : undefined,
      badgeColor: 'bg-red-500/30 text-red-400 border-red-500/50 animate-pulse',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
      )
    },
    {
      id: 'facilities' as NavTab,
      label: 'Infrastructure',
      shortLabel: 'Facilities',
      badge: facilityCount > 0 ? facilityCount : undefined,
      badgeColor: 'bg-sky-500/20 text-sky-400 border-sky-500/40',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      )
    },
    {
      id: 'analytics' as NavTab,
      label: 'Temporal Analysis',
      shortLabel: 'Analytics',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      )
    },
    {
      id: 'reports' as NavTab,
      label: 'Dossier Studio',
      shortLabel: 'Reports',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    },
    {
      id: 'monitoring' as NavTab,
      label: 'Health & NOC',
      shortLabel: 'Monitoring',
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      )
    }
  ];

  return (
    <aside className="w-14 lg:w-48 bg-slate-950/90 border-r border-slate-800/80 flex flex-col justify-between py-3 backdrop-blur-md select-none shrink-0 z-30">
      <div className="space-y-1 px-2">
        <div className="hidden lg:block px-2 py-1 text-[9px] font-mono tracking-wider text-slate-500 uppercase">
          WORKSPACE
        </div>

        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md font-mono text-xs transition-all duration-150 ${
                isActive
                  ? 'bg-slate-800/90 text-cyan-300 border border-slate-700 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
              title={item.label}
            >
              <div className={isActive ? 'text-cyan-400' : 'text-slate-500'}>
                {item.icon}
              </div>
              <span className="hidden lg:inline truncate font-medium">
                {item.label}
              </span>
              {item.badge !== undefined && (
                <span className={`hidden lg:inline-block ml-auto text-[10px] px-1.5 py-0.2 rounded-full border ${item.badgeColor || 'bg-slate-800 text-slate-400'}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Satellite Platform & Engine Info */}
      <div className="px-2 pt-2 border-t border-slate-900/80 hidden lg:block">
        <div className="p-2 rounded bg-slate-900/60 border border-slate-800/60 text-[10px] font-mono text-slate-400 space-y-1">
          <div className="flex justify-between items-center text-slate-500">
            <span>ENGINE:</span>
            <span className="text-emerald-400 font-semibold">V1.0 OPERATIONAL</span>
          </div>
          <div className="flex justify-between items-center text-slate-500">
            <span>FIRMS FEED:</span>
            <span className="text-cyan-400">NRT VIIRS</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
