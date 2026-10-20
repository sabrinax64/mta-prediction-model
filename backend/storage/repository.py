"""Read/write helpers around the Postgres pool."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import asyncpg

from backend.delay.snapshot import TrainObservation
from backend.gtfs_static.load import iter_routes, iter_stops


async def replace_reference_data(pool: asyncpg.Pool, gtfs_dir: Path) -> None:
    """Wipes and reloads the stops/routes reference tables."""
    stops = list(iter_stops(gtfs_dir))
    routes = list(iter_routes(gtfs_dir))

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("TRUNCATE stops, routes")
            await conn.copy_records_to_table(
                "stops",
                records=[(s["stop_id"], s["stop_name"], s["lat"], s["lon"], s["parent_station"]) for s in stops],
                columns=["stop_id", "stop_name", "lat", "lon", "parent_station"],
            )
            await conn.copy_records_to_table(
                "routes",
                records=[(r["route_id"], r["route_long_name"], r["route_color"]) for r in routes],
                columns=["route_id", "route_long_name", "route_color"],
            )


async def insert_observations(pool: asyncpg.Pool, observations: list[TrainObservation]) -> None:
    if not observations:
        return
    records = [
        (
            dt.datetime.fromtimestamp(o.observed_at, tz=dt.timezone.utc),
            o.route_id,
            o.trip_id,
            o.direction,
            o.current_stop_id,
            dt.datetime.fromtimestamp(o.predicted_epoch, tz=dt.timezone.utc),
            o.delay_seconds,
        )
        for o in observations
    ]
    async with pool.acquire() as conn:
        await conn.copy_records_to_table(
            "delay_observations",
            records=records,
            columns=[
                "observed_at",
                "route_id",
                "trip_id",
                "direction",
                "stop_id",
                "predicted_arrival",
                "delay_seconds",
            ],
        )


async def recent_delays_for_route(pool: asyncpg.Pool, route_id: str, minutes: int = 60):
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT observed_at, trip_id, direction, stop_id, delay_seconds
            FROM delay_observations
            WHERE route_id = $1 AND observed_at > now() - ($2 || ' minutes')::interval
            ORDER BY observed_at DESC
            """,
            route_id,
            str(minutes),
        )
