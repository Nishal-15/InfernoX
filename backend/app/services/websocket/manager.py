import json
import logging
from typing import Set, Dict, Any, List
from datetime import datetime, timezone
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Real-Time WebSocket & Event Stream Manager.
    Broadcasts autonomous geospatial thermal intelligence events,
    incident updates, alerts, and pipeline telemetry to connected clients.
    Maintains an in-memory event buffer for replay on initial connection.
    """
    def __init__(self, max_buffer_size: int = 50):
        self.active_connections: Set[WebSocket] = set()
        self.event_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = max_buffer_size

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")
        
        # Send connection established greeting and recent buffer
        await websocket.send_json({
            "event": "connection.ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message": "Connected to InfernoX Autonomous Intelligence Stream",
                "active_clients": len(self.active_connections),
                "buffered_events_count": len(self.event_buffer)
            }
        })

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Broadcasts an event envelope to all active subscribers.
        Silently cleans up any dead/broken sockets.
        """
        envelope = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }

        # Append to circular buffer
        self.event_buffer.append(envelope)
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop(0)

        if not self.active_connections:
            return

        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(envelope)
            except Exception as e:
                logger.debug(f"Error sending message to websocket client: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns recent broadcasted events from the memory buffer."""
        return list(reversed(self.event_buffer[-limit:]))

# Global Singleton Instance
ws_manager = ConnectionManager()
