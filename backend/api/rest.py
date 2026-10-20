"""Plain REST endpoints for static-ish metadata and historical lookback.
Live train state is pushed over the WebSocket (see ws.py), not polled here.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from backend.storage.repository import recent_delays_for_route

router = APIRouter()


@router.get("/api/routes/{route_id}/recent_delays")
async def recent_delays(route_id: str, request: Request, minutes: int = 60):
    pool = request.app.state.db_pool
    rows = await recent_delays_for_route(pool, route_id, minutes=minutes)
    return [dict(row) for row in rows]


@router.get("/api/health")
async def health():
    return {"status": "ok"}
