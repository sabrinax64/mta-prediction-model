"""Broadcasts the latest train snapshot to every connected browser.

Push-based instead of client polling: the ingestion loop calls `broadcast()`
once per 30s cycle, and every connected socket gets the update immediately —
no client has to ask for it.
"""
from __future__ import annotations

import dataclasses
import json
import logging

from fastapi import WebSocket

from backend.delay.snapshot import TrainObservation

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, observations: list[TrainObservation]) -> None:
        if not self._connections:
            return
        payload = json.dumps(
            {"trains": [dataclasses.asdict(o) for o in observations]}
        )
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
