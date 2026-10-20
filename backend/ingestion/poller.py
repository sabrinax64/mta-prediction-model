"""The 30-second loop: poll every subway feed, diff against the schedule,
persist the observations, and hand the latest snapshot to whoever wants to
broadcast it (the WebSocket manager, via a callback — kept decoupled here so
this module has no dependency on FastAPI/the API layer).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

import asyncpg
import httpx

from backend.config import POLL_INTERVAL_SECONDS, SUBWAY_FEEDS
from backend.delay.models import ScheduleIndex
from backend.delay.snapshot import TrainObservation, build_observations
from backend.ingestion.feeds import fetch_feed
from backend.storage.repository import insert_observations

logger = logging.getLogger(__name__)

BroadcastFn = Callable[[list[TrainObservation]], Awaitable[None]]


async def poll_once(
    client: httpx.AsyncClient, index: ScheduleIndex
) -> list[TrainObservation]:
    observed_at = int(time.time())

    async def fetch_one(name: str, url: str):
        try:
            feed = await fetch_feed(client, url)
            return feed.entity
        except Exception:
            logger.exception("failed to fetch feed %s", name)
            return []

    results = await asyncio.gather(
        *(fetch_one(name, url) for name, url in SUBWAY_FEEDS.items())
    )
    all_entities = [entity for entities in results for entity in entities]
    return build_observations(index, all_entities, observed_at)


async def run_poll_loop(
    pool: asyncpg.Pool,
    index: ScheduleIndex,
    broadcast: BroadcastFn,
    stop_event: asyncio.Event,
) -> None:
    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            start = time.monotonic()
            try:
                observations = await poll_once(client, index)
                logger.info("polled %d train observations", len(observations))
                await insert_observations(pool, observations)
                await broadcast(observations)
            except Exception:
                logger.exception("poll cycle failed")

            elapsed = time.monotonic() - start
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=max(0.0, POLL_INTERVAL_SECONDS - elapsed)
                )
            except asyncio.TimeoutError:
                pass
