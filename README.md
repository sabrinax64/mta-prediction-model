# MTA Subway Delay Tracker

Goal: detect subway delays faster/more accurately than the MTA's own feed
reports them, by computing delay ourselves (`predicted_arrival - scheduled_arrival`)
instead of trusting the feed's `delay` field — which MTA always sets to `0`.
Eventually: train a model on the accumulated delay history to *predict*
delays. For now, this is just the scaffold: ingestion + storage + a live map.

## Architecture

```
            every 30s
  ┌──────────────────────────────────────────┐
  │  backend/ingestion/poller.py              │
  │   - fetch all 8 MTA subway GTFS-RT feeds  │──┐
  │     concurrently (backend/ingestion/      │  │
  │     feeds.py)                             │  │
  │   - match each realtime trip to its       │  │
  │     static-schedule trip (backend/delay/  │  │
  │     matcher.py)                           │  │
  │   - compute delay_seconds (backend/delay/ │  │
  │     calculator.py)                        │  │
  └──────────────────────────────────────────┘  │
        │                          │             │
        ▼                          ▼             │
  Postgres/TimescaleDB      backend/api/ws.py ────┘
  delay_observations        broadcasts the
  (history, for the         snapshot to every
  future prediction model)  connected browser
                                   │
                                   ▼
                          frontend/ (Leaflet map,
                          WebSocket client, no polling)
```

The static GTFS schedule (`stops.txt`, `trips.txt`, `stop_times.txt`, ...) is
loaded once at startup into an in-memory `ScheduleIndex`
(`backend/delay/models.py`) so the 30s poll loop never has to hit Postgres to
do the matching — it's a pure in-memory diff. Only `stops`/`routes` (small,
mostly-static reference data) and the computed `delay_observations` rows get
written to Postgres.

## Why delay calculation needs its own matching logic

The realtime feed's trip_id (e.g. `079850_1..S15R`) is **not** the same
string as the static schedule's trip_id (e.g.
`XL0S1-1-1094-S02_079850_1..S15R`) — but it's always an exact suffix of it.
`backend/delay/matcher.py` exploits that: index static trips by that suffix,
then disambiguate using route_id + whichever service (Weekday/Saturday/Sunday)
is actually running on the realtime trip's `start_date`. This was verified
against the live feed during development, not just read off docs — see the
git history / this file's age for when. Expect ~70-80% of realtime trips to
match a static trip at any given moment; the rest are typically schedule
changes or added/supplemented service that doesn't have a static counterpart.
Unmatched trains still show up on the map, just without a delay figure.

There is also no train GPS in the subway GTFS-RT feed — only "next/current
stop + status" (`STOPPED_AT` / `IN_TRANSIT_TO` / `INCOMING_AT`). So the map
plots each train at its next stop's coordinates, not an interpolated position
along the track. That's a known, deliberate simplification — worth revisiting
once the basics are solid, not before.

## Running it

```
cp .env.example .env
docker compose up --build
```

Then open http://localhost:8000. First boot downloads the static GTFS feed
(~5MB zipped) and populates Postgres; subsequent restarts reuse the volume.

To force a refresh of the static schedule later (MTA updates it periodically):
```
docker compose run backend python -m scripts.load_static_gtfs
```

To run the backend locally against a Postgres you already have (no Docker):
```
pip install -r requirements.txt
export DATABASE_URL=postgresql://mta:mta@localhost:5432/mta
python -m backend.main
```

## Tests

```
pytest tests/
```

Covers the matcher and delay calculator with synthetic fixtures. The matching
approach itself was validated by hand against real downloaded MTA data
(live GTFS-RT feed + the static schedule) before being written up here —
worth re-doing that sanity check if MTA ever changes their trip_id format.

## Deliberately not here yet

- **Prediction model** — see `backend/prediction/README.md`. Needs real
  history in `delay_observations` first.
- **Historical backfill/retention policy** — TimescaleDB supports this well
  (compression, retention policies), but there's no data yet to make real
  decisions about it.
- **Auth, rate limiting, multi-user anything** — single-user local/learning
  project for now.
