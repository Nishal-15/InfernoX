"use client";

import React, { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import * as Cesium from 'cesium';
import "cesium/Build/Cesium/Widgets/widgets.css";
import { getAnalyticsGeospatial } from '@/lib/api';

declare global {
  interface Window {
    CESIUM_BASE_URL?: string;
  }
}

if (typeof window !== 'undefined') {
  window.CESIUM_BASE_URL = '/cesium';
}

export interface CesiumMapRef {
  flyTo: (longitude: number, latitude: number, height?: number) => void;
  investigate: (longitude: number, latitude: number) => void;
  resetView: () => void;
  toggle2D: (enable2D: boolean) => void;
}

export interface SelectedEventData {
  id?: number;
  detected_at?: string;
  satellite?: string;
  confidence?: number;
  frp?: number;
  brightness_temperature?: number;
  status?: string;
  source?: string;
  latitude: number;
  longitude: number;
}

export interface SelectedFacilityData {
  id?: number;
  osm_id?: string;
  name?: string;
  facility_type?: string;
  operator?: string;
  source?: string;
  latitude?: number;
  longitude?: number;
}

interface GeoJsonFeatureCollection {
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

export interface EventContextPayload {
  event: {
    id: number;
    latitude: number;
    longitude: number;
  };
  nearest_facility?: {
    id?: number;
    name?: string;
    latitude?: number;
    longitude?: number;
  };
  distance_meters?: number;
}

export interface ClusterPoint {
  id: number;
  latitude: number;
  longitude: number;
  detected_at?: string;
  frp?: number;
  confidence?: number;
  is_current?: boolean;
}

interface CesiumMapProps {
  geoJsonData: GeoJsonFeatureCollection;
  facilitiesGeoJsonData?: GeoJsonFeatureCollection;
  selectedEventContext?: EventContextPayload | null;
  selectedEventId?: number | null;
  clusterPoints?: ClusterPoint[];
  showFirms?: boolean;
  showFacilities?: boolean;
  showTerrain?: boolean;
  showSatellite?: boolean;
  showHistorical?: boolean;
  showNdvi?: boolean;
  showNbr?: boolean;
  showLandCover?: boolean;
  showHeatmap?: boolean;
  followEvent?: boolean;
  onEventSelect: (eventData: SelectedEventData | null) => void;
  onFacilitySelect?: (facilityData: SelectedFacilityData | null) => void;
  onMapClick?: () => void;
}

const CesiumMap = forwardRef<CesiumMapRef, CesiumMapProps>(({ 
  geoJsonData, 
  facilitiesGeoJsonData,
  selectedEventContext,
  selectedEventId,
  clusterPoints = [],
  showFirms = true,
  showFacilities = true,
  showTerrain = true,
  showSatellite = false,
  showHistorical = false,
  showNdvi = false,
  showNbr = false,
  showLandCover = false,
  showHeatmap = false,
  followEvent = false,
  onEventSelect,
  onFacilitySelect,
  onMapClick
}, ref) => {
  const cesiumContainer = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  
  const eventsDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null);
  const facilitiesDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null);
  const contextEntityRef = useRef<Cesium.Entity | null>(null);
  const focusEntityRef = useRef<Cesium.Entity | null>(null);
  const footprintEntityRef = useRef<Cesium.Entity | null>(null);
  const clusterEntitiesRef = useRef<Cesium.Entity[]>([]);
  const imageryLayerRef = useRef<Cesium.ImageryLayer | null>(null);
  const falseColorLayerRef = useRef<Cesium.ImageryLayer | null>(null);
  const heatmapDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null);

  useImperativeHandle(ref, () => ({
    flyTo: (longitude: number, latitude: number, height: number = 5000) => {
      if (viewerRef.current) {
        viewerRef.current.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, height),
          orientation: {
            heading: Cesium.Math.toRadians(0.0),
            pitch: Cesium.Math.toRadians(-45.0),
            roll: 0.0
          },
          duration: 2.0
        });
      }
    },
    investigate: (longitude: number, latitude: number) => {
      if (!viewerRef.current) return;
      const camera = viewerRef.current.camera;
      
      // Multi-stage cinematic investigation flight:
      // Stage 1: Regional swoop down to 40,000m
      camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, 40000),
        orientation: {
          heading: Cesium.Math.toRadians(0.0),
          pitch: Cesium.Math.toRadians(-60.0),
          roll: 0.0
        },
        duration: 1.5,
        complete: () => {
          // Stage 2: Final tactical approach to 2,400m at angled pitch
          if (viewerRef.current && !viewerRef.current.isDestroyed()) {
            viewerRef.current.camera.flyTo({
              destination: Cesium.Cartesian3.fromDegrees(longitude, latitude - 0.012, 2400),
              orientation: {
                heading: Cesium.Math.toRadians(12.0),
                pitch: Cesium.Math.toRadians(-35.0),
                roll: 0.0
              },
              duration: 1.8
            });
          }
        }
      });
    },
    resetView: () => {
      if (viewerRef.current) {
        viewerRef.current.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(78.9629, 20.5937, 12000000), // Center of India / Global
          orientation: {
            heading: 0.0,
            pitch: Cesium.Math.toRadians(-90.0),
            roll: 0.0
          },
          duration: 2.0
        });
      }
    },
    toggle2D: (enable2D: boolean) => {
      if (viewerRef.current) {
        if (enable2D) {
          viewerRef.current.scene.morphTo2D(1.5);
        } else {
          viewerRef.current.scene.morphTo3D(1.5);
        }
      }
    }
  }));

  // Initialize Viewer
  useEffect(() => {
    if (!cesiumContainer.current) return;

    if (process.env.NEXT_PUBLIC_CESIUM_ION_ACCESS_TOKEN) {
      Cesium.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_ACCESS_TOKEN;
    }

    const viewer = new Cesium.Viewer(cesiumContainer.current, {
      terrain: showTerrain ? Cesium.Terrain.fromWorldTerrain() : undefined,
      animation: false,
      timeline: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      selectionIndicator: false,
      fullscreenButton: false,
      baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        Cesium.IonImageryProvider.fromAssetId(2)
      )
    });

    const creditContainer = viewer.bottomContainer;
    if (creditContainer) {
      (creditContainer as HTMLElement).style.display = 'none';
    }

    viewerRef.current = viewer;

    // Click handler
    viewer.screenSpaceEventHandler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      const pickedObject = viewer.scene.pick(click.position);
      if (Cesium.defined(pickedObject) && pickedObject.id) {
        const entity = pickedObject.id;
        if (entity.properties) {
          const type = entity.properties.facility_type ? 'facility' : 'event';
          
          if (type === 'event') {
            const props: SelectedEventData = {
              id: entity.properties.id?.getValue(),
              detected_at: entity.properties.detected_at?.getValue(),
              satellite: entity.properties.satellite?.getValue(),
              confidence: entity.properties.confidence?.getValue(),
              frp: entity.properties.frp?.getValue(),
              brightness_temperature: entity.properties.brightness_temperature?.getValue(),
              status: entity.properties.status?.getValue(),
              source: entity.properties.source?.getValue(),
              latitude: entity.properties.latitude?.getValue() || (entity.position ? Cesium.Cartographic.fromCartesian(entity.position.getValue(Cesium.JulianDate.now())!).latitude * (180 / Math.PI) : 0),
              longitude: entity.properties.longitude?.getValue() || (entity.position ? Cesium.Cartographic.fromCartesian(entity.position.getValue(Cesium.JulianDate.now())!).longitude * (180 / Math.PI) : 0),
            };
            onEventSelect(props);
            if (onFacilitySelect) onFacilitySelect(null);
          } else {
            const props: SelectedFacilityData = {
              id: entity.properties.id?.getValue(),
              osm_id: entity.properties.osm_id?.getValue(),
              name: entity.properties.name?.getValue(),
              facility_type: entity.properties.facility_type?.getValue(),
              operator: entity.properties.operator?.getValue(),
              source: entity.properties.source?.getValue(),
              latitude: entity.position?.getValue(Cesium.JulianDate.now()) 
                  ? Cesium.Cartographic.fromCartesian(entity.position.getValue(Cesium.JulianDate.now())!).latitude * (180 / Math.PI)
                  : undefined,
              longitude: entity.position?.getValue(Cesium.JulianDate.now()) 
                  ? Cesium.Cartographic.fromCartesian(entity.position.getValue(Cesium.JulianDate.now())!).longitude * (180 / Math.PI)
                  : undefined,
            };
            if (onFacilitySelect) onFacilitySelect(props);
            onEventSelect(null);
          }
        }
      } else {
        onEventSelect(null);
        if (onFacilitySelect) onFacilitySelect(null);
        if (onMapClick) onMapClick();
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => {
      viewer.destroy();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update Terrain
  useEffect(() => {
    if (!viewerRef.current) return;
    if (showTerrain) {
      viewerRef.current.scene.setTerrain(Cesium.Terrain.fromWorldTerrain());
    } else {
      viewerRef.current.scene.setTerrain(new Cesium.Terrain(Promise.resolve(new Cesium.EllipsoidTerrainProvider())));
    }
  }, [showTerrain]);

  // Update Satellite Imagery (Sentinel-2 True Color)
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;
    
    if (showSatellite && !imageryLayerRef.current) {
      Cesium.IonImageryProvider.fromAssetId(3954).then(provider => {
        if (viewer.isDestroyed()) return;
        const layer = viewer.imageryLayers.addImageryProvider(provider);
        layer.alpha = 0.85;
        imageryLayerRef.current = layer;
      }).catch(e => console.warn("Failed to load Sentinel-2 imagery", e));
    } else if (!showSatellite && imageryLayerRef.current) {
      viewer.imageryLayers.remove(imageryLayerRef.current);
      imageryLayerRef.current = null;
    }
  }, [showSatellite]);

  // Handle False Color / NDVI / NBR Layer
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;
    const needsSpectral = showNdvi || showNbr || showLandCover;

    if (needsSpectral && !falseColorLayerRef.current) {
      Cesium.IonImageryProvider.fromAssetId(3812).then(provider => {
        if (viewer.isDestroyed()) return;
        const layer = viewer.imageryLayers.addImageryProvider(provider);
        layer.alpha = showNdvi ? 0.75 : showNbr ? 0.65 : 0.55;
        falseColorLayerRef.current = layer;
      }).catch(e => console.warn("Failed to load spectral raster layer", e));
    } else if (!needsSpectral && falseColorLayerRef.current) {
      viewer.imageryLayers.remove(falseColorLayerRef.current);
      falseColorLayerRef.current = null;
    }
  }, [showNdvi, showNbr, showLandCover]);

  // Handle Thermal Events
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;

    const loadData = async () => {
      if (eventsDataSourceRef.current) {
        viewer.dataSources.remove(eventsDataSourceRef.current);
        eventsDataSourceRef.current = null;
      }

      if (!showFirms || !geoJsonData || !geoJsonData.features || geoJsonData.features.length === 0) return;
      
      const filteredGeoJson = {
        ...geoJsonData,
        features: geoJsonData.features.filter(f => {
          if (showHistorical) return true;
          const date = new Date(String(f.properties.detected_at || ""));
          const now = new Date();
          return (now.getTime() - date.getTime()) <= 48 * 60 * 60 * 1000;
        })
      };

      const dataSource = await Cesium.GeoJsonDataSource.load(filteredGeoJson);

      const entities = dataSource.entities.values;
      for (let i = 0; i < entities.length; i++) {
        const entity = entities[i];
        if (entity.billboard) {
          entity.billboard.show = new Cesium.ConstantProperty(false);
        }
        
        const date = new Date(entity.properties?.detected_at?.getValue());
        const isHistorical = (new Date().getTime() - date.getTime()) > 24 * 60 * 60 * 1000;
        const frp = entity.properties?.frp?.getValue() || 20;
        const riskLevel = (entity.properties?.risk_level?.getValue() || '').toUpperCase();
        const priorityLevel = (entity.properties?.priority_level?.getValue() || '').toUpperCase();

        // 4-tier analytical severity evaluation
        const effectiveSeverity = riskLevel || priorityLevel || (frp >= 80 ? 'CRITICAL' : frp >= 45 ? 'HIGH' : frp >= 20 ? 'MODERATE' : 'LOW');
        const rawClass = (entity.properties?.classification?.getValue() || '').toUpperCase();

        let pointColor = Cesium.Color.fromCssColorString('#94a3b8'); // Neutral slate
        let pixelSize = effectiveSeverity === 'CRITICAL' ? 16 : effectiveSeverity === 'HIGH' ? 12 : effectiveSeverity === 'MODERATE' ? 10 : 8;
        let outlineWidth = effectiveSeverity === 'CRITICAL' ? 3.5 : effectiveSeverity === 'HIGH' ? 2.5 : effectiveSeverity === 'MODERATE' ? 2.0 : 1.5;
        let outlineColor = effectiveSeverity === 'CRITICAL' ? Cesium.Color.fromCssColorString('#fecaca') : Cesium.Color.WHITE;
        let labelIcon = '🔥';
        let labelPrefix = 'ANOMALY';

        if (isHistorical) {
          pointColor = Cesium.Color.fromCssColorString('#f97316').withAlpha(0.65);
          pixelSize = 7;
          outlineWidth = 1;
          labelIcon = '⏱️';
          labelPrefix = 'HIST';
        } else if (rawClass === 'INDUSTRIAL_FIRE') {
          pointColor = Cesium.Color.fromCssColorString('#ef4444'); // Industrial Fire (Red)
          labelIcon = '🚨';
          labelPrefix = '[IND-FIRE]';
        } else if (rawClass === 'GAS_FLARE' || rawClass === 'PERSISTENT_INDUSTRIAL_THERMAL_SOURCE') {
          pointColor = Cesium.Color.fromCssColorString('#c084fc'); // Gas Flare / Persistent Source (Violet)
          labelIcon = '⚡';
          labelPrefix = '[FLARE]';
        } else if (rawClass === 'WILDFIRE') {
          pointColor = Cesium.Color.fromCssColorString('#22c55e'); // Wildfire / Forest (Green)
          labelIcon = '🌲';
          labelPrefix = '[WILDFIRE]';
        } else if (rawClass === 'AGRICULTURAL_BURNING') {
          pointColor = Cesium.Color.fromCssColorString('#eab308'); // Agricultural Burning (Yellow/Gold)
          labelIcon = '🌾';
          labelPrefix = '[AGRI]';
        } else if (rawClass === 'MINING_ACTIVITY') {
          pointColor = Cesium.Color.fromCssColorString('#f97316'); // Mining (Amber)
          labelIcon = '⛏️';
          labelPrefix = '[MINING]';
        } else if (effectiveSeverity === 'CRITICAL') {
          pointColor = Cesium.Color.fromCssColorString('#ef4444');
          labelIcon = '🛑';
          labelPrefix = '[CRIT]';
        } else if (effectiveSeverity === 'HIGH') {
          pointColor = Cesium.Color.fromCssColorString('#f97316');
          labelIcon = '🔶';
          labelPrefix = '[HIGH]';
        } else if (effectiveSeverity === 'MODERATE') {
          pointColor = Cesium.Color.fromCssColorString('#eab308');
          labelIcon = '⚠️';
          labelPrefix = '[MOD]';
        } else {
          pointColor = Cesium.Color.fromCssColorString('#38bdf8');
          labelIcon = '🟢';
          labelPrefix = '[LOW]';
        }

        entity.point = new Cesium.PointGraphics({
          pixelSize,
          color: pointColor,
          outlineColor,
          outlineWidth
        });
        
        if (!isHistorical) {
          entity.label = new Cesium.LabelGraphics({
            text: `${labelIcon} ${labelPrefix} ${Math.round(frp)} MW`,
            font: effectiveSeverity === 'CRITICAL' ? 'bold 11pt monospace' : '10pt monospace',
            fillColor: effectiveSeverity === 'CRITICAL' ? Cesium.Color.fromCssColorString('#fca5a5') : Cesium.Color.fromCssColorString('#fef08a'),
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            outlineWidth: 2,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -16),
            showBackground: true,
            backgroundColor: Cesium.Color.BLACK.withAlpha(0.85),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 500000)
          });
        }
      }

      viewer.dataSources.add(dataSource);
      eventsDataSourceRef.current = dataSource;
    };
    loadData();
  }, [geoJsonData, showHistorical, showFirms]);

  // Handle Facilities
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;

    const loadData = async () => {
      if (facilitiesDataSourceRef.current) {
        viewer.dataSources.remove(facilitiesDataSourceRef.current);
        facilitiesDataSourceRef.current = null;
      }

      if (!showFacilities || !facilitiesGeoJsonData || !facilitiesGeoJsonData.features || facilitiesGeoJsonData.features.length === 0) return;

      const dataSource = await Cesium.GeoJsonDataSource.load(facilitiesGeoJsonData);

      const entities = dataSource.entities.values;
      for (let i = 0; i < entities.length; i++) {
        const entity = entities[i];
        if (entity.billboard) {
          entity.billboard.show = new Cesium.ConstantProperty(false);
        }
        entity.point = new Cesium.PointGraphics({
          pixelSize: 11,
          color: Cesium.Color.fromCssColorString('#0ea5e9'),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2
        });
        entity.label = new Cesium.LabelGraphics({
          text: `🏭 ${entity.properties?.name?.getValue() || 'Industrial Facility'}`,
          font: '10pt monospace',
          fillColor: Cesium.Color.fromCssColorString('#bae6fd'),
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -14),
          showBackground: true,
          backgroundColor: Cesium.Color.BLACK.withAlpha(0.8),
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 30000)
        });
      }

      viewer.dataSources.add(dataSource);
      facilitiesDataSourceRef.current = dataSource;
    };
    loadData();
  }, [facilitiesGeoJsonData, showFacilities]);

  // Handle Event Focus Visualizations (Glowing 3D pin + thermal radius footprint)
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;

    // Clean previous focus entities
    if (focusEntityRef.current) {
      viewer.entities.remove(focusEntityRef.current);
      focusEntityRef.current = null;
    }
    if (footprintEntityRef.current) {
      viewer.entities.remove(footprintEntityRef.current);
      footprintEntityRef.current = null;
    }

    if (selectedEventContext && selectedEventContext.event) {
      const { latitude, longitude } = selectedEventContext.event;

      // 1. Vertical 3D Indicator Cylinder (Beacon)
      focusEntityRef.current = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(longitude, latitude, 600),
        cylinder: {
          length: 1200.0,
          topRadius: 15.0,
          bottomRadius: 6.0,
          material: new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString('#ef4444').withAlpha(0.65)),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#fca5a5')
        }
      });

      // 2. Ground Thermal Footprint Ellipse
      footprintEntityRef.current = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(longitude, latitude, 0),
        ellipse: {
          semiMajorAxis: 300.0,
          semiMinorAxis: 300.0,
          material: new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString('#f97316').withAlpha(0.35)),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#fbbf24'),
          outlineWidth: 2
        }
      });

      // Follow event camera tracking if enabled
      if (followEvent) {
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(longitude, latitude - 0.008, 2500),
          orientation: {
            heading: Cesium.Math.toRadians(0.0),
            pitch: Cesium.Math.toRadians(-40.0),
            roll: 0.0
          },
          duration: 1.0
        });
      }
    }
  }, [selectedEventContext, selectedEventId, followEvent]);

  // Handle Cluster Historical Sequence
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;

    // Clear old cluster entities
    clusterEntitiesRef.current.forEach(e => viewer.entities.remove(e));
    clusterEntitiesRef.current = [];

    if (clusterPoints && clusterPoints.length > 1) {
      // Connect chronological cluster detections with dashed path
      const sorted = [...clusterPoints].sort((a, b) => {
        const da = a.detected_at ? new Date(a.detected_at).getTime() : 0;
        const db = b.detected_at ? new Date(b.detected_at).getTime() : 0;
        return da - db;
      });

      const positions = sorted.map(p => Cesium.Cartesian3.fromDegrees(p.longitude, p.latitude, 50));
      if (positions.length >= 2) {
        const pathEntity = viewer.entities.add({
          polyline: {
            positions: positions,
            width: 2,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.7),
              dashLength: 6.0
            })
          }
        });
        clusterEntitiesRef.current.push(pathEntity);
      }

      // Add small markers for cluster nodes
      sorted.forEach((pt, idx) => {
        const nodeEntity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(pt.longitude, pt.latitude, 20),
          point: {
            pixelSize: pt.is_current ? 14 : 7,
            color: pt.is_current ? Cesium.Color.RED : Cesium.Color.fromCssColorString('#f59e0b'),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 1
          },
          label: {
            text: `T${idx + 1}`,
            font: '8pt monospace',
            fillColor: Cesium.Color.WHITE,
            pixelOffset: new Cesium.Cartesian2(0, 10),
            showBackground: true,
            backgroundColor: Cesium.Color.BLACK.withAlpha(0.6),
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 50000)
          }
        });
        clusterEntitiesRef.current.push(nodeEntity);
      });
    }
  }, [clusterPoints]);

  // Handle Context Proximity Line
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;
    
    if (contextEntityRef.current) {
      viewer.entities.remove(contextEntityRef.current);
      contextEntityRef.current = null;
    }

    const fac = selectedEventContext?.nearest_facility;
    if (
      selectedEventContext?.event &&
      fac &&
      typeof fac.longitude === 'number' &&
      typeof fac.latitude === 'number'
    ) {
      const { event, distance_meters } = selectedEventContext;
      const nLon = fac.longitude;
      const nLat = fac.latitude;
      
      const positions = Cesium.Cartesian3.fromDegreesArray([
        event.longitude, event.latitude,
        nLon, nLat
      ]);
      
      contextEntityRef.current = viewer.entities.add({
        polyline: {
          positions: positions,
          width: 3,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.YELLOW,
            dashLength: 8.0
          }),
        },
        position: Cesium.Cartesian3.midpoint(
          Cesium.Cartesian3.fromDegrees(event.longitude, event.latitude),
          Cesium.Cartesian3.fromDegrees(nLon, nLat),
          new Cesium.Cartesian3()
        ),
        label: {
          text: `PROXIMITY: ${distance_meters ?? 'N/A'} m`,
          font: '10pt monospace',
          fillColor: Cesium.Color.YELLOW,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          showBackground: true,
          backgroundColor: Cesium.Color.BLACK.withAlpha(0.85),
          pixelOffset: new Cesium.Cartesian2(0, -10),
        }
      });
    }
  }, [selectedEventContext]);

  // Phase 7: Analytical Heatmap Grid Layer
  useEffect(() => {
    if (!viewerRef.current) return;
    const viewer = viewerRef.current;

    if (!showHeatmap) {
      if (heatmapDataSourceRef.current) {
        viewer.dataSources.remove(heatmapDataSourceRef.current, true);
        heatmapDataSourceRef.current = null;
      }
      return;
    }

    const loadHeatmapGrid = async () => {
      try {
        const res = await getAnalyticsGeospatial({ resolution_deg: 0.25 });
        if (!res?.geojson) return;

        const ds = await Cesium.GeoJsonDataSource.load(res.geojson, {
          stroke: Cesium.Color.fromCssColorString('#f97316').withAlpha(0.7),
          strokeWidth: 1.5,
          fill: Cesium.Color.fromCssColorString('#ef4444').withAlpha(0.2)
        });

        for (const entity of ds.entities.values) {
          if (entity.polygon) {
            const frp = entity.properties?.mean_frp?.getValue() || 10;
            const count = entity.properties?.event_count?.getValue() || 1;
            const alpha = Math.min(0.2 + (count / 20) * 0.4, 0.6);
            const color = frp >= 50
              ? Cesium.Color.fromCssColorString('#ef4444').withAlpha(alpha)
              : frp >= 25
              ? Cesium.Color.fromCssColorString('#f97316').withAlpha(alpha)
              : Cesium.Color.fromCssColorString('#eab308').withAlpha(alpha);

            entity.polygon.material = new Cesium.ColorMaterialProperty(color);
            entity.polygon.outline = new Cesium.ConstantProperty(true);
            entity.polygon.outlineColor = new Cesium.ConstantProperty(
              Cesium.Color.fromCssColorString('#fbbf24').withAlpha(0.8)
            );
          }
        }

        viewer.dataSources.add(ds);
        heatmapDataSourceRef.current = ds;
      } catch (err) {
        console.error('Failed to load analytical heatmap grid:', err);
      }
    };

    loadHeatmapGrid();

    return () => {
      if (heatmapDataSourceRef.current && viewerRef.current) {
        viewerRef.current.dataSources.remove(heatmapDataSourceRef.current, true);
        heatmapDataSourceRef.current = null;
      }
    };
  }, [showHeatmap]);

  return (
    <div className="w-full h-full relative overflow-hidden bg-slate-950">
      <div ref={cesiumContainer} className="w-full h-full" />

      {/* Industrial vs Natural Fire Semantic Map Legend */}
      <div className="absolute bottom-6 left-4 z-20 bg-slate-950/90 border border-slate-800/90 backdrop-blur-md rounded-lg p-3 shadow-2xl font-mono text-[11px] text-slate-300 pointer-events-auto select-none max-w-[280px]">
        <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-slate-800">
          <span className="font-bold text-[11px] text-white tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            CLASSIFICATION
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-400">SIH GIS</span>
        </div>
        <div className="grid grid-cols-2 gap-x-2.5 gap-y-1.5 text-[10px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-sm shadow-red-500/50"></span>
            <span className="text-red-400 font-medium truncate">Industrial Fire</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400 shadow-sm shadow-purple-500/50"></span>
            <span className="text-purple-300 font-medium truncate">Gas Flare</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50"></span>
            <span className="text-emerald-400 font-medium truncate">Wildfire</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 shadow-sm shadow-yellow-500/50"></span>
            <span className="text-yellow-300 font-medium truncate">Agricultural</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-400 shadow-sm shadow-orange-500/50"></span>
            <span className="text-orange-300 font-medium truncate">Mining</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400 shadow-sm shadow-sky-500/50"></span>
            <span className="text-sky-300 font-medium truncate">Facility (OSM)</span>
          </div>
        </div>
        <div className="mt-2 pt-1.5 border-t border-slate-800/80 flex items-center justify-between text-[9px] text-slate-400">
          <span>Outer Ring = Risk Level</span>
          <span className="text-slate-500">VIIRS 375m</span>
        </div>
      </div>
    </div>
  );
});

CesiumMap.displayName = 'CesiumMap';
export default CesiumMap;
