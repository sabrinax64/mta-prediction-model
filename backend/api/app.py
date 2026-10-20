"""FastAPI app: wires up the DB pool, loads the static schedule into memory,
starts the 30s ingestion loop as a background task, and serves the REST +
WebSocket + static frontend.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from backend.api.rest import router as rest_router
from backend.api.ws import manager
from backend.gtfs_static.download import DATA_DIR, download_and_extract
from backend.gtfs_static.load import build_schedule_index
from backend.ingestion.poller import run_poll_loop
from backend.storage.db import apply_schema, close_pool, get_pool
from backend.storage.repository import replace_reference_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    await apply_schema()
    app.state.db_pool = pool

    gtfs_dir = DATA_DIR
    if not (gtfs_dir / "stops.txt").exists():
        logger.info("no static GTFS on disk yet, downloading...")
        gtfs_dir = download_and_extract()

    logger.info("building in-memory schedule index...")
    app.state.schedule_index = build_schedule_index(gtfs_dir)
    await replace_reference_data(pool, gtfs_dir)

    stop_event = asyncio.Event()
    poll_task = asyncio.create_task(
        run_poll_loop(pool, app.state.schedule_index, manager.broadcast, stop_event)
    )

    yield

    stop_event.set()
    await poll_task
    await close_pool()


app = FastAPI(title="MTA Delay Tracker", lifespan=lifespan)
app.include_router(rest_router)


@app.websocket("/ws/live")
async def live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from the client, just keep the socket
            # open until it disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
