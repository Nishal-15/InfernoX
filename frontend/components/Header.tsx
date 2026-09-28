"use client";

import React, { useState, useEffect, useRef } from 'react';
import { globalSearch } from '@/lib/api';
import { useAuth } from '@/lib/authContext';
import { TenantSwitcher } from './TenantSwitcher';
import { AuthModal } from './AuthModal';
import { OrganizationSettingsModal } from './OrganizationSettingsModal';
import { BillingModal } from './BillingModal';
import { AdminHqModal } from './AdminHqModal';
import { LogIn, LogOut, Settings, CreditCard, ShieldCheck, ChevronDown } from 'lucide-react';


interface SearchResultFacility {
  id: number;
  osm_id: string;
  name: string;
  facility_type: string;
  latitude: number;
  longitude: number;
}

interface SearchResultEvent {
  id: number;
  event_code: string;
  detected_at?: string;
  latitude: number;
  longitude: number;
  confidence?: number;
  frp?: number;
  status?: string;
  satellite?: string;
}

interface HeaderProps {
  onSelectEventId?: (id: number) => void;
  onSelectFacility?: (facility: SearchResultFacility) => void;
  onSearchCoordinates?: (lat: number, lon: number) => void;
  activeModelVersion?: string;
  onOpenNotifications?: () => void;
  onOpenPreferences?: () => void;
  unreadNotificationsCount?: number;
  // Phase 8 & 10 additions
  isLive?: boolean;
  lastUpdateTimestamp?: Date | null;
  autoFlyEnabled?: boolean;
  onToggleAutoFly?: () => void;
  onOpenPipelineModal?: () => void;
  onOpenSihBrief?: () => void;
  onToggleGuidedDemo?: () => void;
  isGuidedDemoActive?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onSelectEventId,
  onSelectFacility,
  onSearchCoordinates,
  activeModelVersion = "xgb-v1",
  onOpenNotifications,
  onOpenPreferences,
  unreadNotificationsCount = 0,
  isLive = true,
  lastUpdateTimestamp,
  autoFlyEnabled = false,
  onToggleAutoFly,
  onOpenPipelineModal,
  onOpenSihBrief,
  onToggleGuidedDemo,
  isGuidedDemoActive = false
}) => {
  const [utcTime, setUtcTime] = useState<string>('');
  const [secondsAgo, setSecondsAgo] = useState<number>(0);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<{ facilities: SearchResultFacility[]; events: SearchResultEvent[]; coordinates?: { latitude: number; longitude: number } | null }>({ facilities: [], events: [] });
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Phase 9 SaaS Auth State
  const { user, isAuthenticated, role, isSuperAdmin, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [showOrgModal, setShowOrgModal] = useState<boolean>(false);
  const [showBillingModal, setShowBillingModal] = useState<boolean>(false);
  const [showAdminModal, setShowAdminModal] = useState<boolean>(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState<boolean>(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // UTC clock & seconds ago counter
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
      if (lastUpdateTimestamp) {
        const diff = Math.max(0, Math.floor((now.getTime() - new Date(lastUpdateTimestamp).getTime()) / 1000));
        setSecondsAgo(diff);
      }
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, [lastUpdateTimestamp]);

  // Search debounce
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults({ facilities: [], events: [] });
      setIsDropdownOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setIsSearching(true);
        const data = await globalSearch(searchQuery.trim());
        setSearchResults({
          facilities: data.facilities || [],
          events: data.events || [],
          coordinates: data.coordinates
        });
        setIsDropdownOpen(true);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setIsSearching(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-14 bg-slate-950/95 border-b border-slate-800/80 px-4 flex items-center justify-between z-40 backdrop-blur-md relative select-none">
      {/* Brand & Mission Control ID */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-gradient-to-tr from-orange-600 to-red-500 flex items-center justify-center shadow-lg shadow-orange-950/50">
            <span className="text-white text-base">🔥</span>
          </div>
          <div>
            <span className="font-mono text-sm tracking-wider font-bold bg-clip-text text-transparent bg-gradient-to-r from-orange-400 via-amber-300 to-red-400">
              INFERNO<span className="text-white">X</span>
            </span>
            <span className="ml-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/90 text-cyan-400 border border-slate-700/60 uppercase">
              Mission Control
            </span>
          </div>
        </div>

        {/* Phase 9 SaaS Multi-Tenant Switcher */}
        <TenantSwitcher onOpenOrgSettings={() => setShowOrgModal(true)} />

        {/* Live Indicator Pill with Data Provenance Transparency (Section 18) */}
        <div 
          className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-[10px] font-mono"
          title={isLive ? "DATA MODE: LIVE | Programmatic API: https://firms.modaps.eosdis.nasa.gov/" : "DATA MODE: DEMO | Historical NASA FIRMS Archive"}
        >
          <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
          <span className="font-bold text-slate-200">{isLive ? 'LIVE' : 'DEMO ARCHIVE'}</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">{secondsAgo}s ago</span>
        </div>

        {/* Live Clock */}
        <div className="hidden xl:flex items-center gap-2 ml-2 pl-3 border-l border-slate-800 text-[11px] font-mono text-slate-400">
          <span>{utcTime || 'SYNCING UTC...'}</span>
        </div>
      </div>

      {/* Global Search Interface */}
      <div ref={searchContainerRef} className="relative w-80 md:w-96">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => { if (searchQuery.trim()) setIsDropdownOpen(true); }}
            placeholder="Search event code, facility, lat/lon..."
            className="w-full bg-slate-900/90 border border-slate-700/70 hover:border-slate-600 focus:border-cyan-500 rounded-md px-3 py-1.5 pl-8 text-xs text-slate-200 placeholder-slate-500 font-mono outline-none transition-all"
          />
          <svg className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          {isSearching && (
            <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin absolute right-2.5 top-2.5" />
          )}
        </div>

        {/* Dropdown Results */}
        {isDropdownOpen && (
          <div className="absolute top-10 left-0 right-0 bg-slate-900/95 border border-slate-700 rounded-lg shadow-2xl overflow-hidden z-50 max-h-80 overflow-y-auto backdrop-blur-xl">
            {searchResults.coordinates && (
              <div 
                onClick={() => {
                  if (onSearchCoordinates && searchResults.coordinates) {
                    onSearchCoordinates(searchResults.coordinates.latitude, searchResults.coordinates.longitude);
                  }
                  setIsDropdownOpen(false);
                }}
                className="px-3 py-2 text-xs font-mono text-cyan-300 hover:bg-slate-800 cursor-pointer border-b border-slate-800 flex items-center justify-between"
              >
                <span>📍 Jump to Coordinates:</span>
                <span className="text-slate-400">{searchResults.coordinates.latitude.toFixed(4)}, {searchResults.coordinates.longitude.toFixed(4)}</span>
              </div>
            )}

            {searchResults.facilities.length > 0 && (
              <div>
                <div className="px-3 py-1 text-[10px] font-mono tracking-wider text-slate-400 uppercase bg-slate-950/60 border-b border-slate-800">
                  Facilities ({searchResults.facilities.length})
                </div>
                {searchResults.facilities.map((fac) => (
                  <div
                    key={fac.id}
                    onClick={() => {
                      if (onSelectFacility) onSelectFacility(fac);
                      setIsDropdownOpen(false);
                    }}
                    className="px-3 py-2 text-xs font-mono hover:bg-slate-800/80 cursor-pointer border-b border-slate-800/50 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-slate-200 font-semibold">{fac.name}</div>
                      <div className="text-[10px] text-slate-400">{fac.facility_type} • {fac.osm_id}</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
                      FACILITY
                    </span>
                  </div>
                ))}
              </div>
            )}

            {searchResults.events.length > 0 && (
              <div>
                <div className="px-3 py-1 text-[10px] font-mono tracking-wider text-slate-400 uppercase bg-slate-950/60 border-b border-slate-800">
                  Thermal Events ({searchResults.events.length})
                </div>
                {searchResults.events.map((ev) => (
                  <div
                    key={ev.id}
                    onClick={() => {
                      if (onSelectEventId) onSelectEventId(ev.id);
                      setIsDropdownOpen(false);
                    }}
                    className="px-3 py-2 text-xs font-mono hover:bg-slate-800/80 cursor-pointer border-b border-slate-800/50 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-amber-300 font-semibold">{ev.event_code || `#INF-2026-${ev.id}`}</div>
                      <div className="text-[10px] text-slate-400">{ev.satellite} • FRP: {ev.frp ? Math.round(ev.frp) : 'N/A'} MW</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-950 text-orange-400 border border-orange-800">
                      {ev.status || 'NEW'}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {searchResults.facilities.length === 0 && searchResults.events.length === 0 && !searchResults.coordinates && !isSearching && (
              <div className="px-3 py-4 text-center text-xs font-mono text-slate-500">
                No matching facilities or thermal events found.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Telemetry Status & User Role */}
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 text-[10px] font-mono">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            <span className="text-slate-500">MODEL:</span>
            <span className="text-indigo-400 font-semibold">{activeModelVersion}</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            <span className="text-slate-500">SATELLITE:</span>
            <span className="text-cyan-400 font-semibold">S2 MSI</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            <span className="text-slate-500">COVER:</span>
            <span className="text-emerald-400 font-semibold">WorldCover 10m</span>
          </div>
        </div>

        {/* Alerts & Notifications Actions */}
        <div className="flex items-center gap-1.5">
          {/* SIH Defense Brief Button (Section 27) */}
          {onOpenSihBrief && (
            <button
              onClick={onOpenSihBrief}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-gradient-to-r from-orange-950/80 to-amber-950/80 border border-orange-600/70 hover:border-orange-500 text-orange-300 hover:text-white text-[10px] font-mono transition-all shadow-sm cursor-pointer"
              title="Open SIH Judge Defense & Problem Solution Brief"
            >
              <span>🔥</span>
              <span className="font-bold">SIH BRIEF</span>
            </button>
          )}

          {/* SIH 18-Step Guided Demo Button (Section 17 & 30) */}
          {onToggleGuidedDemo && (
            <button
              onClick={onToggleGuidedDemo}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-mono border transition-all cursor-pointer ${
                isGuidedDemoActive
                  ? 'bg-amber-400 text-slate-950 font-bold border-amber-300 shadow-md shadow-amber-400/30'
                  : 'bg-slate-900 border-slate-800 text-amber-300 hover:bg-slate-800 hover:border-amber-600/60'
              }`}
              title="Toggle 18-Step Autonomous SIH Guided Demo Walkthrough"
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isGuidedDemoActive ? 'bg-slate-950' : 'bg-amber-400 animate-ping'}`}></span>
              <span>18-STEP DEMO</span>
            </button>
          )}

          {/* Auto-Fly Toggle Button */}
          <button
            onClick={onToggleAutoFly}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-mono border transition-all ${
              autoFlyEnabled
                ? 'bg-amber-950/80 text-amber-300 border-amber-600/70 shadow-sm shadow-amber-950/50'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
            title="Auto-Fly Camera to Critical Anomaly Detections (Cesium)"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${autoFlyEnabled ? 'bg-amber-400 animate-ping' : 'bg-slate-500'}`}></span>
            <span>AUTO-FLY</span>
            <span className={`font-bold ${autoFlyEnabled ? 'text-amber-400' : 'text-slate-500'}`}>
              {autoFlyEnabled ? 'ON' : 'OFF'}
            </span>
          </button>

          {/* NOC Telemetry & Ingestion Monitor */}
          <button
            onClick={onOpenPipelineModal}
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-slate-900 border border-slate-800 hover:border-orange-500/50 text-slate-300 hover:text-orange-400 text-[10px] font-mono transition-all"
            title="Open Autonomous Pipeline NOC & Telemetry"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
            <span>NOC TELEMETRY</span>
          </button>

          {/* Bell Icon with Badge */}
          <button
            onClick={onOpenNotifications}
            className="relative p-1.5 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Open In-App Notifications"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            {unreadNotificationsCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white font-bold text-[9px] flex items-center justify-center border border-slate-950 animate-pulse">
                {unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount}
              </span>
            )}
          </button>

          {/* Preferences Icon */}
          <button
            onClick={onOpenPreferences}
            className="p-1.5 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Alert & Notification Preferences"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>

        {/* User Pill & SaaS Auth Menu */}
        {isAuthenticated && user ? (
          <div ref={userMenuRef} className="relative">
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer"
            >
              <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-amber-500 to-rose-600 text-slate-950 font-bold text-[10px] flex items-center justify-center shadow-sm">
                {user.full_name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-[11px] font-semibold text-slate-200 leading-none truncate max-w-[100px]">
                  {user.full_name?.split(' ')[0] || user.email}
                </div>
                <div className="text-[9px] text-amber-400 font-mono leading-none mt-0.5 uppercase">
                  {role?.replace('_', ' ') || 'ANALYST'}
                </div>
              </div>
              <ChevronDown size={13} className="text-slate-400" />
            </button>

            {userDropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl z-50 overflow-hidden backdrop-blur-md divide-y divide-slate-800/80">
                <div className="px-3.5 py-2.5 bg-slate-950/40">
                  <p className="text-xs font-semibold text-white truncate">{user.full_name}</p>
                  <p className="text-[11px] text-slate-400 font-mono truncate">{user.email}</p>
                </div>

                <div className="p-1 text-xs">
                  <button
                    onClick={() => { setUserDropdownOpen(false); setShowOrgModal(true); }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-left cursor-pointer"
                  >
                    <Settings size={14} className="text-amber-400" />
                    <span>Workspace Settings</span>
                  </button>

                  <button
                    onClick={() => { setUserDropdownOpen(false); setShowBillingModal(true); }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-left cursor-pointer"
                  >
                    <CreditCard size={14} className="text-emerald-400" />
                    <span>Billing & Resource Limits</span>
                  </button>

                  {isSuperAdmin && (
                    <button
                      onClick={() => { setUserDropdownOpen(false); setShowAdminModal(true); }}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-purple-300 hover:text-purple-200 hover:bg-purple-950/30 transition-colors text-left font-medium cursor-pointer"
                    >
                      <ShieldCheck size={14} className="text-purple-400" />
                      <span>Platform Admin HQ</span>
                    </button>
                  )}
                </div>

                <div className="p-1 text-xs">
                  <button
                    onClick={() => { setUserDropdownOpen(false); logout(); }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 transition-colors text-left cursor-pointer"
                  >
                    <LogOut size={14} />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setShowAuthModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs shadow-md shadow-amber-500/20 transition-all cursor-pointer"
          >
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
        )}
      </div>

      {/* Phase 9 SaaS Modals */}
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      <OrganizationSettingsModal
        isOpen={showOrgModal}
        onClose={() => setShowOrgModal(false)}
        onOpenBilling={() => setShowBillingModal(true)}
      />
      <BillingModal isOpen={showBillingModal} onClose={() => setShowBillingModal(false)} />
      <AdminHqModal isOpen={showAdminModal} onClose={() => setShowAdminModal(false)} />
    </header>
  );
};
