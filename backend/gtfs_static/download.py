"""Fetch and unzip MTA's static subway GTFS feed."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx

from backend.config import GTFS_STATIC_URL

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "gtfs_static"


def download_and_extract(dest_dir: Path = DATA_DIR) -> Path:
    """Downloads google_transit.zip and extracts it to dest_dir, returning it."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = client.get(GTFS_STATIC_URL)
        response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(dest_dir)
    return dest_dir
