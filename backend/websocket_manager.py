"""
WebSocket Manager
Per-room connection management with presence tracking and broadcast.

Adapted from Ruflo pattern: SwarmCoordinator's eventBus + topology-aware messaging.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional, Any, Callable
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentConnection:
    """Represents an agent's WebSocket connection in a room."""
    agent_id: str
    websocket: WebSocket
    room_id: str
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    status: str = "online"  # online, away, busy
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketManager:
    """
    Scalable WebSocket manager for AgentVerse rooms.
    - Per-room connection isolation
    - Presence tracking with heartbeat
    - Typed message routing
    - Broadcast / unicast / roomcast
    """

    def __init__(self):
        # room_id -> {agent_id -> AgentConnection}
        self._rooms: Dict[str, Dict[str, AgentConnection]] = {}
        # Global lock for room mutations
        self._lock = asyncio.Lock()
        # Event handlers: message_type -> [handler]
        self._handlers: Dict[str, list] = {}
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start background tasks (cleanup, heartbeat)."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Gracefully close all connections and stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        async with self._lock:
            for room_id, agents in list(self._rooms.items()):
                for conn in list(agents.values()):
                    try:
                        await conn.websocket.close(code=1001)
                    except Exception:
                        pass
                agents.clear()
            self._rooms.clear()
        logger.info("WebSocket manager stopped")

    # ── Connection Management ─────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Accept connection and register agent in room."""
        await websocket.accept()

        async with self._lock:
            if room_id not in self._rooms:
                self._rooms[room_id] = {}

            # Disconnect existing connection for this agent (prevent duplicates)
            if agent_id in self._rooms[room_id]:
                old = self._rooms[room_id][agent_id]
                try:
                    await old.websocket.close(code=1008)
                except Exception:
                    pass

            conn = AgentConnection(
                agent_id=agent_id,
                websocket=websocket,
                room_id=room_id,
                metadata=metadata or {},
            )
            self._rooms[room_id][agent_id] = conn

        logger.info("Agent %s connected to room %s", agent_id, room_id)

        # Announce presence
        await self.broadcast_to_room(
            room_id,
            {
                "type": "presence",
                "agent_id": agent_id,
                "status": "online",
                "room_id": room_id,
                "timestamp": asyncio.get_event_loop().time(),
            },
            exclude=agent_id,
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        room_id: str,
        agent_id: str,
    ) -> None:
        """Remove agent from room and announce departure."""
        async with self._lock:
            room = self._rooms.get(room_id, {})
            if agent_id in room and room[agent_id].websocket == websocket:
                del room[agent_id]
                if not room:
                    del self._rooms[room_id]

        logger.info("Agent %s disconnected from room %s", agent_id, room_id)

        await self.broadcast_to_room(
            room_id,
            {
                "type": "presence",
                "agent_id": agent_id,
                "status": "offline",
                "room_id": room_id,
                "timestamp": asyncio.get_event_loop().time(),
            },
            exclude=agent_id,
        )

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude: Optional[str] = None,
    ) -> int:
        """Broadcast message to all agents in a room. Returns number of recipients."""
        sent = 0
        disconnected: list = []

        async with self._lock:
            room = self._rooms.get(room_id, {})
            connections = list(room.values())

        for conn in connections:
            if exclude and conn.agent_id == exclude:
                continue
            try:
                await conn.websocket.send_json(message)
                sent += 1
            except Exception:
                disconnected.append((room_id, conn.agent_id))

        # Cleanup failed connections
        for rid, aid in disconnected:
            async with self._lock:
                r = self._rooms.get(rid, {})
                if aid in r and r[aid].websocket.client_state.DISCONNECTED:
                    del r[aid]

        return sent

    async def send_to_agent(
        self,
        room_id: str,
        agent_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """Send message to a specific agent. Returns True if delivered."""
        async with self._lock:
            conn = self._rooms.get(room_id, {}).get(agent_id)

        if not conn:
            return False
        try:
            await conn.websocket.send_json(message)
            return True
        except Exception:
            return False

    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """Broadcast to every connected agent across all rooms."""
        sent = 0
        async with self._lock:
            rooms = {k: list(v.values()) for k, v in self._rooms.items()}

        for room_id, connections in rooms.items():
            for conn in connections:
                try:
                    await conn.websocket.send_json(message)
                    sent += 1
                except Exception:
                    pass
        return sent

    # ── Presence & Queries ────────────────────────────────────────────────────

    def get_room_presence(self, room_id: str) -> Dict[str, Dict[str, Any]]:
        """Get current presence map for a room."""
        room = self._rooms.get(room_id, {})
        return {
            aid: {
                "status": conn.status,
                "connected_at": conn.connected_at,
                "last_ping": conn.last_ping,
                "metadata": conn.metadata,
            }
            for aid, conn in room.items()
        }

    def get_agent_connection(
        self, room_id: str, agent_id: str
    ) -> Optional[AgentConnection]:
        """Get connection info for a specific agent."""
        return self._rooms.get(room_id, {}).get(agent_id)

    def active_rooms(self) -> list:
        """List all active room IDs."""
        return list(self._rooms.keys())

    def total_connections(self) -> int:
        """Total number of active connections across all rooms."""
        return sum(len(r) for r in self._rooms.values())

    # ── Handlers ──────────────────────────────────────────────────────────────

    def on(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def handle_message(
        self, room_id: str, agent_id: str, data: Dict[str, Any]
    ) -> None:
        """Route incoming message to registered handlers."""
        msg_type = data.get("type", "chat")
        handlers = self._handlers.get(msg_type, [])

        for handler in handlers:
            try:
                await handler(room_id, agent_id, data)
            except Exception as e:
                logger.error("Handler error for %s: %s", msg_type, e)

    # ── Background Tasks ──────────────────────────────────────────────────────

    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale connections."""
        while True:
            try:
                await asyncio.sleep(60)
                now = asyncio.get_event_loop().time()
                stale_threshold = 300  # 5 minutes without ping

                async with self._lock:
                    for room_id in list(self._rooms.keys()):
                        room = self._rooms[room_id]
                        stale = [
                            aid
                            for aid, conn in room.items()
                            if now - conn.last_ping > stale_threshold
                        ]
                        for aid in stale:
                            del room[aid]
                            logger.info("Cleaned up stale agent %s", aid)
                        if not room:
                            del self._rooms[room_id]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error: %s", e)

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping to all clients for keepalive."""
        while True:
            try:
                await asyncio.sleep(30)
                async with self._lock:
                    rooms = {k: list(v.values()) for k, v in self._rooms.items()}

                for room_id, connections in rooms.items():
                    for conn in connections:
                        try:
                            await conn.websocket.send_json({"type": "ping"})
                            conn.last_ping = asyncio.get_event_loop().time()
                        except Exception:
                            pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat loop error: %s", e)


# ── Global Instance ─────────────────────────────────────────────────────────
ws_manager = WebSocketManager()
