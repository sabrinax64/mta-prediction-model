"""Parse the unzipped static GTFS files.

Two consumers of this data:
  1. `build_schedule_index` -> an in-memory ScheduleIndex, held by the
     ingestion service for fast per-poll trip matching (see backend/delay/).
  2. `iter_stops` / `iter_routes` -> small reference tables written to
     Postgres, used by the REST API / frontend for display metadata.

We deliberately do NOT store trips.txt/stop_times.txt in Postgres — they're
only needed transiently for matching, and the computed scheduled time is
already captured per-observation in delay_observations.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from backend.delay.models import Service, StaticTrip, ScheduleIndex

WEEKDAY_COLUMNS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _parse_hms_to_seconds(value: str) -> int:
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def _load_services(gtfs_dir: Path) -> dict[str, Service]:
    services: dict[str, Service] = {}
    with open(gtfs_dir / "calendar.txt", newline="") as f:
        for row in csv.DictReader(f):
            weekdays = frozenset(
                i for i, col in enumerate(WEEKDAY_COLUMNS) if row[col] == "1"
            )
            services[row["service_id"]] = Service(
                service_id=row["service_id"],
                weekdays=weekdays,
                start_date=dt.datetime.strptime(row["start_date"], "%Y%m%d").date(),
                end_date=dt.datetime.strptime(row["end_date"], "%Y%m%d").date(),
            )

    calendar_dates_path = gtfs_dir / "calendar_dates.txt"
    if calendar_dates_path.exists():
        added: dict[str, set] = {}
        removed: dict[str, set] = {}
        with open(calendar_dates_path, newline="") as f:
            for row in csv.DictReader(f):
                date = dt.datetime.strptime(row["date"], "%Y%m%d").date()
                bucket = added if row["exception_type"] == "1" else removed
                bucket.setdefault(row["service_id"], set()).add(date)
        for service_id, svc in list(services.items()):
            services[service_id] = Service(
                service_id=svc.service_id,
                weekdays=svc.weekdays,
                start_date=svc.start_date,
                end_date=svc.end_date,
                added_dates=frozenset(added.get(service_id, set())),
                removed_dates=frozenset(removed.get(service_id, set())),
            )
    return services


def build_schedule_index(gtfs_dir: Path) -> ScheduleIndex:
    index = ScheduleIndex()
    index.services = _load_services(gtfs_dir)

    with open(gtfs_dir / "stops.txt", newline="") as f:
        for row in csv.DictReader(f):
            index.stops[row["stop_id"]] = (
                float(row["stop_lat"]),
                float(row["stop_lon"]),
                row["stop_name"],
            )

    with open(gtfs_dir / "trips.txt", newline="") as f:
        for row in csv.DictReader(f):
            trip_id = row["trip_id"]
            if "_" not in trip_id:
                continue
            suffix = trip_id.split("_", 1)[1]
            index.trips_by_suffix[suffix].append(
                StaticTrip(
                    trip_id=trip_id,
                    route_id=row["route_id"],
                    service_id=row["service_id"],
                    direction_id=row.get("direction_id", ""),
                )
            )

    with open(gtfs_dir / "stop_times.txt", newline="") as f:
        for row in csv.DictReader(f):
            trip_times = index.stop_times.setdefault(row["trip_id"], {})
            trip_times[row["stop_id"]] = _parse_hms_to_seconds(row["arrival_time"])

    return index


def iter_stops(gtfs_dir: Path):
    with open(gtfs_dir / "stops.txt", newline="") as f:
        for row in csv.DictReader(f):
            yield {
                "stop_id": row["stop_id"],
                "stop_name": row["stop_name"],
                "lat": float(row["stop_lat"]),
                "lon": float(row["stop_lon"]),
                "parent_station": row["parent_station"] or None,
            }


def iter_routes(gtfs_dir: Path):
    with open(gtfs_dir / "routes.txt", newline="") as f:
        for row in csv.DictReader(f):
            yield {
                "route_id": row["route_id"],
                "route_long_name": row.get("route_long_name", ""),
                "route_color": row.get("route_color", ""),
            }
