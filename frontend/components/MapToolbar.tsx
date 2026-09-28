"use client";

import React, { useState } from 'react';

interface LayerStates {
  showFirms: boolean;
  showFacilities: boolean;
  showHistorical: boolean;
  showSatellite: boolean;
  showNdvi: boolean;
  showNbr: boolean;
  showLandCover: boolean;
  showTerrain: boolean;
  showHeatmap: boolean;
}

interface MapToolbarProps {
  layers: LayerStates;
  onToggleLayer: (layerName: keyof LayerStates) => void;
  is2D: boolean;
  onToggle2D: (enable2D: boolean) => void;
  onResetView: () => void;
  onInvestigateCurrent?: () => void;
  hasSelectedEvent?: boolean;
  followEvent?: boolean;
  onToggleFollowEvent?: (follow: boolean) => void;
  onFlyToPreset?: (lon: number, lat: number, height: number) => void;
}

const REGION_PRESETS = [
  { name: 'India (National Overview)', lon: 78.9629, lat: 20.5937, height: 3500000 },
  { name: 'Gujarat Petrochemical (Jamnagar)', lon: 70.0712, lat: 22.4632, height: 45000 },
  { name: 'Mumbai Industrial Corridor (BPCL)', lon: 72.8540, lat: 19.0125, height: 35000 },
  { name: 'Korba Super Thermal Power Hub', lon: 82.6844, lat: 22.3595, height: 40000 },
  { name: 'IOCL Paradip Refinery & Port', lon: 86.6085, lat: 20.2644, height: 45000 },
  { name: 'Tata Steel Kalinganagar Complex', lon: 85.9622, lat: 20.9521, height: 35000 },
  { name: 'Jharia Coalfield Mining Complex', lon: 86.4167, lat: 23.7441, height: 35000 },
  { name: 'Ramagundam STPS (Telangana)', lon: 79.4312, lat: 18.7562, height: 40000 },
  { name: 'Hazira LNG & Petrochemicals', lon: 72.6481, lat: 21.1125, height: 40000 },
  { name: 'HPCL Visakhapatnam Refinery', lon: 83.2185, lat: 17.6868, height: 38000 }
];

export const MapToolbar: React.FC<MapToolbarProps> = ({
  layers,
  onToggleLayer,
  is2D,
  onToggle2D,
  onResetView,
  onInvestigateCurrent,
  hasSelectedEvent = false,
  followEvent = false,
  onToggleFollowEvent,
  onFlyToPreset
}) => {
  const [layersMenuOpen, setLayersMenuOpen] = useState(false);
  const [presetsMenuOpen, setPresetsMenuOpen] = useState(false);

  return (
    <div className="absolute top-4 left-4 z-20 flex items-center gap-2 font-mono select-none">
      {/* 2D / 3D Switcher */}
      <div className="bg-slate-950/85 backdrop-blur-md p-1 rounded-lg border border-slate-800 shadow-xl flex items-center gap-1">
        <button
          onClick={() => onToggle2D(false)}
          className={`px-2.5 py-1 text-xs rounded transition-all ${
            !is2D
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="3D Globe View"
        >
          🌐 3D Globe
        </button>
        <button
          onClick={() => onToggle2D(true)}
          className={`px-2.5 py-1 text-xs rounded transition-all ${
            is2D
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="2D Map View"
        >
          🗺️ 2D Map
        </button>
      </div>

      {/* Camera Reset */}
      <button
        onClick={onResetView}
        className="bg-slate-950/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white hover:border-slate-700 shadow-xl transition-all flex items-center gap-1.5"
        title="Reset Camera to Global View"
      >
        <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span>Reset View</span>
      </button>

      {/* Region Presets Dropdown (Section 32) */}
      <div className="relative">
        <button
          onClick={() => { setPresetsMenuOpen(!presetsMenuOpen); setLayersMenuOpen(false); }}
          className={`backdrop-blur-md px-2.5 py-1.5 rounded-lg border text-xs shadow-xl transition-all flex items-center gap-1.5 ${
            presetsMenuOpen
              ? 'bg-slate-800 text-cyan-300 border-cyan-500/50'
              : 'bg-slate-950/85 border-slate-800 text-slate-300 hover:text-white hover:border-slate-700'
          }`}
          title="Fly to Major Industrial Corridors & Regions"
        >
          <span>📍 Regions</span>
          <svg className={`w-3 h-3 text-slate-400 transition-transform ${presetsMenuOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {presetsMenuOpen && (
          <div className="absolute top-10 left-0 w-64 bg-slate-950/95 border border-slate-800 rounded-xl shadow-2xl p-2 z-30 backdrop-blur-xl animate-in fade-in slide-in-from-top-2 duration-150">
            <div className="px-2 py-1 text-[10px] text-slate-500 font-bold uppercase tracking-wider border-b border-slate-800/80 mb-1">
              STRATEGIC INDUSTRIAL REGIONS
            </div>
            <div className="space-y-0.5 max-h-64 overflow-y-auto">
              {REGION_PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (onFlyToPreset) {
                      onFlyToPreset(preset.lon, preset.lat, preset.height);
                    }
                    setPresetsMenuOpen(false);
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] text-slate-300 hover:text-cyan-300 hover:bg-slate-900/90 transition flex items-center justify-between"
                >
                  <span className="truncate">{preset.name}</span>
                  <span className="text-[9px] text-slate-500">FLY</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Investigate Current Event */}
      {hasSelectedEvent && onInvestigateCurrent && (
        <button
          onClick={onInvestigateCurrent}
          className="bg-gradient-to-r from-red-600 to-orange-500 hover:from-red-500 hover:to-orange-400 text-white font-semibold px-3 py-1.5 rounded-lg shadow-xl shadow-red-950/40 text-xs flex items-center gap-1.5 animate-pulse"
          title="Fly to and Focus Selected Event"
        >
          <span>🎯 Investigate</span>
        </button>
      )}

      {/* Follow Event Toggle */}
      {hasSelectedEvent && onToggleFollowEvent && (
        <button
          onClick={() => onToggleFollowEvent(!followEvent)}
          className={`backdrop-blur-md px-2.5 py-1.5 rounded-lg border text-xs shadow-xl transition-all flex items-center gap-1.5 ${
            followEvent
              ? 'bg-amber-950/80 border-amber-600 text-amber-300 font-semibold'
              : 'bg-slate-950/85 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
          title="Track and lock camera on current event"
        >
          <span>{followEvent ? '🔒 Tracking' : '🔓 Follow Event'}</span>
        </button>
      )}

      {/* Layers Menu Trigger */}
      <div className="relative">
        <button
          onClick={() => setLayersMenuOpen(!layersMenuOpen)}
          className={`backdrop-blur-md px-3 py-1.5 rounded-lg border text-xs shadow-xl transition-all flex items-center gap-1.5 ${
            layersMenuOpen
              ? 'bg-slate-800 text-cyan-300 border-cyan-500/50'
              : 'bg-slate-950/85 border-slate-800 text-slate-300 hover:text-white hover:border-slate-700'
          }`}
        >
          <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span>Layers</span>
          <svg className={`w-3 h-3 transition-transform ${layersMenuOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Layers Dropdown */}
        {layersMenuOpen && (
          <div className="absolute top-10 left-0 w-60 bg-slate-950/95 border border-slate-800 rounded-lg shadow-2xl p-2.5 backdrop-blur-xl z-30 space-y-1.5">
            <div className="text-[10px] font-mono tracking-wider text-slate-500 uppercase px-1 pb-1 border-b border-slate-900">
              Intelligence Layers
            </div>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-red-400">🔥</span> FIRMS Thermal
              </span>
              <input
                type="checkbox"
                checked={layers.showFirms}
                onChange={() => onToggleLayer('showFirms')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-sky-400">🏭</span> Infrastructure (OSM)
              </span>
              <input
                type="checkbox"
                checked={layers.showFacilities}
                onChange={() => onToggleLayer('showFacilities')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-amber-400">⏱️</span> Historical Detections
              </span>
              <input
                type="checkbox"
                checked={layers.showHistorical}
                onChange={() => onToggleLayer('showHistorical')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <div className="text-[10px] font-mono tracking-wider text-slate-500 uppercase px-1 pt-1.5 pb-0.5 border-t border-slate-900">
              Remote Sensing Overlays
            </div>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-cyan-400">🛰️</span> Sentinel-2 True Color
              </span>
              <input
                type="checkbox"
                checked={layers.showSatellite}
                onChange={() => onToggleLayer('showSatellite')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-emerald-400">🌿</span> NDVI (Vegetation)
              </span>
              <input
                type="checkbox"
                checked={layers.showNdvi}
                onChange={() => onToggleLayer('showNdvi')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-purple-400">📉</span> NBR (Burn Scar)
              </span>
              <input
                type="checkbox"
                checked={layers.showNbr}
                onChange={() => onToggleLayer('showNbr')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-lime-400">🗺️</span> ESA WorldCover
              </span>
              <input
                type="checkbox"
                checked={layers.showLandCover}
                onChange={() => onToggleLayer('showLandCover')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>

            <div className="text-[10px] font-mono tracking-wider text-slate-500 uppercase px-1 pt-1.5 pb-0.5 border-t border-slate-900">
              Analytical Spatial Overlays
            </div>

            <label className="flex items-center justify-between px-2 py-1 rounded hover:bg-slate-900/60 cursor-pointer text-xs">
              <span className="flex items-center gap-2 text-slate-200">
                <span className="text-orange-500">📊</span> Heatmap Density Grid
              </span>
              <input
                type="checkbox"
                checked={layers.showHeatmap}
                onChange={() => onToggleLayer('showHeatmap')}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 bg-slate-800"
              />
            </label>
          </div>
        )}
      </div>
    </div>
  );
};
