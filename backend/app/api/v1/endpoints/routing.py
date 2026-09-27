from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.thermal_event import ThermalEvent
from app.models.risk_alert import ResponseContact
from app.schemas.risk_alert import ResponseContactCreate, ResponseContactResponse
from app.services.routing.service import ResponseRoutingService
from app.api.v1.endpoints.events import _query_nearby_facilities
from app.services.classification.classifier import PrototypeClassifier
from app.services.ml.classifier import MLClassifier
from app.services.features.engineer import FeatureEngineer
from app.services.temporal.analyzer import TemporalAnalyzer

router = APIRouter()


@router.get("/events/{event_id}/routing")
def get_event_routing(event_id: int, db: Session = Depends(get_db)):
    """
    Evaluates and recommends the response authority routing for a thermal event.
    """
    event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Thermal event {event_id} not found")

    facs = _query_nearby_facilities(db, event.longitude, event.latitude, 5000.0)
    nearest = facs[0] if facs else None

    # Derive classification
    temp = TemporalAnalyzer().analyze_event(db, event.id)
    features = FeatureEngineer.extract_features(
        event,
        spatial_context={"nearest_facility": nearest, "distance_meters": nearest["distance_meters"] if nearest else None},
        temporal_data=temp
    )
    try:
        clf = MLClassifier().classify(features)
        classification = clf["classification"]
    except Exception:
        clf = PrototypeClassifier().classify(features)
        classification = clf["classification"]

    routing = ResponseRoutingService.resolve_routing(
        db=db,
        classification=classification,
        severity="HIGH" if event.frp > 50 else "MODERATE",
        facility_info=nearest
    )

    return {
        "event_id": event.id,
        "classification": classification,
        "routing": routing
    }


@router.get("/response-contacts", response_model=List[ResponseContactResponse])
def list_response_contacts(
    department_type: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List configured emergency and operational response contacts.
    """
    query = db.query(ResponseContact).filter(ResponseContact.enabled == True)
    if department_type:
        query = query.filter(ResponseContact.department_type == department_type.upper())
    if jurisdiction:
        query = query.filter(ResponseContact.jurisdiction.ilike(f"%{jurisdiction}%"))
    return query.order_by(ResponseContact.id.asc()).all()


@router.post("/response-contacts", response_model=ResponseContactResponse, status_code=201)
def create_response_contact(contact_in: ResponseContactCreate, db: Session = Depends(get_db)):
    """
    Add a new response contact to the authority routing directory.
    """
    contact = ResponseContact(
        organization_name=contact_in.organization_name,
        department_type=contact_in.department_type.upper(),
        jurisdiction=contact_in.jurisdiction,
        contact_type=contact_in.contact_type.upper(),
        contact_value=contact_in.contact_value,
        enabled=contact_in.enabled,
        verified=contact_in.verified,
        last_verified_at=datetime.now(timezone.utc) if contact_in.verified else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
