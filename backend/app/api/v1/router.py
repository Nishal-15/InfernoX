from fastapi import APIRouter
import logging
from app.api.v1.endpoints import (
    events,
    data,
    facilities,
    search,
    ai,
    ingestion,
    ml,
    alerts,
    risk,
    alert_rules,
    routing,
    notifications,
    analytics,
    reports,
    system,
    incidents,
    ws
)

api_router = APIRouter()

logger = logging.getLogger(__name__)

@api_router.get("/health")
def health_check():
    """
    Check if the API is running correctly.
    """
    logger.info("Health check accessed.")
    return {
        "status": "ok",
        "service": "thermal-intelligence-api",
        "version": "1.0.0"
    }

api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(data.router, prefix="/data", tags=["data"])
api_router.include_router(facilities.router, prefix="/facilities", tags=["facilities"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(ml.router, prefix="/ml", tags=["ml"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(risk.router, tags=["risk"])
api_router.include_router(alert_rules.router, prefix="/alert-rules", tags=["alert-rules"])
api_router.include_router(routing.router, tags=["routing"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])


