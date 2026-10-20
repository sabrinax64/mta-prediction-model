"""Fetch + decode a single GTFS-Realtime subway feed."""
from __future__ import annotations

import httpx
from google.transit import gtfs_realtime_pb2

from backend.config import MTA_API_KEY


async def fetch_feed(client: httpx.AsyncClient, url: str) -> gtfs_realtime_pb2.FeedMessage:
    headers = {"x-api-key": MTA_API_KEY} if MTA_API_KEY else {}
    response = await client.get(url, headers=headers, timeout=15.0)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed
