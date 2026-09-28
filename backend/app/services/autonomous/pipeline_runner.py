import time
import uuid
import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.models.thermal_event import ThermalEvent
from app.models.facility import Facility
from app.models.ai_models import EventAssessment
from app.models.risk_alert import RiskAssessment, Alert
from app.models.incident import ThermalIncident
from app.models.pipeline import (
    PipelineJob,
    PipelineStageRun,
    AutonomousAuditLog
)
from app.services.features.engineer import FeatureEngineer
from app.services.temporal.analyzer import TemporalAnalyzer
from app.services.ml.classifier import MLClassifier
from app.services.landcover.provider import LandCoverProvider
from app.services.satellite.provider import Sentinel2Provider
from app.services.risk.engine import RiskEngine
from app.services.alert.engine import AlertEngine
from app.services.autonomous.incident_correlator import IncidentCorrelator
from app.services.autonomous.retry_policy import RetryPolicy
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

class PipelineRunner:
    """
    Autonomous Geospatial Thermal Intelligence Pipeline Runner.
    Orchestrates continuous multi-modal processing across 10 deterministic stages:
      1. Spatial Context Enrichment (OSM Infrastructure)
      2. Temporal Persistence Analysis (Cluster Statistics & Status)
      3. Land Cover & Satellite Evidence Evaluation
      4. Multi-modal Feature Engineering
      5. ML Classification Inference (XGBoost / Heuristic Fallback)
      6. Analytical Risk Scoring (0-100 & Factor Breakdown)
      7. Thermal Incident Correlation (Cluster grouping, anti-storm)
      8. Alert Engine Evaluation & Deduplication
      9. In-App Notification Dispatch & Audit Logging
      10. Real-Time WebSocket Telemetry Broadcast
    
    Supports persistent stage-level tracking, restart recovery, and idempotent retries.
    """

    @classmethod
    def _get_or_create_stage_run(
        cls,
        db: Session,
        job_id: int,
        event_id: int,
        correlation_id: str,
        stage_name: str
    ) -> PipelineStageRun:
        """Finds existing stage run or initializes a new one."""
        run = db.query(PipelineStageRun).filter(
            PipelineStageRun.job_id == job_id,
            PipelineStageRun.event_id == event_id,
            PipelineStageRun.stage_name == stage_name
        ).first()

        if not run:
            run = PipelineStageRun(
                job_id=job_id,
                event_id=event_id,
                correlation_id=correlation_id,
                stage_name=stage_name,
                status="RUNNING",
                started_at=datetime.now(timezone.utc)
            )
            db.add(run)
            db.commit()
            db.refresh(run)
        else:
            run.status = "RUNNING"
            run.started_at = datetime.now(timezone.utc)
            db.commit()

        return run

    @classmethod
    def _record_stage_success(
        cls,
        db: Session,
        stage_run: PipelineStageRun,
        duration_s: float,
        output: Dict[str, Any]
    ) -> None:
        import json
        stage_run.status = "SUCCESS"
        stage_run.duration_seconds = round(duration_s, 3)
        try:
            stage_run.stage_output_json = json.loads(json.dumps(output, default=str))
        except Exception:
            stage_run.stage_output_json = {}
        stage_run.completed_at = datetime.now(timezone.utc)
        db.commit()

    @classmethod
    def _record_stage_failure(
        cls,
        db: Session,
        stage_run: PipelineStageRun,
        duration_s: float,
        error: Exception
    ) -> None:
        try:
            db.rollback()
        except Exception:
            pass
        stage_run.status = "FAILED"
        stage_run.duration_seconds = round(duration_s, 3)
        stage_run.is_transient_error = RetryPolicy.is_transient(error)
        stage_run.error_message = str(error)[:1000]
        stage_run.completed_at = datetime.now(timezone.utc)
        try:
            db.commit()
        except Exception:
            db.rollback()

    @classmethod
    async def process_event(
        cls,
        db: Session,
        event_id: int,
        job_id: int,
        correlation_id: str,
        force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the autonomous intelligence pipeline for a single ThermalEvent.
        """
        event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
        if not event:
            raise ValueError(f"ThermalEvent {event_id} not found")

        stages_executed: List[str] = []
        pipeline_result: Dict[str, Any] = {
            "event_id": event_id,
            "correlation_id": correlation_id,
            "status": "SUCCESS"
        }

        # Stage 1: Spatial Context Enrichment
        t0 = time.perf_counter()
        stage_spatial = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "SPATIAL_ENRICHMENT")
        spatial_context = {}
        try:
            # Query nearby facilities (PostGIS with SQLite fallback)
            radius_m = settings.INDUSTRIAL_PROXIMITY_THRESHOLD_METERS
            point_geom = f"SRID=4326;POINT({event.longitude} {event.latitude})"
            matched_facs = []
            try:
                fac_query = db.query(
                    Facility,
                    text(f"ST_Distance(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography) as dist")
                ).filter(
                    text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {radius_m})")
                ).order_by(text("dist ASC")).limit(5).all()

                for fac, dist in fac_query:
                    matched_facs.append({
                        "id": fac.id,
                        "name": fac.name,
                        "facility_type": fac.facility_type,
                        "distance_meters": round(float(dist), 1),
                        "latitude": fac.latitude,
                        "longitude": fac.longitude
                    })
            except Exception:
                # SQLite fallback
                all_facs = db.query(Facility).all()
                for fac in all_facs:
                    dlat = (fac.latitude - event.latitude) * 111000
                    dlon = (fac.longitude - event.longitude) * 111000 * math.cos(math.radians(event.latitude))
                    dist = math.sqrt(dlat**2 + dlon**2)
                    if dist <= radius_m:
                        matched_facs.append({
                            "id": fac.id,
                            "name": fac.name,
                            "facility_type": fac.facility_type,
                            "distance_meters": round(dist, 1),
                            "latitude": fac.latitude,
                            "longitude": fac.longitude
                        })
                matched_facs.sort(key=lambda x: x["distance_meters"])

            nearest = matched_facs[0] if matched_facs else None
            spatial_context = {
                "nearest_facility": nearest,
                "distance_meters": nearest["distance_meters"] if nearest else None,
                "facility_count": len(matched_facs),
                "facilities": matched_facs
            }
            cls._record_stage_success(db, stage_spatial, time.perf_counter() - t0, spatial_context)
            stages_executed.append("SPATIAL_ENRICHMENT")
        except Exception as e:
            cls._record_stage_failure(db, stage_spatial, time.perf_counter() - t0, e)
            logger.error(f"Stage SPATIAL_ENRICHMENT failed for event {event_id}: {e}")
            raise

        # Stage 2: Temporal Persistence Analysis
        t0 = time.perf_counter()
        stage_temporal = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "TEMPORAL_ANALYSIS")
        temporal_data = {}
        try:
            temporal_analyzer = TemporalAnalyzer()
            ev_dict = {
                "id": event.id,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "frp": event.frp,
                "confidence": event.confidence,
                "detected_at": event.detected_at.isoformat() if event.detected_at else None
            }
            # Query historical points in radius
            cluster_recs = []
            lookback_cutoff = (event.detected_at or datetime.now(timezone.utc)) - timedelta(days=settings.TEMPORAL_LOOKBACK_DAYS)
            
            try:
                hist_evs = db.query(ThermalEvent).filter(
                    ThermalEvent.id != event.id,
                    ThermalEvent.detected_at >= lookback_cutoff,
                    text(f"ST_DWithin(geometry::geography, ST_GeomFromEWKT('{point_geom}')::geography, {temporal_analyzer.radius_meters})")
                ).all()
                for h in hist_evs:
                    cluster_recs.append({
                        "id": h.id,
                        "detected_at": h.detected_at.isoformat() if h.detected_at else None,
                        "frp": h.frp,
                        "confidence": h.confidence,
                        "latitude": h.latitude,
                        "longitude": h.longitude
                    })
            except Exception:
                all_evs = db.query(ThermalEvent).filter(
                    ThermalEvent.id != event.id,
                    ThermalEvent.detected_at >= lookback_cutoff
                ).all()
                for h in all_evs:
                    dlat = (h.latitude - event.latitude) * 111000
                    dlon = (h.longitude - event.longitude) * 111000 * math.cos(math.radians(event.latitude))
                    if math.sqrt(dlat**2 + dlon**2) <= temporal_analyzer.radius_meters:
                        cluster_recs.append({
                            "id": h.id,
                            "detected_at": h.detected_at.isoformat() if h.detected_at else None,
                            "frp": h.frp,
                            "confidence": h.confidence,
                            "latitude": h.latitude,
                            "longitude": h.longitude
                        })

            temporal_res = temporal_analyzer.compute_metrics(ev_dict, cluster_recs)
            temporal_data = {
                "status": temporal_res.get("temporal_status", "NEW"),
                "active_days": temporal_res.get("metrics", {}).get("active_days", 1),
                "duration_hours": temporal_res.get("metrics", {}).get("duration_hours", 0.0),
                "mean_frp": temporal_res.get("metrics", {}).get("mean_frp", event.frp),
                "max_frp": temporal_res.get("metrics", {}).get("max_frp", event.frp),
                "event_count": temporal_res.get("metrics", {}).get("event_count", 1),
                "metrics": temporal_res.get("metrics", {})
            }
            cls._record_stage_success(db, stage_temporal, time.perf_counter() - t0, temporal_data)
            stages_executed.append("TEMPORAL_ANALYSIS")
        except Exception as e:
            cls._record_stage_failure(db, stage_temporal, time.perf_counter() - t0, e)
            logger.error(f"Stage TEMPORAL_ANALYSIS failed for event {event_id}: {e}")
            raise

        # Stage 3: Satellite & Land Cover Evidence
        t0 = time.perf_counter()
        stage_sat = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "SATELLITE_EVALUATION")
        satellite_data = {}
        try:
            lc_info = LandCoverProvider().get_land_cover(float(event.latitude), float(event.longitude)) or {}
            # Query satellite provider
            stac_info = None
            try:
                sat_provider = Sentinel2Provider()
                target_dt = event.detected_at or datetime.now(timezone.utc)
                stac_info = sat_provider.search_imagery(float(event.latitude), float(event.longitude), target_dt)
            except Exception as stac_err:
                logger.debug(f"Satellite scene lookup non-fatal: {stac_err}")

            satellite_data = {
                "available": bool(stac_info and stac_info.get("scene_id")),
                "scene_id": stac_info.get("scene_id") if stac_info else None,
                "cloud_cover": stac_info.get("cloud_cover") if stac_info else None,
                "landcover_class": lc_info.get("class_name", "Unknown") if isinstance(lc_info, dict) else "Unknown",
                "landcover_code": lc_info.get("class_code", 0) if isinstance(lc_info, dict) else 0,
                "indices": stac_info.get("indices") if stac_info else {}
            }
            cls._record_stage_success(db, stage_sat, time.perf_counter() - t0, satellite_data)
            stages_executed.append("SATELLITE_EVALUATION")
        except Exception as e:
            # Satellite lookup failures should be gracefully handled as degraded evidence rather than blocking pipeline
            cls._record_stage_failure(db, stage_sat, time.perf_counter() - t0, e)
            satellite_data = {"available": False, "landcover_class": "Built-up / Urban", "landcover_code": 50}

        # Stage 4: Feature Engineering
        t0 = time.perf_counter()
        stage_feat = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "FEATURE_ENGINEERING")
        features_obj = None
        try:
            features_obj = FeatureEngineer.extract_features(
                event=event,
                spatial_context=spatial_context,
                temporal_data=temporal_data,
                satellite_data=satellite_data
            )
            cls._record_stage_success(db, stage_feat, time.perf_counter() - t0, features_obj.model_dump())
            stages_executed.append("FEATURE_ENGINEERING")
        except Exception as e:
            cls._record_stage_failure(db, stage_feat, time.perf_counter() - t0, e)
            logger.error(f"Stage FEATURE_ENGINEERING failed: {e}")
            raise

        # Stage 5: ML Classification
        t0 = time.perf_counter()
        stage_ml = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "CLASSIFICATION")
        classification_result = {}
        try:
            classifier = MLClassifier()
            classification_result = classifier.classify(features_obj)

            # Persist or update EventAssessment idempotently
            pred_class = classification_result.get("classification", "UNKNOWN")
            pred_prob = classification_result.get("model_probability", 0.5)
            import json
            feat_safe = json.loads(json.dumps(features_obj.model_dump(), default=str))

            assessment = db.query(EventAssessment).filter(EventAssessment.event_id == event.id).first()
            priority_score = round(float(pred_prob) * 100, 1)
            priority_level = "CRITICAL" if pred_class == "INDUSTRIAL_FIRE" else ("HIGH" if priority_score >= 70 else "MEDIUM")

            if not assessment:
                assessment = EventAssessment(
                    event_id=event.id,
                    classification=pred_class,
                    confidence_score=float(pred_prob),
                    confidence_type="ml_probability",
                    priority_score=priority_score,
                    priority_level=priority_level,
                    explanation=[f"Autonomous ML prediction: {pred_class} with probability {pred_prob:.2f}"],
                    evidence_factors=classification_result.get("evidence_factors", []),
                    model_type="xgboost",
                    model_version=classifier.model_version,
                    feature_schema_version="v2.0",
                    prediction_timestamp=datetime.now(timezone.utc),
                    feature_snapshot=feat_safe
                )
                db.add(assessment)
            else:
                assessment.classification = pred_class
                assessment.confidence_score = float(pred_prob)
                assessment.priority_score = priority_score
                assessment.priority_level = priority_level
                assessment.model_version = classifier.model_version
                assessment.evidence_factors = classification_result.get("evidence_factors", [])
                assessment.prediction_timestamp = datetime.now(timezone.utc)
                assessment.feature_snapshot = feat_safe
            
            db.commit()

            cls._record_stage_success(db, stage_ml, time.perf_counter() - t0, classification_result)
            stages_executed.append("CLASSIFICATION")
        except Exception as e:
            cls._record_stage_failure(db, stage_ml, time.perf_counter() - t0, e)
            logger.error(f"Stage CLASSIFICATION failed: {e}")
            raise

        # Stage 6: Autonomous Risk Calculation
        t0 = time.perf_counter()
        stage_risk = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "RISK_ASSESSMENT")
        risk_result = {}
        try:
            pred_class = classification_result.get("classification", "UNKNOWN")
            risk_eval = RiskEngine.evaluate_risk(
                features=feat_safe,
                classification=pred_class,
                spatial_context=spatial_context,
                temporal_data=temporal_data,
                satellite_data=satellite_data
            )
            risk_score = risk_eval["risk_score"]
            risk_level = risk_eval["risk_level"]

            # Persist RiskAssessment
            risk_rec = db.query(RiskAssessment).filter(RiskAssessment.event_id == event.id).first()
            if not risk_rec:
                risk_rec = RiskAssessment(
                    event_id=event.id,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    risk_model_version=risk_eval["risk_model_version"],
                    breakdown_json=risk_eval["breakdown"],
                    input_snapshot_json=risk_eval["input_snapshot"],
                    calculated_at=datetime.now(timezone.utc)
                )
                db.add(risk_rec)
            else:
                risk_rec.risk_score = risk_score
                risk_rec.risk_level = risk_level
                risk_rec.breakdown_json = risk_eval["breakdown"]
                risk_rec.calculated_at = datetime.now(timezone.utc)
            db.commit()

            risk_result = {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "breakdown": risk_eval["breakdown"]
            }
            cls._record_stage_success(db, stage_risk, time.perf_counter() - t0, risk_result)
            stages_executed.append("RISK_ASSESSMENT")
        except Exception as e:
            cls._record_stage_failure(db, stage_risk, time.perf_counter() - t0, e)
            logger.error(f"Stage RISK_ASSESSMENT failed: {e}")
            raise

        # Stage 7: Thermal Incident Correlation
        t0 = time.perf_counter()
        stage_inc = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "INCIDENT_CORRELATION")
        incident = None
        try:
            incident = IncidentCorrelator.correlate_event(
                db=db,
                event=event,
                classification=classification_result.get("classification", "UNKNOWN"),
                risk_score=risk_result.get("risk_score", 0.0),
                risk_level=risk_result.get("risk_level", "LOW"),
                spatial_context=spatial_context,
                correlation_id=correlation_id
            )
            cls._record_stage_success(db, stage_inc, time.perf_counter() - t0, {
                "incident_id": incident.id,
                "incident_code": incident.incident_code,
                "event_count": incident.event_count,
                "severity": incident.severity
            })
            stages_executed.append("INCIDENT_CORRELATION")
        except Exception as e:
            cls._record_stage_failure(db, stage_inc, time.perf_counter() - t0, e)
            logger.error(f"Stage INCIDENT_CORRELATION failed: {e}")
            raise

        # Stage 8: Alert Evaluation & Anti-Storm Deduplication
        t0 = time.perf_counter()
        stage_alert = cls._get_or_create_stage_run(db, job_id, event_id, correlation_id, "ALERT_EVALUATION")
        created_alerts = []
        try:
            # Check incident-level cooldown to prevent alert storms
            # If an alert was created for this incident within ALERT_COOLDOWN_MINUTES, suppress duplicate
            cooldown_cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
            existing_incident_alert = None
            if incident:
                existing_incident_alert = db.query(Alert).filter(
                    Alert.incident_id == incident.id,
                    Alert.created_at >= cooldown_cutoff
                ).first()

            if existing_incident_alert:
                logger.info(f"Suppressed duplicate alert creation: Incident {incident.incident_code} already has active alert {existing_incident_alert.alert_code}")
                cls._record_stage_success(db, stage_alert, time.perf_counter() - t0, {
                    "alert_count": 0,
                    "suppressed_by_incident": incident.incident_code,
                    "existing_alert_code": existing_incident_alert.alert_code
                })
            else:
                triggered = AlertEngine.evaluate_event_alerts(
                    db=db,
                    event=event,
                    risk_data={"risk_score": risk_result.get("risk_score", 0.0), "risk_level": risk_result.get("risk_level", "LOW")},
                    classification=classification_result.get("classification", "UNKNOWN"),
                    spatial_context=spatial_context,
                    temporal_data=temporal_data,
                    satellite_data=satellite_data
                )
                for al in triggered:
                    if incident:
                        al.incident_id = incident.id
                    created_alerts.append(al.alert_code)
                db.commit()

                cls._record_stage_success(db, stage_alert, time.perf_counter() - t0, {
                    "alert_count": len(created_alerts),
                    "alert_codes": created_alerts
                })
            stages_executed.append("ALERT_EVALUATION")
        except Exception as e:
            cls._record_stage_failure(db, stage_alert, time.perf_counter() - t0, e)
            logger.error(f"Stage ALERT_EVALUATION failed: {e}")
            raise

        # Stage 9: Audit Trail
        audit_log = AutonomousAuditLog(
            correlation_id=correlation_id,
            action="PIPELINE_EVENT_COMPLETED",
            source="AUTONOMOUS_PIPELINE",
            event_id=event.id,
            incident_id=incident.id if incident else None,
            new_value={
                "classification": classification_result.get("classification"),
                "risk_score": risk_result.get("risk_score"),
                "risk_level": risk_result.get("risk_level"),
                "alerts": created_alerts
            },
            model_version=classification_result.get("model_version", "xgb-v1"),
            details_json={"stages_executed": stages_executed}
        )
        db.add(audit_log)
        db.commit()

        # Stage 10: Real-Time WebSocket Telemetry Broadcast
        try:
            # 1. thermal_event.updated / created
            await ws_manager.broadcast("thermal_event.created", {
                "id": event.id,
                "event_code": f"INF-2026-{event.id:06d}",
                "latitude": event.latitude,
                "longitude": event.longitude,
                "frp": event.frp,
                "confidence": event.confidence,
                "detected_at": event.detected_at.isoformat() if event.detected_at else None,
                "classification": classification_result.get("classification"),
                "risk_score": risk_result.get("risk_score"),
                "risk_level": risk_result.get("risk_level"),
                "status": event.status,
                "incident_id": incident.id if incident else None,
                "incident_code": incident.incident_code if incident else None
            })

            # 2. incident.updated if exists
            if incident:
                await ws_manager.broadcast("incident.updated", {
                    "incident_id": incident.id,
                    "incident_code": incident.incident_code,
                    "event_count": incident.event_count,
                    "peak_frp": incident.peak_frp,
                    "mean_frp": incident.mean_frp,
                    "risk_score": incident.risk_score,
                    "severity": incident.severity,
                    "classification": incident.classification,
                    "centroid_latitude": incident.centroid_latitude,
                    "centroid_longitude": incident.centroid_longitude
                })

            # 3. alert.created if any
            for ac in created_alerts:
                await ws_manager.broadcast("alert.created", {
                    "alert_code": ac,
                    "event_id": event.id,
                    "incident_id": incident.id if incident else None,
                    "incident_code": incident.incident_code if incident else None,
                    "risk_score": risk_result.get("risk_score"),
                    "risk_level": risk_result.get("risk_level"),
                    "classification": classification_result.get("classification")
                })
        except Exception as ws_err:
            logger.debug(f"WebSocket broadcast non-blocking error: {ws_err}")

        pipeline_result["classification"] = classification_result.get("classification")
        pipeline_result["risk_score"] = risk_result.get("risk_score")
        pipeline_result["risk_level"] = risk_result.get("risk_level")
        pipeline_result["incident_code"] = incident.incident_code if incident else None
        pipeline_result["alert_code"] = created_alerts[0] if created_alerts else None
        pipeline_result["stages_executed"] = stages_executed

        return pipeline_result

    @classmethod
    async def run_autonomous_cycle(cls, db: Session, use_demo: bool = False) -> Dict[str, Any]:
        """
        Executes a complete autonomous cycle:
          1. Incremental FIRMS ingestion
          2. Runs multi-stage pipeline on all new events
          3. Emits job status updates
        """
        correlation_id = f"CORR-{uuid.uuid4().hex[:12].upper()}"
        job = PipelineJob(
            correlation_id=correlation_id,
            job_type="FIRMS_AUTONOMOUS_PIPELINE",
            source="DEMO_NASA_FIRMS" if use_demo else "NASA_FIRMS",
            status="RUNNING",
            started_at=datetime.now(timezone.utc)
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        t_start = time.perf_counter()
        logger.info(f"Starting autonomous pipeline cycle [{correlation_id}], job_id={job.id}")

        await ws_manager.broadcast("job.started", {
            "job_id": job.id,
            "correlation_id": correlation_id,
            "job_type": job.job_type,
            "source": job.source
        })

        try:
            from app.services.firms.ingestion import FirmsIngestionService
            ingestion_service = FirmsIngestionService()
            ingest_res = await ingestion_service.ingest_incremental(db, use_demo=use_demo)

            job.records_received = ingest_res.get("fetched", 0)
            job.records_inserted = ingest_res.get("inserted", 0)
            job.records_skipped = ingest_res.get("skipped", 0)
            job.records_failed = ingest_res.get("rejected", 0)
            db.commit()

            new_event_ids: List[int] = ingest_res.get("inserted_event_ids", [])
            # Also discover any unassessed events in the database to guarantee total pipeline coverage
            unassessed = db.query(ThermalEvent.id).outerjoin(
                EventAssessment, ThermalEvent.id == EventAssessment.event_id
            ).filter(EventAssessment.id.is_(None)).all()
            target_ids = list(dict.fromkeys(new_event_ids + [r[0] for r in unassessed]))
            logger.info(f"Incremental ingestion fetched {job.records_received} records. Processing {len(target_ids)} events.")

            succeeded = 0
            failed = 0
            for ev_id in target_ids:
                try:
                    await cls.process_event(
                        db=db,
                        event_id=ev_id,
                        job_id=job.id,
                        correlation_id=correlation_id
                    )
                    succeeded += 1
                except Exception as ev_err:
                    failed += 1
                    logger.error(f"Event {ev_id} failed pipeline processing: {ev_err}")

            job.records_processed = len(target_ids)
            job.records_succeeded = succeeded
            job.records_failed = failed
            job.duration_seconds = round(time.perf_counter() - t_start, 2)
            job.status = "COMPLETED" if failed == 0 else "PARTIAL"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            await ws_manager.broadcast("job.completed", {
                "job_id": job.id,
                "correlation_id": correlation_id,
                "status": job.status,
                "records_succeeded": succeeded,
                "records_failed": failed,
                "duration_seconds": job.duration_seconds
            })

            return {
                "status": job.status,
                "job_id": job.id,
                "correlation_id": correlation_id,
                "records_received": job.records_received,
                "records_inserted": job.records_inserted,
                "records_succeeded": succeeded,
                "records_failed": failed,
                "duration_seconds": job.duration_seconds
            }

        except Exception as e:
            job.status = "FAILED"
            job.error_message = str(e)
            job.duration_seconds = round(time.perf_counter() - t_start, 2)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            await ws_manager.broadcast("job.failed", {
                "job_id": job.id,
                "correlation_id": correlation_id,
                "error": str(e)
            })

            logger.error(f"Autonomous cycle failed: {e}")
            return {
                "status": "FAILED",
                "job_id": job.id,
                "correlation_id": correlation_id,
                "error": str(e),
                "duration_seconds": job.duration_seconds
            }

    @classmethod
    async def run_demo_pipeline(
        cls,
        db: Session,
        latitude: float = 22.4630,
        longitude: float = 70.0710,
        frp: float = 425.0,
        brightness_temperature: float = 388.4,
        satellite: str = "VIIRS_NPP",
        confidence: float = 95.0
    ) -> Dict[str, Any]:
        """
        Demo Mode Pipeline Trigger (Section 40).
        Creates a labeled DEMO observation and flows through the entire autonomous pipeline in real-time.
        """
        correlation_id = f"DEMO-{uuid.uuid4().hex[:10].upper()}"
        job = PipelineJob(
            correlation_id=correlation_id,
            job_type="DEMO_PIPELINE",
            source="DEMO_NASA_FIRMS",
            status="RUNNING",
            records_received=1,
            records_inserted=1,
            started_at=datetime.now(timezone.utc)
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        t_start = time.perf_counter()

        now_utc = datetime.now(timezone.utc)
        # Create marked DEMO observation
        demo_event = ThermalEvent(
            source="DEMO_NASA_FIRMS",
            source_id=f"DEMO_{int(time.time())}",
            latitude=latitude,
            longitude=longitude,
            geometry=f"SRID=4326;POINT({longitude} {latitude})",
            detected_at=now_utc,
            acquired_at=now_utc,
            satellite=satellite,
            instrument="VIIRS",
            confidence=confidence,
            frp=frp,
            brightness_temperature=brightness_temperature,
            day_night="D",
            status="NEW"
        )
        db.add(demo_event)
        db.commit()
        db.refresh(demo_event)

        res = await cls.process_event(
            db=db,
            event_id=demo_event.id,
            job_id=job.id,
            correlation_id=correlation_id
        )

        job.records_processed = 1
        job.records_succeeded = 1
        job.status = "COMPLETED"
        job.duration_seconds = round(time.perf_counter() - t_start, 2)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        res["job_id"] = job.id
        res["duration_seconds"] = job.duration_seconds
        return res
