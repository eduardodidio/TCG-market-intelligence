"""Scryfall bulk data downloader and streaming parser.

Downloads the 'default_cards' bulk dataset from Scryfall and parses it
into CatalogCard domain objects, filtering for paper-only English cards.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Iterator

import httpx
import structlog

log = structlog.get_logger()

SCRYFALL_BULK_API = "https://api.scryfall.com/bulk-data"
DOWNLOAD_TIMEOUT = 600  # 10 minutes for large file
API_TIMEOUT = 30
MAX_RETRIES = 3
OLD_FILES_TO_KEEP = 2

RARITY_MAP: dict[str, str] = {
    "common": "C",
    "uncommon": "U",
    "rare": "R",
    "mythic": "M",
    "special": "S",
    "bonus": "B",
}


@dataclass(frozen=True, slots=True)
class CatalogCard:
    """Domain object representing a card from the Scryfall catalog."""

    name_en: str
    set_code: str
    collector_number: str
    rarity: str
    color_identity: str
    mana_cost: str
    type_line: str
    image_uri: str | None
    name_pt: str | None = None


def _get_download_url() -> tuple[str, int]:
    """Fetch the download URL for the default_cards bulk dataset.

    Returns:
        Tuple of (download_url, expected_size_bytes).

    Raises:
        RuntimeError: If the default_cards dataset is not found.
    """
    log.info("scryfall.fetching_bulk_metadata")
    resp = httpx.get(SCRYFALL_BULK_API, timeout=API_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    for entry in data.get("data", []):
        if entry.get("type") == "default_cards":
            # Scryfall may offer download_uri (JSON) or jsonl_download_uri (JSONL)
            uri = entry.get("download_uri") or entry.get("jsonl_download_uri")
            if not uri:
                raise RuntimeError("default_cards entry has no download URI")
            size = entry.get("size") or entry.get("compressed_size") or 0
            log.info("scryfall.found_bulk_dataset", uri=uri, size_mb=round(size / 1e6, 1))
            return uri, size

    raise RuntimeError("Scryfall bulk-data response has no 'default_cards' entry")


def _cleanup_old_files(dest_dir: Path) -> None:
    """Remove old bulk data files, keeping the most recent ones."""
    json_files = list(dest_dir.glob("scryfall-default-cards-*.json"))
    jsonl_files = list(dest_dir.glob("scryfall-default-cards-*.jsonl"))
    files = sorted(
        json_files + jsonl_files,
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    for old_file in files[OLD_FILES_TO_KEEP:]:
        log.info("scryfall.removing_old_file", path=str(old_file))
        old_file.unlink()


def download_bulk_data(dest_dir: str | Path) -> Path:
    """Download Scryfall default_cards bulk data JSON.

    If a file for today already exists and is non-empty, the download is
    skipped. Retries up to 3 times on transient failures.

    Args:
        dest_dir: Directory where the JSON file will be saved.

    Returns:
        Path to the downloaded (or existing) JSON file.

    Raises:
        RuntimeError: If download fails after all retries.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    # Check both .json and .jsonl extensions (Scryfall migrated to JSONL)
    dest_file_json = dest_dir / f"scryfall-default-cards-{today}.json"
    dest_file_jsonl = dest_dir / f"scryfall-default-cards-{today}.jsonl"
    dest_file = dest_file_jsonl  # default to JSONL

    # Skip if file already exists today and is non-empty (either extension)
    for candidate in (dest_file_jsonl, dest_file_json):
        if candidate.exists() and candidate.stat().st_size > 0:
            log.info("scryfall.skip_download", path=str(candidate), reason="file_exists_today")
            return candidate

    url, _expected_size = _get_download_url()

    # Detect if URL is gzipped — we'll decompress on the fly
    is_gzipped = url.endswith(".gz")
    # Always save as .jsonl (we decompress gzip during download)
    is_jsonl_url = url.endswith(".jsonl") or url.endswith(".jsonl.gz")
    dest_file = dest_file_jsonl if is_jsonl_url else dest_file_json

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("scryfall.downloading", attempt=attempt, url=url, gzipped=is_gzipped)
            with httpx.stream("GET", url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                if is_gzipped:
                    # Download to memory then decompress
                    buf = BytesIO()
                    for chunk in resp.iter_bytes(chunk_size=1024 * 64):
                        buf.write(chunk)
                        downloaded += len(chunk)
                        if total and downloaded % (10 * 1024 * 1024) < len(chunk):
                            pct = round(downloaded / total * 100, 1)
                            log.info(
                                "scryfall.download_progress",
                                downloaded_mb=round(downloaded / 1e6, 1),
                                total_mb=round(total / 1e6, 1),
                                pct=pct,
                            )
                    log.info("scryfall.decompressing", compressed_mb=round(downloaded / 1e6, 1))
                    buf.seek(0)
                    with open(dest_file, "wb") as f:
                        f.write(gzip.decompress(buf.read()))
                else:
                    with open(dest_file, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=1024 * 64):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total and downloaded % (10 * 1024 * 1024) < len(chunk):
                                pct = round(downloaded / total * 100, 1)
                                log.info(
                                    "scryfall.download_progress",
                                    downloaded_mb=round(downloaded / 1e6, 1),
                                    total_mb=round(total / 1e6, 1),
                                    pct=pct,
                                )

            # Verify file was written
            size = dest_file.stat().st_size
            if size == 0:
                raise RuntimeError("Downloaded file is empty")

            size_mb = round(size / 1e6, 1)
            log.info("scryfall.download_complete", path=str(dest_file), size_mb=size_mb)
            _cleanup_old_files(dest_dir)
            return dest_file

        except Exception as exc:
            last_error = exc
            log.warning(
                "scryfall.download_failed",
                attempt=attempt,
                max_retries=MAX_RETRIES,
                error=str(exc),
            )
            # Remove partial file on failure
            if dest_file.exists():
                dest_file.unlink()

    raise RuntimeError(
        f"Failed to download Scryfall bulk data after {MAX_RETRIES} attempts: {last_error}"
    )


def _parse_card(raw: dict) -> CatalogCard | None:
    """Convert a raw Scryfall card dict to a CatalogCard.

    Returns None if the card should be filtered out (not paper or not English).
    """
    # Filter: must be paper game and English language
    games = raw.get("games", [])
    if "paper" not in games:
        return None
    if raw.get("lang") != "en":
        return None

    rarity_raw = raw.get("rarity", "")
    rarity = RARITY_MAP.get(rarity_raw, rarity_raw[:1].upper() if rarity_raw else "")

    color_identity = "".join(raw.get("color_identity", []))

    image_uris = raw.get("image_uris") or {}
    image_uri = image_uris.get("normal")

    return CatalogCard(
        name_en=raw.get("name", ""),
        set_code=raw.get("set", ""),
        collector_number=raw.get("collector_number", ""),
        rarity=rarity,
        color_identity=color_identity,
        mana_cost=raw.get("mana_cost", ""),
        type_line=raw.get("type_line", ""),
        image_uri=image_uri,
        name_pt=None,
    )


def parse_bulk_cards(path: Path) -> Iterator[CatalogCard]:
    """Parse a Scryfall bulk data file into CatalogCard objects.

    Supports both JSONL (one JSON object per line, preferred) and JSON
    array format. JSONL is naturally streaming and memory-efficient.
    For JSON arrays, attempts ijson for streaming, falls back to json.load().

    Args:
        path: Path to the Scryfall bulk data file (.jsonl or .json).

    Yields:
        CatalogCard objects for each paper/English card in the file.
    """
    is_jsonl = str(path).endswith(".jsonl")

    if is_jsonl:
        log.info("scryfall.parse_start", path=str(path), parser="jsonl_streaming")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                card = _parse_card(raw)
                if card is not None:
                    yield card
    else:
        # Legacy JSON array format
        try:
            import ijson

            log.info("scryfall.parse_start", path=str(path), parser="ijson_streaming")
            with open(path, "rb") as f:
                for raw in ijson.items(f, "item"):
                    card = _parse_card(raw)
                    if card is not None:
                        yield card
        except ImportError:
            log.warning(
                "scryfall.ijson_not_available",
                msg="ijson not installed, falling back to json.load()",
            )
            log.info("scryfall.parse_start", path=str(path), parser="json_load")
            with open(path, encoding="utf-8") as f:
                cards = json.load(f)
            for raw in cards:
                card = _parse_card(raw)
                if card is not None:
                    yield card
