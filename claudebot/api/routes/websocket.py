# .claudebot/api/routes/websocket.py
"""WebSocket endpoints for real-time updates"""

import asyncio
import json
import logging
from typing import Dict, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # task_id -> set of websocket connections
        self.task_connections: Dict[str, Set[WebSocket]] = {}
        # connection -> set of subscribed task_ids
        self.connection_tasks: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, task_id: str = None):
        """Connect a new WebSocket client"""
        await websocket.accept()

        # Add to global connections if no specific task
        if task_id is None:
            self.connection_tasks[websocket] = set()
        else:
            if task_id not in self.task_connections:
                self.task_connections[task_id] = set()
            self.task_connections[task_id].add(websocket)
            self.connection_tasks[websocket] = {task_id}

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        # Remove from all task subscriptions
        if websocket in self.connection_tasks:
            task_ids = self.connection_tasks.pop(websocket)
            for task_id in task_ids:
                if task_id in self.task_connections:
                    self.task_connections[task_id].discard(websocket)

    async def subscribe(self, websocket: WebSocket, task_id: str):
        """Subscribe to a specific task"""
        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(websocket)
        self.connection_tasks[websocket].add(task_id)

    async def unsubscribe(self, websocket: WebSocket, task_id: str):
        """Unsubscribe from a specific task"""
        if task_id in self.task_connections:
            self.task_connections[task_id].discard(websocket)
        if websocket in self.connection_tasks:
            self.connection_tasks[websocket].discard(task_id)

    async def broadcast_task_update(self, task_id: str, data: dict):
        """Broadcast update to all subscribers of a task"""
        if task_id not in self.task_connections:
            return

        message = json.dumps({
            "type": "task_update",
            "task_id": task_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        # Create list to avoid modification during iteration
        connections = list(self.task_connections[task_id])
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                self.task_connections[task_id].discard(connection)

    async def broadcast_global(self, data: dict):
        """Broadcast update to all connected clients"""
        message = json.dumps({
            "type": "global",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

        # Create list to avoid modification during iteration
        connections = list(self.connection_tasks.keys())
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                self.connection_tasks.pop(connection, None)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/tasks")
async def websocket_tasks(websocket: WebSocket):
    """WebSocket endpoint for task updates"""
    await manager.connect(websocket)

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
                continue

            msg_type = message.get("type")

            if msg_type == "subscribe":
                task_id = message.get("task_id")
                if task_id:
                    await manager.subscribe(websocket, task_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "task_id": task_id
                    }))

            elif msg_type == "unsubscribe":
                task_id = message.get("task_id")
                if task_id:
                    await manager.unsubscribe(websocket, task_id)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "task_id": task_id
                    }))

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        manager.disconnect(websocket)


async def notify_task_update(task_id: str, status: str, result: dict = None, error: str = None):
    """Helper function to broadcast task updates"""
    data = {
        "task_id": task_id,
        "status": status,
    }

    if result:
        data["result"] = result
    if error:
        data["error"] = error

    await manager.broadcast_task_update(task_id, data)
