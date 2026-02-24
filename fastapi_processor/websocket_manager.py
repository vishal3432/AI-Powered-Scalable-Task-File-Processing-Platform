"""
WebSocket Connection Manager
Broadcasts "Processing Complete" alerts to connected clients.
"""
from typing import Dict, List
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    """
    Manages WebSocket connections per user.
    When a background task finishes, it notifies the user's connected clients.
    """

    def __init__(self):
        # user_id -> list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"[WS] User {user_id} connected. Total connections: {self.total_connections}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"[WS] User {user_id} disconnected.")

    async def send_to_user(self, user_id: int, message: dict):
        """Send a message to ALL connections for a specific user."""
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.append(connection)
            # Clean up dead connections
            for dead in dead_connections:
                self.active_connections[user_id].remove(dead)

    async def broadcast(self, message: dict):
        """Broadcast to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    @property
    def total_connections(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())


# Singleton instance
manager = ConnectionManager()
