"""Vessel observation log files for the Norwegian Maritime Tracker integration.

Appends every observation from every poll cycle to a file under
``<config>/marinetraffic_tracker/``, giving a permanent record with all AIS
fields that outlives Home Assistant's recorder purge.

Files rotate daily (``vessels-YYYY-MM-DD.csv``) and are pruned after a
configurable retention period, because a busy area produces tens of thousands
of rows per day.

All file access happens in the executor: writing from the event loop would
block every other integration.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import UTC, date, datetime
import json
import logging
from pathlib import Path
from typing import Any

from .client import VesselData
from .const import (
    VESSEL_LOG_DIR_NAME,
    VESSEL_LOG_FORMAT_CSV,
    VESSEL_TYPE_MAP,
)

_LOGGER = logging.getLogger(__name__)

# Column order for CSV output. Also the key order used for JSON Lines so both
# formats expose exactly the same information.
LOG_FIELDS: tuple[str, ...] = (
    "logged_at",
    "mmsi",
    "name",
    "vessel_type",
    "vessel_type_name",
    "latitude",
    "longitude",
    "heading",
    "course",
    "speed",
    "status",
    "origin",
    "destination",
    "eta",
    "imo",
    "flag",
    "callsign",
    "length",
    "beam",
    "draught",
    "rate_of_turn",
    "msgtime",
    "last_seen",
    "source",
)

# Leading characters a spreadsheet treats as the start of a formula. AIS is an
# unauthenticated broadcast, so vessel names and destinations are attacker
# controlled and must never be evaluated when the log is opened in Excel.
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitise_csv_value(value: Any) -> Any:
    """Neutralise spreadsheet formula injection in free-text CSV fields."""
    if isinstance(value, str) and value.startswith(_CSV_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def vessel_to_row(vessel: VesselData, logged_at: datetime) -> dict[str, Any]:
    """Flatten *vessel* into a log row containing every available field."""
    raw = asdict(vessel)
    row: dict[str, Any] = {
        "logged_at": logged_at.isoformat(),
        "vessel_type_name": VESSEL_TYPE_MAP.get(vessel.vessel_type, "Unknown"),
        "last_seen": vessel.last_seen.isoformat() if vessel.last_seen else None,
    }
    for key in LOG_FIELDS:
        if key not in row:
            row[key] = raw.get(key)
    return {key: row[key] for key in LOG_FIELDS}


class VesselLogWriter:
    """Append vessel observations to a rotating log file."""

    def __init__(
        self,
        log_dir: Path,
        entry_id: str,
        log_format: str,
        retention_days: int,
    ) -> None:
        """Initialise a writer rooted at *log_dir*."""
        self._log_dir = log_dir
        self._entry_id = entry_id
        self._log_format = log_format
        self._retention_days = retention_days
        self._last_pruned: date | None = None

    def path_for(self, day: date) -> Path:
        """Return the log file path for *day*."""
        suffix = "csv" if self._log_format == VESSEL_LOG_FORMAT_CSV else "jsonl"
        return self._log_dir / f"vessels-{self._entry_id[:8]}-{day.isoformat()}.{suffix}"

    def write(self, vessels: list[VesselData], logged_at: datetime | None = None) -> None:
        """Append *vessels* to today's log file. Blocking; call in the executor."""
        if not vessels:
            return

        logged_at = logged_at or datetime.now(UTC)
        target = self.path_for(logged_at.date())
        rows = [vessel_to_row(vessel, logged_at) for vessel in vessels]

        self._log_dir.mkdir(parents=True, exist_ok=True)
        is_new = not target.exists()

        with target.open("a", encoding="utf-8", newline="") as handle:
            if self._log_format == VESSEL_LOG_FORMAT_CSV:
                writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
                if is_new:
                    writer.writeheader()
                for row in rows:
                    writer.writerow({k: _sanitise_csv_value(v) for k, v in row.items()})
            else:
                for row in rows:
                    handle.write(json.dumps(row, default=str) + "\n")

        self._prune(logged_at.date())

    def _prune(self, today: date) -> None:
        """Delete log files older than the retention period, once per day."""
        if self._retention_days <= 0 or self._last_pruned == today:
            return
        self._last_pruned = today

        cutoff = today.toordinal() - self._retention_days
        for path in self._log_dir.glob(f"vessels-{self._entry_id[:8]}-*"):
            try:
                day = date.fromisoformat(path.stem[-10:])
            except ValueError:
                continue
            if day.toordinal() < cutoff:
                try:
                    path.unlink()
                except OSError as exc:
                    _LOGGER.warning("Could not delete old vessel log %s: %s", path, exc)


def build_writer(
    config_dir: str,
    entry_id: str,
    log_format: str,
    retention_days: int,
) -> VesselLogWriter:
    """Create a writer rooted at the integration's directory in the HA config."""
    return VesselLogWriter(
        Path(config_dir) / VESSEL_LOG_DIR_NAME,
        entry_id,
        log_format,
        retention_days,
    )
