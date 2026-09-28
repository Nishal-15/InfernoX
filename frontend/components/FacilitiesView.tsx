"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { getFacilitiesGeoJson } from '@/lib/api';

interface FacilityFeature {
  id?: number | string;
  properties: {
    id?: number;
    name?: string;
    facility_type?: string;
    operator?: string;
    hazard_class?: string;
    risk_score?: number;
    latitude?: number;
    longitude?: number;
    capacity_mw?: number;
    state?: string;
    [key: string]: unknown;
  };
  geometry: {
    coordinates: number[];
  };
}

interface FacilitiesViewProps {
  onSelectFacility: (facilityId: number) => void;
  onFlyToFacility: (lon: number, lat: number) => void;
  onGenerateReport: (facilityId: number) => void;
}

export const FacilitiesView: React.FC<FacilitiesViewProps> = ({
  onSelectFacility,
  onFlyToFacility,
  onGenerateReport
}) => {
  const [facilities, setFacilities] = useState<FacilityFeature[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');

  useEffect(() => {
    const fetchFacilities = async () => {
      try {
        setLoading(true);
        const geojson = await getFacilitiesGeoJson();
        if (geojson && geojson.features) {
          setFacilities(geojson.features);
        }
      } catch (err) {
        console.error("Failed to load facilities:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchFacilities();
  }, []);

  const filteredFacilities = useMemo(() => {
    return facilities.filter(f => {
      const p = f.properties || {};
      const name = (p.name || '').toLowerCase();
      const operator = (p.operator || '').toLowerCase();
      const facType = (p.facility_type || '').toUpperCase();
      const query = searchQuery.toLowerCase();

      const matchesSearch = !query || name.includes(query) || operator.includes(query);
      const matchesType = typeFilter === 'ALL' || facType.includes(typeFilter);

      return matchesSearch && matchesType;
    });
  }, [facilities, searchQuery, typeFilter]);

  const getFacilityTypeBadge = (type?: string) => {
    const t = (type || 'INDUSTRIAL').toUpperCase();
    if (t.includes('REFINERY')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-400 border border-amber-800">
          OIL REFINERY
        </span>
      );
    }
    if (t.includes('POWER')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-950/80 text-blue-400 border border-blue-800">
          POWER STATION
        </span>
      );
    }
    if (t.includes('STEEL')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950/80 text-purple-400 border border-purple-800">
          STEEL COMPLEX
        </span>
      );
    }
    if (t.includes('PETRO') || t.includes('LNG') || t.includes('CHEMICAL')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800">
          PETROCHEMICAL / LNG
        </span>
      );
    }
    if (t.includes('MINING') || t.includes('COAL')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-950/80 text-orange-400 border border-orange-800">
          MINING SECTOR
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
        {type || 'INDUSTRIAL'}
      </span>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden font-mono">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-900/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-slate-100 tracking-wide">STRATEGIC INDUSTRIAL INFRASTRUCTURE</h1>
            <span className="px-2 py-0.5 text-[11px] rounded bg-sky-950 text-sky-400 border border-sky-800">
              {facilities.length} Monitored Assets
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Geospatial reference registry cross-referencing OpenStreetMap industrial footprints with high-resolution satellite imagery
          </p>
        </div>
      </div>

      {/* Filter Ribbon */}
      <div className="px-6 py-3 bg-slate-900/40 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search facility name, operator..."
              className="w-72 bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1.5 text-xs text-slate-400 hover:text-white"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Asset Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ALL">All Asset Types</option>
              <option value="REFINERY">Refineries</option>
              <option value="POWER">Power Stations</option>
              <option value="STEEL">Steel Plants</option>
              <option value="PETRO">Petrochemical / LNG</option>
              <option value="MINING">Mining & Minerals</option>
            </select>
          </div>
        </div>
      </div>

      {/* Grid Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs">Loading verified industrial assets...</p>
          </div>
        ) : filteredFacilities.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center gap-2 text-slate-500 bg-slate-900/30 border border-slate-800 rounded-xl p-8">
            <p className="text-sm font-semibold text-slate-400">No facilities match your search criteria</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredFacilities.map((f, idx) => {
              const p = f.properties || {};
              const facId = p.id || idx + 1;
              const coords = f.geometry?.coordinates || [0, 0];
              const lon = coords[0];
              const lat = coords[1];

              return (
                <div
                  key={facId}
                  className="bg-slate-900/70 border border-slate-800 hover:border-cyan-500/60 rounded-xl p-5 transition-all shadow-lg hover:shadow-cyan-950/20 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider">
                          FAC-IN-{facId.toString().padStart(4, '0')}
                        </span>
                        <h3 className="text-sm font-bold text-slate-100 mt-0.5 line-clamp-1">
                          {p.name || 'Industrial Facility'}
                        </h3>
                      </div>
                      {getFacilityTypeBadge(p.facility_type)}
                    </div>

                    <div className="mt-4 space-y-2 text-xs">
                      <div className="flex justify-between py-1 border-b border-slate-800/80">
                        <span className="text-slate-500">OPERATOR:</span>
                        <span className="text-slate-300 font-semibold truncate max-w-[180px]">
                          {p.operator || 'National Authority / PSU'}
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-800/80">
                        <span className="text-slate-500">COORDINATES:</span>
                        <span className="text-slate-400 text-[11px]">
                          {lat.toFixed(4)}°N, {lon.toFixed(4)}°E
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-800/80">
                        <span className="text-slate-500">HAZARD TIER:</span>
                        <span className="text-amber-400 font-semibold">
                          {p.hazard_class || 'TIER-1 HIGH HAZARD'}
                        </span>
                      </div>
                      <div className="flex justify-between py-1">
                        <span className="text-slate-500">PERSISTENCE BASELINE:</span>
                        <span className="text-emerald-400 font-semibold">
                          MONITORED ACTIVE
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                    <button
                      onClick={() => onFlyToFacility(lon, lat)}
                      className="flex-1 py-1.5 px-3 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-xs font-semibold transition flex items-center justify-center gap-1.5"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      Fly To
                    </button>
                    <button
                      onClick={() => onSelectFacility(Number(facId))}
                      className="py-1.5 px-3 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition"
                    >
                      Inspect
                    </button>
                    <button
                      onClick={() => onGenerateReport(Number(facId))}
                      className="py-1.5 px-2.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs transition"
                      title="Generate Facility Dossier"
                    >
                      Dossier
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
