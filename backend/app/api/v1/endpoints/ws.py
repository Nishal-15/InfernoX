import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """
    Real-Time WebSocket Stream for Mission Control.
    Delivers live thermal detection events, ML classification updates,
    risk score revisions, incident correlations, alerts, and system health status.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep socket alive and receive client heartbeats/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)
