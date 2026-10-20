"""Central configuration, loaded from environment variables (see .env.example)."""
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

NY_TZ = ZoneInfo("America/New_York")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://mta:mta@localhost:5432/mta"
)

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))

# MTA dropped the API-key requirement for these endpoints in 2024 — they are
# plain public HTTP GETs. MTA_API_KEY is kept here (and sent as the `x-api-key`
# header when set) in case that ever changes back; leave it unset otherwise.
MTA_API_KEY = os.getenv("MTA_API_KEY", "")

GTFS_STATIC_URL = os.getenv(
    "GTFS_STATIC_URL",
    "http://web.mta.info/developers/data/nyct/subway/google_transit.zip",
)

# One GTFS-RT feed per group of subway lines that MTA bundles together.
SUBWAY_FEEDS = {
    "123456S": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "ACE": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "BDFM": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "G": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "JZ": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "NQRW": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "L": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "SIR": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}
