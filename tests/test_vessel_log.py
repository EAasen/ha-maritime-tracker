"""Tests for vessel observation log files."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import json
from pathlib import Path

from custom_components.marinetraffic_tracker.const import (
    VESSEL_LOG_FORMAT_CSV,
    VESSEL_LOG_FORMAT_JSONL,
)
from custom_components.marinetraffic_tracker.vessel_log import (
    LOG_FIELDS,
    VesselLogWriter,
    vessel_to_row,
)

from .conftest import MOCK_VESSEL_CARGO, MOCK_VESSEL_TANKER

_NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _writer(tmp_path: Path, log_format: str = VESSEL_LOG_FORMAT_CSV, retention: int = 7):
    return VesselLogWriter(tmp_path / "logs", "abcdef123456", log_format, retention)


def test_row_contains_every_field() -> None:
    """Each row must carry the full AIS field set."""
    row = vessel_to_row(MOCK_VESSEL_CARGO, _NOW)
    assert tuple(row) == LOG_FIELDS
    assert row["mmsi"] == "123456789"
    assert row["vessel_type_name"] == "Cargo"
    assert row["logged_at"] == _NOW.isoformat()


def test_csv_written_with_header_once(tmp_path: Path) -> None:
    """The header is written on creation and not repeated on append."""
    writer = _writer(tmp_path)
    writer.write([MOCK_VESSEL_CARGO], _NOW)
    writer.write([MOCK_VESSEL_TANKER], _NOW)

    with writer.path_for(_NOW.date()).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [r["mmsi"] for r in rows] == ["123456789", "987654321"]
    assert list(rows[0]) == list(LOG_FIELDS)


def test_jsonl_written_one_object_per_line(tmp_path: Path) -> None:
    """JSON Lines output is one complete object per vessel."""
    writer = _writer(tmp_path, VESSEL_LOG_FORMAT_JSONL)
    writer.write([MOCK_VESSEL_CARGO, MOCK_VESSEL_TANKER], _NOW)

    lines = writer.path_for(_NOW.date()).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["name"] == "EVER GIVEN"


def test_csv_formula_injection_is_neutralised(tmp_path: Path) -> None:
    """AIS is unauthenticated, so names must never become spreadsheet formulas."""
    from dataclasses import replace

    hostile = replace(MOCK_VESSEL_CARGO, name='=HYPERLINK("http://evil","click")')
    writer = _writer(tmp_path)
    writer.write([hostile], _NOW)

    raw = writer.path_for(_NOW.date()).read_text(encoding="utf-8")
    assert "\"'=HYPERLINK" in raw or "'=HYPERLINK" in raw
    assert not any(line.startswith("=") for line in raw.splitlines())


def test_empty_vessel_list_writes_nothing(tmp_path: Path) -> None:
    """An empty poll must not create a file."""
    writer = _writer(tmp_path)
    writer.write([], _NOW)
    assert not writer.path_for(_NOW.date()).exists()


def test_files_rotate_daily(tmp_path: Path) -> None:
    """Each day gets its own file."""
    writer = _writer(tmp_path)
    day_two = datetime(2026, 5, 2, 12, 0, tzinfo=UTC)

    writer.write([MOCK_VESSEL_CARGO], _NOW)
    writer.write([MOCK_VESSEL_CARGO], day_two)

    assert writer.path_for(_NOW.date()).exists()
    assert writer.path_for(day_two.date()).exists()


def test_old_files_pruned_after_retention(tmp_path: Path) -> None:
    """Files past the retention window are deleted; recent ones are kept."""
    writer = _writer(tmp_path, retention=7)
    old = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
    recent = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)

    writer.write([MOCK_VESSEL_CARGO], old)
    writer.write([MOCK_VESSEL_CARGO], recent)
    writer.write([MOCK_VESSEL_CARGO], _NOW)

    assert not writer.path_for(old.date()).exists()
    assert writer.path_for(recent.date()).exists()
    assert writer.path_for(_NOW.date()).exists()


def test_retention_zero_keeps_everything(tmp_path: Path) -> None:
    """Retention of 0 disables pruning."""
    writer = _writer(tmp_path, retention=0)
    old = datetime(2020, 1, 1, 12, 0, tzinfo=UTC)

    writer.write([MOCK_VESSEL_CARGO], old)
    writer.write([MOCK_VESSEL_CARGO], _NOW)

    assert writer.path_for(old.date()).exists()
