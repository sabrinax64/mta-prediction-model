# Prediction (not started)

This is where the actual "predict delays before MTA announces them" model
will live, once there's enough `delay_observations` history in Postgres to
train against.

Rough shape for later, not decided yet:
- A feature set per (route, stop, time-of-day, day-of-week) window.
- Start with something simple (e.g. rolling median delay per route/hour) as a
  baseline before reaching for anything heavier.
- Needs at least a few weeks of continuous ingestion to have enough signal —
  no point starting this until the ingestion/storage side has been running
  unattended for a while.
