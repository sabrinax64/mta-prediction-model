-- Reference tables, refreshed whenever the static GTFS feed is reloaded.
CREATE TABLE IF NOT EXISTS stops (
    stop_id TEXT PRIMARY KEY,
    stop_name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    parent_station TEXT
);

CREATE TABLE IF NOT EXISTS routes (
    route_id TEXT PRIMARY KEY,
    route_long_name TEXT,
    route_color TEXT
);

-- One row per (train, poll). This is the time-series table the prediction
-- model will eventually train on, and what the live map renders from.
CREATE TABLE IF NOT EXISTS delay_observations (
    observed_at TIMESTAMPTZ NOT NULL,
    route_id TEXT NOT NULL,
    trip_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    stop_id TEXT NOT NULL,
    predicted_arrival TIMESTAMPTZ NOT NULL,
    delay_seconds INTEGER
);

-- Converts delay_observations into a TimescaleDB hypertable, partitioned by
-- time. No-op (and safe to re-run) if the extension isn't installed, but the
-- docker-compose.yml here uses the timescaledb/timescaledb image so it is.
SELECT create_hypertable('delay_observations', 'observed_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_delay_observations_trip
    ON delay_observations (trip_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_delay_observations_route
    ON delay_observations (route_id, observed_at DESC);
