"use client";

import React from 'react';

interface FacilityContextCardProps {
  facility?: {
    id?: number;
    osm_id?: string;
    name?: string;
    facility_type?: string;
    operator?: string;
    distance_meters?: number;
    latitude?: number;
    longitude?: number;
  } | null;
  distanceMeters?: number;
  nearbyCount?: number;
  onInspectFacility?: (facilityId: number) => void;
}

export const FacilityContextCard: React.FC<FacilityContextCardProps> = ({
  facility,
  distanceMeters,
  nearbyCount = 0,
  onInspectFacility
}) => {
  const dist = distanceMeters ?? facility?.distance_meters;

  return (
    <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 space-y-2.5 font-mono text-xs">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 uppercase text-[10px] tracking-wider">
          NEARBY INFRASTRUCTURE
        </span>
        {nearbyCount > 0 && (
          <span className="text-[10px] text-slate-500">
            {nearbyCount} within 5km
          </span>
        )}
      </div>

      {facility ? (
        <div className="space-y-2 pt-1 border-t border-slate-800/60">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm font-semibold text-sky-300">
                {facility.name || 'Industrial Facility'}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">
                Type: <span className="text-slate-300 font-medium">{facility.facility_type || 'industrial'}</span>
                {facility.operator && ` • ${facility.operator}`}
              </div>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] bg-sky-950 text-sky-400 border border-sky-800 uppercase font-semibold">
              OSM
            </span>
          </div>

          <div className="flex items-center justify-between pt-1 text-[11px]">
            <div>
              <span className="text-slate-500 uppercase text-[9px] block">Spatial Distance</span>
              <span className="text-amber-300 font-bold text-sm">
                {dist !== undefined ? `${dist.toLocaleString()} m` : 'Adjacent'}
              </span>
            </div>

            {facility.id && onInspectFacility && (
              <button
                onClick={() => onInspectFacility(facility.id!)}
                className="px-2.5 py-1 rounded bg-sky-950/80 hover:bg-sky-900 text-sky-300 hover:text-white border border-sky-700/60 text-xs font-semibold transition-all flex items-center gap-1"
              >
                <span>🏭 Inspect Facility</span>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="text-[11px] text-slate-500 py-1">
          No industrial infrastructure identified within 5.0 km radius.
        </div>
      )}
    </div>
  );
};
