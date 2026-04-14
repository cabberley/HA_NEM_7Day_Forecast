"""Data update coordinator for NEM PD7DAY."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import zipfile

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE_URL,
    CONF_REGIONS,
    DEFAULT_REGIONS,
    DOMAIN,
    FILE_DT_PATTERN,
    FILE_PATTERN,
    SCAN_INTERVAL_SECONDS,
)


class LinkExtractor(HTMLParser):
    """Extract links from a listing page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def parse_dt(value: str) -> datetime:
    """Parse NEM date format."""
    return datetime.strptime(value, "%Y/%m/%d %H:%M:%S")


def to_iso_local(value: datetime) -> str:
    """Render datetime in local ISO style without timezone."""
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def source_file_datetime(file_name: str) -> datetime | None:
    """Extract source file timestamp from the PD7DAY file name."""
    match = FILE_DT_PATTERN.search(file_name)
    if not match:
        return None

    timestamp = match.group(1)
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M"):
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue
    return None


def average_price(prices_slice: list[dict]) -> float | None:
    """Return average $/kWh for a sequence."""
    if not prices_slice:
        return None
    return round(sum(item["price_kwh"] for item in prices_slice) / len(prices_slice), 6)


def find_cheapest_window(
    prices: list[dict],
    hours: int = 2,
    interval_minutes: int = 30,
) -> dict | None:
    """Return the cheapest rolling window."""
    window_points = int(hours * 60 / interval_minutes)
    if len(prices) < window_points:
        return None

    best: dict | None = None
    for index in range(len(prices) - window_points + 1):
        window = prices[index : index + window_points]
        avg = average_price(window)
        if avg is None:
            continue
        if best is None or avg < best["avg_price_kwh"]:
            best = {
                "start": window[0]["time"],
                "end": window[-1]["time"],
                "avg_price_kwh": avg,
                "points": len(window),
            }
    return best


def min_max_for_horizon(prices: list[dict], hours: int = 24) -> tuple[float | None, float | None]:
    """Return min and max for a given horizon."""
    if not prices:
        return None, None
    subset = prices[: int(hours * 2)]
    if not subset:
        return None, None
    vals = [item["price_kwh"] for item in subset]
    return round(min(vals), 6), round(max(vals), 6)


def load_pd7day_prices(csv_text: str, region: str) -> tuple[datetime | None, list[dict]]:
    """Parse PD7DAY prices for a region."""
    prices: list[dict] = []
    run_dt: datetime | None = None

    reader = csv.reader(io.StringIO(csv_text))
    for row in reader:
        if not row or row[0] != "D":
            continue
        if len(row) < 20:
            continue
        if row[1] != "PD7DAY" or row[2] != "PRICESOLUTION":
            continue
        if row[7] != region:
            continue

        this_run = parse_dt(row[4])
        if run_dt is None:
            run_dt = this_run

        prices.append(
            {
                "time": to_iso_local(parse_dt(row[6])),
                "price_kwh": round(float(row[8]) / 1000.0, 6),
            }
        )

    prices.sort(key=lambda item: item["time"])
    return run_dt, prices


class NEMPD7DayCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate NEM PD7DAY polling and parsing."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.store = Store[dict](hass, version=1, key=f"{DOMAIN}_{entry.entry_id}.json")
        self._last_file_name: str | None = None
        self._last_csv_path: str | None = None
        self._last_data: dict | None = None

    @property
    def regions(self) -> list[str]:
        """Configured regions from options or entry data."""
        return self.entry.options.get(
            CONF_REGIONS,
            self.entry.data.get(CONF_REGIONS, DEFAULT_REGIONS),
        )

    async def _fetch_listing(self) -> list[dict[str, str]]:
        """Fetch and parse the remote directory listing."""
        response = await self.session.get(BASE_URL)
        response.raise_for_status()
        html = await response.text()

        parser = LinkExtractor()
        parser.feed(html)

        files: list[dict[str, str]] = []
        for href in parser.links:
            name = href.split("/")[-1]
            if FILE_PATTERN.search(name):
                files.append({"name": name, "url": urljoin(BASE_URL, href)})

        return files

    async def _fetch_file_bytes(self, url: str) -> bytes:
        """Fetch a CSV or ZIP file as bytes."""
        response = await self.session.get(url)
        response.raise_for_status()
        return await response.read()

    @staticmethod
    def _extract_csv_from_bytes(file_name: str, payload: bytes) -> str:
        """Return CSV text from ZIP/CSV payload bytes."""
        if file_name.upper().endswith(".ZIP"):
            with zipfile.ZipFile(io.BytesIO(payload), "r") as zf:
                members = [item for item in zf.namelist() if item.upper().endswith(".CSV")]
                if not members:
                    raise FileNotFoundError(f"No CSV found in {file_name}")
                member = sorted(members)[0]
                with zf.open(member) as src:
                    return src.read().decode("utf-8", errors="ignore")

        return payload.decode("utf-8", errors="ignore")

    async def _load_cached(self) -> dict | None:
        """Load persisted state from HA storage."""
        if self._last_data is not None:
            return self._last_data
        data = await self.store.async_load()
        if not data:
            return None
        self._last_data = data
        self._last_file_name = data.get("source_file_name")
        self._last_csv_path = data.get("source_file")
        return data

    async def _save_cached(self, data: dict) -> None:
        """Persist latest parsed data."""
        self._last_data = data
        self._last_file_name = data.get("source_file_name")
        self._last_csv_path = data.get("source_file")
        await self.store.async_save(data)

    @staticmethod
    def _write_csv_file(path: Path, content: str) -> None:
        """Write CSV content to disk."""
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _cleanup_old_storage_files(storage_dir: Path, keep_file: Path) -> None:
        """Remove stale downloaded files, keeping only the latest."""
        for item in storage_dir.iterdir():
            if item == keep_file:
                continue
            if item.is_file():
                item.unlink(missing_ok=True)

    async def _async_update_data(self) -> dict:
        """Check for the newest PD7DAY file and parse configured regions."""
        try:
            files = await self._fetch_listing()
            if not files:
                raise UpdateFailed("No PUBLIC_PD7DAY files found")

            newest = sorted(files, key=lambda item: item["name"])[-1]
            newest_name = newest["name"]

            if newest_name == self._last_file_name and self._last_data is not None:
                payload = dict(self._last_data)
                payload["last_success"] = to_iso_local(datetime.now())
                await self._save_cached(payload)
                return payload

            file_bytes = await self._fetch_file_bytes(newest["url"])
            csv_text = self._extract_csv_from_bytes(newest_name, file_bytes)

            storage_dir = Path(self.hass.config.path(f".storage/{DOMAIN}"))
            storage_dir.mkdir(parents=True, exist_ok=True)
            csv_path = storage_dir / f"{newest_name}.csv"
            await self.hass.async_add_executor_job(self._write_csv_file, csv_path, csv_text)
            await self.hass.async_add_executor_job(
                self._cleanup_old_storage_files,
                storage_dir,
                csv_path,
            )

            file_dt = source_file_datetime(newest_name)

            region_payloads: dict[str, dict] = {}
            for region in self.regions:
                run_dt, prices = load_pd7day_prices(csv_text, region)
                if not prices:
                    continue

                current_price = prices[0]["price_kwh"]
                next_price = prices[1]["price_kwh"] if len(prices) > 1 else None
                min_24h, max_24h = min_max_for_horizon(prices, hours=24)
                cheapest_2h = find_cheapest_window(prices, hours=2, interval_minutes=30)

                region_payloads[region] = {
                    "region": region,
                    "forecast_generated_at": to_iso_local(run_dt) if run_dt else None,
                    "current_forecast_price": round(current_price, 6),
                    "next_forecast_price": round(next_price, 6) if next_price is not None else None,
                    "min_24h": min_24h,
                    "max_24h": max_24h,
                    "cheapest_2h_window": cheapest_2h,
                    "prices": prices,
                    "interval_minutes": 30,
                    "unit": "$/kWh",
                }

            if not region_payloads:
                cached = await self._load_cached()
                if cached is not None:
                    return cached
                raise UpdateFailed("No data rows for configured region selection")

            if file_dt is None:
                first_region = next(iter(region_payloads.values()), {})
                fallback_dt = first_region.get("forecast_generated_at")
            else:
                fallback_dt = to_iso_local(file_dt)

            payload = {
                "source_file": str(csv_path),
                "source_file_name": newest_name,
                "source_file_datetime": fallback_dt,
                "regions": region_payloads,
                "last_success": to_iso_local(datetime.now()),
            }
            await self._save_cached(payload)
            return payload

        except Exception as err:
            cached = await self._load_cached()
            if cached is not None:
                return cached
            raise UpdateFailed(str(err)) from err
