"use client";

import React, { useEffect, useState, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { 
  getEventsGeoJson, 
  getFacilitiesGeoJson, 
  getEventsList, 
  getEventInvestigation,
  getEventTimeline,
  updateEventStatus,
  getCurrentModel,
  getNotifications
} from '@/lib/api';
import { Header } from '@/components/Header';
import { SidebarNav, NavTab } from '@/components/SidebarNav';
import { MapToolbar } from '@/components/MapToolbar';
import { EventPanel, InvestigationData } from '@/components/EventPanel';
import { TemporalTimeline, TimelineDetection } from '@/components/TemporalTimeline';
import { FacilityModal } from '@/components/FacilityModal';
import { EventComparisonModal } from '@/components/EventComparisonModal';
import { AlertCenter } from '@/components/AlertCenter';
import { AnalyticsDashboard } from '@/components/AnalyticsDashboard';
import { ReportBuilder } from '@/components/ReportBuilder';
import { OverviewDashboard } from '@/components/OverviewDashboard';
import { LiveEventsView } from '@/components/LiveEventsView';
import { FacilitiesView } from '@/components/FacilitiesView';
import { IncidentsView } from '@/components/IncidentsView';
import { MonitoringView } from '@/components/MonitoringView';
import { NotificationDrawer } from '@/components/NotificationDrawer';
import { AlertPreferencesModal } from '@/components/AlertPreferencesModal';
import PipelineMonitorModal from '@/components/PipelineMonitorModal';
import { SihDemoController } from '@/components/SihDemoController';
import { SihLandingExplainerModal } from '@/components/SihLandingExplainerModal';
import { useWebSocket, WebSocketEvent } from '@/lib/useWebSocket';
import { CesiumMapRef, ClusterPoint, EventContextPayload } from '@/components/CesiumMap';

interface GeoJsonCollection {
  type: string;
  features: Array<{
    type: string;
    geometry: {
      type: string;
      coordinates: number[];
    };
    properties: Record<string, unknown>;
  }>;
}

interface EventListItem {
  id: number;
  priority_level?: string;
  classification?: string;
  frp?: number;
  confidence?: number;
  detected_at?: string;
  latitude?: number;
  longitude?: number;
  satellite?: string;
  status?: string;
}

const CesiumMap = dynamic(() => import('@/components/CesiumMap'), { ssr: false });

export default function MissionControlPage() {
  // Navigation & Workspace State
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [activeModelVersion, setActiveModelVersion] = useState<string>('xgb-v1');
  const [showSihBrief, setShowSihBrief] = useState<boolean>(false);
  const [showGuidedDemo, setShowGuidedDemo] = useState<boolean>(false);

  // Layer States
  const [layers, setLayers] = useState({
    showFirms: true,
    showFacilities: true,
    showHistorical: false,
    showSatellite: false,
    showNdvi: false,
    showNbr: false,
    showLandCover: false,
    showTerrain: true,
    showHeatmap: false
  });

  // Report Target State for cross-tab linking
  const [reportInitialTarget, setReportInitialTarget] = useState<{
    type: 'INCIDENT' | 'FACILITY' | 'REGIONAL' | 'EXECUTIVE';
    id?: string;
  }>({ type: 'EXECUTIVE' });

  // Map Controls State
  const [is2D, setIs2D] = useState(false);
  const [followEvent, setFollowEvent] = useState(false);
  const cesiumRef = useRef<CesiumMapRef>(null);

  // Core Data State
  const [eventsGeoJson, setEventsGeoJson] = useState<GeoJsonCollection>({ type: "FeatureCollection", features: [] });
  const [facilitiesGeoJson, setFacilitiesGeoJson] = useState<GeoJsonCollection>({ type: "FeatureCollection", features: [] });
  const [eventsList, setEventsList] = useState<EventListItem[]>([]);

  // Selected Event & Investigation State
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [investigationData, setInvestigationData] = useState<InvestigationData | null>(null);
  const [loadingInvestigation, setLoadingInvestigation] = useState(false);

  // Cluster Timeline & Playback State
  const [clusterTimeline, setClusterTimeline] = useState<TimelineDetection[]>([]);
  const [timelineIndex, setTimelineIndex] = useState<number>(0);
  const [isPlayingHistory, setIsPlayingHistory] = useState<boolean>(false);

  // Modals State
  const [modalFacilityId, setModalFacilityId] = useState<number | null>(null);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isPreferencesOpen, setIsPreferencesOpen] = useState(false);
  const [unreadNotificationsCount, setUnreadNotificationsCount] = useState(0);

  // Phase 8 Autonomous Monitoring State
  const [autoFlyEnabled, setAutoFlyEnabled] = useState<boolean>(false);
  const [isPipelineModalOpen, setIsPipelineModalOpen] = useState<boolean>(false);
  const [incomingToastAlert, setIncomingToastAlert] = useState<{
    eventId: number;
    frp: number;
    risk: number;
    lat?: number;
    lon?: number;
    title: string;
    severity: string;
  } | null>(null);

  // WebSocket Event Handler
  const handleWebSocketEvent = useCallback((msg: WebSocketEvent) => {
    const payload = msg.payload as Record<string, unknown>;

    if (msg.event === 'thermal_event.created' || msg.event === 'thermal_event.updated') {
      const ev = (payload.event || payload) as EventListItem;
      if (!ev || !ev.id) return;

      // Update event list
      setEventsList(prev => {
        const idx = prev.findIndex(item => item.id === ev.id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = { ...updated[idx], ...ev };
          return updated;
        }
        return [ev, ...prev];
      });

      // Update GeoJSON layer
      if (ev.latitude && ev.longitude) {
        setEventsGeoJson(prev => {
          const filtered = prev.features.filter(f => (f.properties as { id?: number })?.id !== ev.id);
          const newFeature = {
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [ev.longitude!, ev.latitude!]
            },
            properties: {
              id: ev.id,
              frp: ev.frp,
              confidence: ev.confidence,
              detected_at: ev.detected_at,
              satellite: ev.satellite,
              priority_level: ev.priority_level,
              classification: ev.classification,
              status: ev.status || 'NEW'
            }
          };
          return {
            ...prev,
            features: [newFeature, ...filtered]
          };
        });
      }
    }

    if (msg.event === 'alert.created' || msg.event === 'risk.updated') {
      const alert = (payload.alert || payload) as Record<string, unknown>;
      const risk = Number(payload.risk_score ?? alert.risk_score ?? 75);
      const frp = Number(payload.frp ?? alert.frp ?? 150);
      const lat = (payload.latitude ?? alert.latitude) as number | undefined;
      const lon = (payload.longitude ?? alert.longitude) as number | undefined;
      const eventId = (payload.event_id ?? alert.event_id) as number | undefined;

      if (eventId) {
        setIncomingToastAlert({
          eventId,
          frp: Math.round(frp),
          risk: Math.round(risk),
          lat,
          lon,
          title: String(alert.title || 'NEW HIGH-RISK THERMAL EVENT'),
          severity: String(alert.severity || (risk >= 80 ? 'CRITICAL' : 'HIGH'))
        });

        // Trigger Auto-Fly if enabled and coordinates exist
        if (autoFlyEnabled && lat && lon) {
          cesiumRef.current?.flyTo(lon, lat, 4000);
        }
      }

      setUnreadNotificationsCount(prev => prev + 1);
    }
  }, [autoFlyEnabled]);


  const { isConnected, lastUpdateTimestamp } = useWebSocket({
    onEvent: handleWebSocketEvent
  });

  // Auto-dismiss toast alert after 14 seconds
  useEffect(() => {
    if (incomingToastAlert) {
      const t = setTimeout(() => setIncomingToastAlert(null), 14000);
      return () => clearTimeout(t);
    }
  }, [incomingToastAlert]);


  // 1. Initial Data Ingestion & Model Sync
  useEffect(() => {
    const initData = async () => {
      try {
        const [evGeo, facGeo, evList, modelRes, notifRes] = await Promise.all([
          getEventsGeoJson({ limit: 1000 }),
          getFacilitiesGeoJson({ limit: 500 }),
          getEventsList({ limit: 100 }),
          getCurrentModel().catch(() => null),
          getNotifications({ unread_only: true, limit: 10 }).catch(() => ({ items: [], total: 0 }))
        ]);

        setEventsGeoJson(evGeo);
        setFacilitiesGeoJson(facGeo);
        setEventsList(evList.items || []);
        if (modelRes?.model_version) {
          setActiveModelVersion(modelRes.model_version);
        }
        if (notifRes) {
          setUnreadNotificationsCount(Array.isArray(notifRes) ? notifRes.length : (notifRes.total ?? (notifRes.items ? notifRes.items.length : 0)));
        }
      } catch (err) {
        console.error('Failed to initialize mission control data:', err);
      }
    };

    initData();
  }, []);

  // 2. Load Investigation Dossier when an Event is Selected
  const selectAndLoadEvent = useCallback(async (eventId: number, autoFly = false) => {
    setSelectedEventId(eventId);
    setLoadingInvestigation(true);
    setIsPlayingHistory(false);

    try {
      const [inv, timeRes] = await Promise.all([
        getEventInvestigation(eventId),
        getEventTimeline(eventId).catch(() => ({ timeline: [] }))
      ]);

      setInvestigationData(inv);
      const timelineNodes: TimelineDetection[] = timeRes.timeline || [];
      setClusterTimeline(timelineNodes);

      // Find index of current event in timeline
      const curIdx = timelineNodes.findIndex(t => t.id === eventId);
      setTimelineIndex(curIdx >= 0 ? curIdx : timelineNodes.length - 1);

      if (autoFly && inv.event) {
        cesiumRef.current?.investigate(inv.event.longitude, inv.event.latitude);
      }
    } catch (err) {
      console.error(`Failed to load investigation for event ${eventId}:`, err);
    } finally {
      setLoadingInvestigation(false);
    }
  }, []);

  // 3. Handle Investigation Mode Button Click
  const handleInvestigateClick = async () => {
    if (!investigationData?.event) return;
    const { longitude, latitude, id, status } = investigationData.event;

    // Trigger Cesium multi-stage flight
    cesiumRef.current?.investigate(longitude, latitude);

    // Transition status to INVESTIGATING if currently NEW
    if (status === 'NEW') {
      try {
        await updateEventStatus(id, 'INVESTIGATING', 'AI 3D investigation flight initiated by analyst');
        setInvestigationData(prev => prev ? {
          ...prev,
          event: { ...prev.event, status: 'INVESTIGATING' }
        } : null);
      } catch (err) {
        console.error('Failed to update event status:', err);
      }
    }
  };

  // 4. Handle Timeline Point Selection
  const handleSelectTimelineIndex = (idx: number) => {
    setTimelineIndex(idx);
    const target = clusterTimeline[idx];
    if (target) {
      // Re-center camera gently on selected historical detection
      cesiumRef.current?.flyTo(target.longitude, target.latitude, 3500);
    }
  };

  // 5. Handle Layer Toggles
  const handleToggleLayer = (layerName: keyof typeof layers) => {
    setLayers(prev => ({ ...prev, [layerName]: !prev[layerName] }));
  };

  // Convert cluster timeline to map cluster points
  const mapClusterPoints: ClusterPoint[] = clusterTimeline.map((item, idx) => ({
    id: item.id,
    latitude: item.latitude,
    longitude: item.longitude,
    detected_at: item.detected_at,
    frp: item.frp,
    confidence: item.confidence,
    is_current: idx === timelineIndex
  }));

  // Selected event context payload for map proximity line
  const selectedEventContext: EventContextPayload | null = investigationData?.event ? {
    event: {
      id: investigationData.event.id,
      latitude: investigationData.event.latitude,
      longitude: investigationData.event.longitude
    },
    nearest_facility: (investigationData.nearest_facility && 
      investigationData.nearest_facility.latitude !== undefined && 
      investigationData.nearest_facility.longitude !== undefined) ? {
      id: investigationData.nearest_facility.id,
      name: investigationData.nearest_facility.name,
      latitude: investigationData.nearest_facility.latitude,
      longitude: investigationData.nearest_facility.longitude
    } : undefined,
    distance_meters: investigationData.nearest_facility?.distance_meters
  } : null;

  // Active Critical Alerts Count
  const criticalCount = eventsList.filter(e => (e.frp || 0) > 80).length;

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-mono">
      {/* 1. Global Header with Instant Search & Telemetry */}
      <Header
        activeModelVersion={activeModelVersion}
        onSelectEventId={(id) => selectAndLoadEvent(id, true)}
        onSelectFacility={(fac) => {
          setModalFacilityId(fac.id);
          cesiumRef.current?.flyTo(fac.longitude, fac.latitude, 4000);
        }}
        onSearchCoordinates={(lat, lon) => {
          cesiumRef.current?.flyTo(lon, lat, 8000);
        }}
        onOpenNotifications={() => setIsNotificationsOpen(true)}
        onOpenPreferences={() => setIsPreferencesOpen(true)}
        unreadNotificationsCount={unreadNotificationsCount}
        isLive={isConnected}
        lastUpdateTimestamp={lastUpdateTimestamp}
        autoFlyEnabled={autoFlyEnabled}
        onToggleAutoFly={() => setAutoFlyEnabled(prev => !prev)}
        onOpenPipelineModal={() => setIsPipelineModalOpen(true)}
        onOpenSihBrief={() => setShowSihBrief(true)}
        onToggleGuidedDemo={() => setShowGuidedDemo(prev => !prev)}
        isGuidedDemoActive={showGuidedDemo}
      />

      {/* 2. Main Middle Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar Navigation */}
        <SidebarNav
          activeTab={activeTab}
          onTabChange={setActiveTab}
          eventCount={eventsList.length}
          facilityCount={facilitiesGeoJson.features?.length || 0}
          criticalAlertCount={criticalCount}
          incidentCount={Math.max(1, Math.floor(eventsList.length / 3))}
        />

        {/* Center Workspace: 3D Cesium Map & Map Toolbar */}
        <main className="flex-1 relative overflow-hidden bg-slate-950">
          <CesiumMap
            ref={cesiumRef}
            geoJsonData={eventsGeoJson}
            facilitiesGeoJsonData={facilitiesGeoJson}
            selectedEventContext={selectedEventContext}
            selectedEventId={selectedEventId}
            clusterPoints={mapClusterPoints}
            showFirms={layers.showFirms}
            showFacilities={layers.showFacilities}
            showTerrain={layers.showTerrain}
            showSatellite={layers.showSatellite}
            showHistorical={layers.showHistorical}
            showNdvi={layers.showNdvi}
            showNbr={layers.showNbr}
            showLandCover={layers.showLandCover}
            showHeatmap={layers.showHeatmap}
            followEvent={followEvent}
            onEventSelect={(ev) => {
              if (ev && ev.id) {
                selectAndLoadEvent(ev.id);
              } else {
                setSelectedEventId(null);
                setInvestigationData(null);
                setClusterTimeline([]);
              }
            }}
            onFacilitySelect={(fac) => {
              if (fac && fac.id) {
                setModalFacilityId(fac.id);
              }
            }}
          />

          {/* Floating Map Toolbar Controls */}
          <MapToolbar
            layers={layers}
            onToggleLayer={handleToggleLayer}
            is2D={is2D}
            onToggle2D={(enable2D) => {
              setIs2D(enable2D);
              cesiumRef.current?.toggle2D(enable2D);
            }}
            onResetView={() => cesiumRef.current?.resetView()}
            hasSelectedEvent={Boolean(selectedEventId)}
            onInvestigateCurrent={handleInvestigateClick}
            followEvent={followEvent}
            onToggleFollowEvent={setFollowEvent}
          />

          {/* Phase 8 Live Non-Blocking Incident Toast Alert */}
          {incomingToastAlert && (
            <div className="absolute top-4 right-4 z-30 max-w-sm w-full bg-slate-950/95 border border-red-500/80 rounded-xl p-4 shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-top-3 duration-300 font-mono">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
                  <span className="text-[11px] font-bold text-red-400 tracking-wider">
                    {incomingToastAlert.severity} THERMAL ANOMALY
                  </span>
                </div>
                <button
                  onClick={() => setIncomingToastAlert(null)}
                  className="text-slate-400 hover:text-white text-xs p-1"
                >
                  ✕
                </button>
              </div>
              <div className="mt-2 text-xs font-semibold text-slate-100">
                {incomingToastAlert.title}
              </div>
              <div className="mt-1.5 flex items-center gap-3 text-[11px] text-slate-400">
                <span>FRP: <strong className="text-orange-400">{incomingToastAlert.frp} MW</strong></span>
                <span>Risk: <strong className="text-red-400">{incomingToastAlert.risk}/100</strong></span>
              </div>
              <div className="mt-3 flex items-center gap-2 pt-2 border-t border-slate-800">
                <button
                  onClick={() => {
                    selectAndLoadEvent(incomingToastAlert.eventId, true);
                    setIncomingToastAlert(null);
                  }}
                  className="flex-1 py-1 px-3 bg-red-600 hover:bg-red-500 text-white rounded text-xs font-bold text-center transition-colors"
                >
                  Inspect
                </button>
                {incomingToastAlert.lat && incomingToastAlert.lon && (
                  <button
                    onClick={() => {
                      cesiumRef.current?.flyTo(incomingToastAlert.lon!, incomingToastAlert.lat!, 3500);
                    }}
                    className="py-1 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-semibold transition-colors"
                  >
                    Fly To
                  </button>
                )}
                <button
                  onClick={() => setIncomingToastAlert(null)}
                  className="py-1 px-2.5 bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-300 rounded text-xs transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}


          {/* 1. Overview Dashboard Overlay */}
          {activeTab === 'overview' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <OverviewDashboard
                onNavigateToEvent={(eventId: number) => {
                  selectAndLoadEvent(eventId, true);
                  setActiveTab('dashboard');
                }}
                onNavigateToTab={(tab: any) => setActiveTab(tab)}
                onSelectFacility={(facId: number) => setModalFacilityId(facId)}
              />
            </div>
          )}

          {/* 2. Live Events Full Explorer Overlay */}
          {activeTab === 'events' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <LiveEventsView
                onSelectEvent={(eventId, flyTo) => {
                  selectAndLoadEvent(eventId, flyTo);
                  if (flyTo) setActiveTab('dashboard');
                }}
                onFlyTo={(lon, lat) => {
                  cesiumRef.current?.flyTo(lon, lat, 3500);
                  setActiveTab('dashboard');
                }}
                onOpenReport={(eventId) => {
                  setReportInitialTarget({ type: 'INCIDENT', id: eventId.toString() });
                  setActiveTab('reports');
                }}
              />
            </div>
          )}

          {/* 3. Incidents Command Board Overlay */}
          {activeTab === 'incidents' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <IncidentsView
                onFlyToIncident={(lon, lat) => {
                  cesiumRef.current?.flyTo(lon, lat, 4000);
                  setActiveTab('dashboard');
                }}
                onInspectEvent={(eventId) => {
                  selectAndLoadEvent(eventId, true);
                  setActiveTab('dashboard');
                }}
              />
            </div>
          )}

          {/* 4. Infrastructure Facilities Overlay */}
          {activeTab === 'facilities' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <FacilitiesView
                onSelectFacility={(facId) => {
                  setModalFacilityId(facId);
                }}
                onFlyToFacility={(lon, lat) => {
                  cesiumRef.current?.flyTo(lon, lat, 3500);
                  setActiveTab('dashboard');
                }}
                onGenerateReport={(facId) => {
                  setReportInitialTarget({ type: 'FACILITY', id: facId.toString() });
                  setActiveTab('reports');
                }}
              />
            </div>
          )}

          {/* 5. Active Alerts Center Overlay */}
          {activeTab === 'alerts' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <AlertCenter
                onInvestigateEvent={(eventId) => {
                  selectAndLoadEvent(eventId, true);
                  setActiveTab('dashboard');
                }}
                onClose={() => setActiveTab('dashboard')}
              />
            </div>
          )}

          {/* 6. Temporal Analytics Dashboard Overlay */}
          {activeTab === 'analytics' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <AnalyticsDashboard
                onInvestigateEvent={(eventId) => {
                  selectAndLoadEvent(eventId, true);
                  setActiveTab('dashboard');
                }}
                onSelectFacility={(facId) => {
                  setModalFacilityId(facId);
                }}
                onOpenReportStudio={(type, targetId) => {
                  setReportInitialTarget({ type, id: targetId });
                  setActiveTab('reports');
                }}
                onClose={() => setActiveTab('dashboard')}
              />
            </div>
          )}

          {/* 7. Intelligence Dossier / Report Studio Overlay */}
          {activeTab === 'reports' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <ReportBuilder
                initialType={reportInitialTarget.type}
                initialTargetId={reportInitialTarget.id}
                onInvestigateEvent={(eventId) => {
                  selectAndLoadEvent(eventId, true);
                  setActiveTab('dashboard');
                }}
                onClose={() => setActiveTab('dashboard')}
              />
            </div>
          )}

          {/* 8. Telemetry & Health Monitoring Overlay */}
          {activeTab === 'monitoring' && (
            <div className="absolute inset-0 z-20 bg-slate-950 overflow-hidden flex flex-col">
              <MonitoringView />
            </div>
          )}
        </main>

        {/* Right Event Investigation Workspace Panel */}
        <EventPanel
          data={investigationData}
          isLoading={loadingInvestigation}
          onClose={() => {
            setSelectedEventId(null);
            setInvestigationData(null);
            setClusterTimeline([]);
          }}
          onInvestigate={handleInvestigateClick}
          onOpenFacilityModal={(id) => setModalFacilityId(id)}
          onOpenCompareModal={() => setIsCompareOpen(true)}
          onGenerateReport={(evId) => {
            setReportInitialTarget({ type: 'INCIDENT', id: evId.toString() });
            setActiveTab('reports');
          }}
          onStatusUpdated={(newStatus) => {
            setInvestigationData(prev => prev ? {
              ...prev,
              event: { ...prev.event, status: newStatus }
            } : null);
          }}
          onToggleLayer={(layer) => setLayers(prev => ({ ...prev, [layer]: !prev[layer] }))}
          layers={layers}
        />
      </div>

      {/* 3. Bottom Timeline & Event History Playback */}
      {clusterTimeline.length > 0 && (
        <TemporalTimeline
          timeline={clusterTimeline}
          selectedIndex={timelineIndex}
          onSelectIndex={handleSelectTimelineIndex}
          isPlaying={isPlayingHistory}
          onTogglePlay={setIsPlayingHistory}
        />
      )}

      {/* 4. Modals */}
      <FacilityModal
        facilityId={modalFacilityId}
        isOpen={Boolean(modalFacilityId)}
        onClose={() => setModalFacilityId(null)}
        onFlyToFacility={(lon, lat) => {
          cesiumRef.current?.flyTo(lon, lat, 3500);
        }}
        onGenerateReport={(facId) => {
          setReportInitialTarget({ type: 'FACILITY', id: facId.toString() });
          setActiveTab('reports');
        }}
      />

      <EventComparisonModal
        currentEventId={selectedEventId}
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
      />

      {/* 5. Phase 6 Notification & Alert Modals */}
      <NotificationDrawer
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        onSelectEventId={(eventId) => {
          selectAndLoadEvent(eventId, true);
          setActiveTab('dashboard');
        }}
      />

      <AlertPreferencesModal
        isOpen={isPreferencesOpen}
        onClose={() => setIsPreferencesOpen(false)}
      />

      {/* 6. Phase 8 Autonomous Pipeline NOC & Telemetry Modal */}
      <PipelineMonitorModal
        isOpen={isPipelineModalOpen}
        onClose={() => setIsPipelineModalOpen(false)}
        onDemoTriggered={(eventId, lat, lon) => {
          selectAndLoadEvent(eventId, true);
          if (lat && lon) {
            cesiumRef.current?.flyTo(lon, lat, 4000);
          }
        }}
      />

      {/* 7. SIH Judge Defense & Problem Solution Explainer Modal (Section 27) */}
      <SihLandingExplainerModal
        isOpen={showSihBrief}
        onClose={() => setShowSihBrief(false)}
        onStartDemo={() => {
          setShowSihBrief(false);
          setShowGuidedDemo(true);
        }}
      />

      {/* 8. SIH 18-Step Autonomous Guided Demo Controller (Section 17, 18, 30) */}
      <SihDemoController
        isOpen={showGuidedDemo}
        onClose={() => setShowGuidedDemo(false)}
        onFlyToCoordinates={(lat, lon, height) => {
          cesiumRef.current?.flyTo(lon, lat, height ?? 15000);
        }}
        onSelectEventId={(id) => {
          selectAndLoadEvent(id, true);
        }}
        onNavigateTab={(tab) => {
          setActiveTab(tab);
        }}
        isLiveMode={isConnected}
      />
    </div>
  );
}

