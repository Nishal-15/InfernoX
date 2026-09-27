"use client";

import React from 'react';

interface SatelliteCardProps {
  sceneId?: string;
  acquisitionTime?: string;
  cloudPercentage?: number;
  evidenceStatus?: string;
  provider?: string;
  processingLevel?: string;
  indices?: {
    ndvi?: number | null;
    nbr?: number | null;
    ndwi?: number | null;
    swir_nir_ratio?: number | null;
    burn_scar_indicator?: boolean;
  };
  onToggleLayer?: (layer: 'showSatellite' | 'showNdvi' | 'showNbr') => void;
  layers?: {
    showSatellite?: boolean;
    showNdvi?: boolean;
    showNbr?: boolean;
  };
}

export const SatelliteCard: React.FC<SatelliteCardProps> = ({
  sceneId,
  acquisitionTime,
  cloudPercentage,
  evidenceStatus = 'AVAILABLE',
  provider = 'Copernicus Sentinel-2 MSI',
  processingLevel = 'Level-2A BOA',
  indices,
  onToggleLayer,
  layers
}) => {
  const isAvailable = evidenceStatus === 'AVAILABLE';
  const isCloudRejected = evidenceStatus === 'REJECTED_CLOUD' || (cloudPercentage !== undefined && cloudPercentage > 30.0);

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-2.5 font-mono text-xs">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 uppercase text-[10px] tracking-wider">
          SATELLITE EVIDENCE
        </span>
        <span className={`px-2 py-0.5 rounded text-[10px] border uppercase font-semibold ${
          isAvailable 
            ? 'bg-emerald-950 text-emerald-400 border-emerald-800' 
            : isCloudRejected 
              ? 'bg-amber-950 text-amber-400 border-amber-800' 
              : 'bg-slate-800 text-slate-400 border-slate-700'
        }`}>
          {isAvailable ? 'AVAILABLE' : isCloudRejected ? 'CLOUD REJECTED' : 'UNAVAILABLE'}
        </span>
      </div>

      <div className="flex justify-between items-center text-[10px] text-slate-500">
        <span>{provider}</span>
        <span className="font-semibold text-slate-400">{processingLevel}</span>
      </div>

      {isAvailable ? (
        <div className="space-y-2 pt-1 border-t border-slate-800/60">
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <div className="text-[9px] text-slate-500 uppercase">Acquisition</div>
              <div className="text-slate-200 font-semibold">{formatDate(acquisitionTime)}</div>
            </div>
            <div>
              <div className="text-[9px] text-slate-500 uppercase">Cloud Coverage</div>
              <div className="text-cyan-300 font-semibold">
                {cloudPercentage !== undefined ? `${cloudPercentage.toFixed(1)}%` : '0.0%'}
              </div>
            </div>
          </div>

          {sceneId && (
            <div className="text-[10px] text-slate-500 truncate">
              Scene: <span className="text-slate-300">{sceneId}</span>
            </div>
          )}

          {/* Spectral Indices Badges */}
          {indices && (
            <div className="grid grid-cols-3 gap-1.5 pt-1 border-t border-slate-800/40 text-center">
              <div className="p-1 rounded bg-slate-950/70 border border-slate-800/80">
                <div className="text-[8px] text-slate-500 uppercase">NDVI</div>
                <div className="text-[11px] font-bold text-emerald-400">
                  {indices.ndvi !== null && indices.ndvi !== undefined ? indices.ndvi.toFixed(2) : 'N/A'}
                </div>
              </div>
              <div className="p-1 rounded bg-slate-950/70 border border-slate-800/80">
                <div className="text-[8px] text-slate-500 uppercase">NBR</div>
                <div className="text-[11px] font-bold text-purple-400">
                  {indices.nbr !== null && indices.nbr !== undefined ? indices.nbr.toFixed(2) : 'N/A'}
                </div>
              </div>
              <div className="p-1 rounded bg-slate-950/70 border border-slate-800/80">
                <div className="text-[8px] text-slate-500 uppercase">SWIR/NIR</div>
                <div className="text-[11px] font-bold text-amber-400">
                  {indices.swir_nir_ratio !== null && indices.swir_nir_ratio !== undefined ? indices.swir_nir_ratio.toFixed(2) : 'N/A'}
                </div>
              </div>
            </div>
          )}

          {/* Layer View Quick Toggles */}
          {onToggleLayer && (
            <div className="flex gap-1.5 pt-1">
              <button
                onClick={() => onToggleLayer('showSatellite')}
                className={`flex-1 py-1 rounded text-[10px] border transition-all ${
                  layers?.showSatellite
                    ? 'bg-cyan-950 text-cyan-300 border-cyan-700 font-semibold'
                    : 'bg-slate-950 hover:bg-slate-800 text-slate-400 border-slate-800'
                }`}
              >
                RGB Optical
              </button>
              <button
                onClick={() => onToggleLayer('showNdvi')}
                className={`flex-1 py-1 rounded text-[10px] border transition-all ${
                  layers?.showNdvi
                    ? 'bg-emerald-950 text-emerald-300 border-emerald-700 font-semibold'
                    : 'bg-slate-950 hover:bg-slate-800 text-slate-400 border-slate-800'
                }`}
              >
                NDVI Index
              </button>
              <button
                onClick={() => onToggleLayer('showNbr')}
                className={`flex-1 py-1 rounded text-[10px] border transition-all ${
                  layers?.showNbr
                    ? 'bg-purple-950 text-purple-300 border-purple-700 font-semibold'
                    : 'bg-slate-950 hover:bg-slate-800 text-slate-400 border-slate-800'
                }`}
              >
                NBR Burn
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="text-[11px] text-slate-400 py-1.5 space-y-1">
          <div className="text-amber-400 font-medium">
            {isCloudRejected 
              ? `No cloud-free optical scene available (cloud: ${cloudPercentage?.toFixed(0) || '>30'}%).`
              : 'No optical satellite scene within temporal revisit window.'}
          </div>
          <div className="text-[10px] text-slate-500">
            Thermal classification relying on FIRMS infrared signature, OSM spatial infrastructure, and temporal persistence.
          </div>
        </div>
      )}
    </div>
  );
};
