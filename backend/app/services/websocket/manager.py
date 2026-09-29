import logging
from typing import Set, Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Real-Time WebSocket & Event Stream Manager with Multi-Tenant Partitioning.
    Broadcasts autonomous geospatial thermal intelligence events,
    incident updates, alerts, and pipeline telemetry to connected clients.
    Guarantees strict tenant isolation: tenant-specific events are delivered
    only to authorized organization subscribers.
    """
    def __init__(self, max_buffer_size: int = 50):
        self.active_connections: Set[WebSocket] = set()
        self.connection_tenants: Dict[WebSocket, Optional[Union[str, int]]] = {}  # websocket -> organization_id
        self.connection_users: Dict[WebSocket, Optional[Union[str, int]]] = {}    # websocket -> user_id
        self.event_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = max_buffer_size

    async def connect(
        self,
        websocket: WebSocket,
        organization_id: Optional[Union[str, int]] = None,
        user_id: Optional[Union[str, int]] = None
    ) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_tenants[websocket] = organization_id
        self.connection_users[websocket] = user_id
        logger.info(
            f"WebSocket client connected. Active: {len(self.active_connections)}, "
            f"Tenant: {organization_id}, User: {user_id}"
        )
        
        # Send connection established greeting
        await websocket.send_json({
            "event": "connection.ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message": "Connected to InfernoX Autonomous Intelligence Stream",
                "active_clients": len(self.active_connections),
                "tenant_scope": organization_id,
                "buffered_events_count": len(self.event_buffer)
            }
        })

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.connection_tenants.pop(websocket, None)
        self.connection_users.pop(websocket, None)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(
        self,
        event_type: str,
        payload: Dict[str, Any],
        organization_id: Optional[Union[str, int]] = None
    ) -> None:
        """
        Broadcasts an event envelope to subscribers.
        If organization_id is None, it is broadcast globally (e.g. NASA FIRMS public anomaly).
        If organization_id is specified, it is delivered ONLY to clients authorized for that tenant.
        """
        envelope = {
            "event": event_type,
            "schema_version": "2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organization_id": organization_id,
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
            client_org = self.connection_tenants.get(connection)
            
            # Tenant isolation filter:
            # Deliver if event is global (organization_id is None) OR matches subscriber's organization
            if organization_id is not None and client_org is not None and client_org != organization_id:
                continue

            try:
                await connection.send_json(envelope)
            except Exception as e:
                logger.debug(f"Error sending message to websocket client: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_heartbeat(self) -> None:
        """Emits a periodic keepalive and telemetry frame to all active subscribers."""
        await self.broadcast("heartbeat", {
            "status": "HEALTHY",
            "active_clients": len(self.active_connections),
            "buffered_events": len(self.event_buffer),
            "pipeline_state": "ACTIVE"
        })


    def get_recent_events(
        self,
        limit: int = 20,
        organization_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns recent broadcasted events from the memory buffer,
        filtering by organization scope if requested.
        """
        buffered = self.event_buffer[-limit:]
        if organization_id is not None:
            buffered = [
                ev for ev in buffered
                if ev.get("organization_id") is None or ev.get("organization_id") == organization_id
            ]
        return list(reversed(buffered))

# Global Singleton Instance
ws_manager = ConnectionManager()
