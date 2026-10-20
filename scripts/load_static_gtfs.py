"""One-off CLI: download the static GTFS feed and (re)populate the stops/routes
reference tables in Postgres. The live app also does this at startup if no
static feed is on disk yet; run this manually to force a refresh (MTA updates
the static schedule periodically, e.g. around service changes).

Usage: python -m scripts.load_static_gtfs
"""
import asyncio

from backend.gtfs_static.download import download_and_extract
from backend.storage.db import apply_schema, close_pool, get_pool
from backend.storage.repository import replace_reference_data


async def main() -> None:
    print("downloading static GTFS...")
    gtfs_dir = download_and_extract()
    print(f"extracted to {gtfs_dir}")

    pool = await get_pool()
    await apply_schema()
    await replace_reference_data(pool, gtfs_dir)
    await close_pool()
    print("reference tables (stops, routes) reloaded")


if __name__ == "__main__":
    asyncio.run(main())
