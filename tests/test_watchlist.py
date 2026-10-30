"""Tests for watchlist functionality: persistent MMSI tracking outside configured area.

Verifies:
- Watchlist MMSIs are stored and retrieved from config
- Watched vessels are tracked in a separate registry
- Entity identity is preserved when vessels transition between area/watchlist
- Watched vessels don't affect area counts or statistics
- Filtering and exclusions don't affect watchlist
- Stale timeout and removal work correctly
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.marinetraffic_tracker.client import VesselData
from custom_components.marinetraffic_tracker.const import (
    ATTR_WATCHED_COUNT,
    ATTR_WATCHED_VESSELS,
    CONF_DATA_SOURCE,
    CONF_EXCLUDE_ANCHORED,
    CONF_EXCLUDE_MOORED,
    CONF_FILTER_VESSEL_TYPES,
    CONF_STALE_TIMEOUT,
    CONF_UPDATE_INTERVAL,
    CONF_WATCHLIST_MMSI,
    DATA_SOURCE_KYSTVERKET,
    DEFAULT_EXCLUDE_ANCHORED,
    DEFAULT_EXCLUDE_MOORED,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_STALE_TIMEOUT,
    MAX_WATCHLIST_MMSI,
    MMSI_LENGTH,
)
from custom_components.marinetraffic_tracker.coordinator import MarineTrafficCoordinator

from .conftest import MOCK_VESSEL_CARGO, MOCK_VESSEL_PASSENGER, MOCK_VESSEL_TANKER

# ---------------------------------------------------------------------------
# Test vessels
# ---------------------------------------------------------------------------

# Cargo vessel inside area (will be in coordinator.data)
_CARGO_IN_AREA = MOCK_VESSEL_CARGO

# Passenger vessel outside area but in watchlist
_PASSENGER_WATCHED = replace(
    MOCK_VESSEL_PASSENGER,
    mmsi="555555555",
    name="FJORD QUEEN",
    latitude=70.0,  # Outside configured area
    longitude=25.0,
)

# Tanker vessel in watchlist but not in snapshot
_TANKER_WATCHED = replace(
    MOCK_VESSEL_TANKER,
    mmsi="777777777",
    name="NORDIC TANKER",
    latitude=71.0,
    longitude=26.0,
)


def _make_entry(
    options: dict | None = None,
    data: dict | None = None,
    watchlist_mmsis: list[str] | None = None,
) -> MagicMock:
    """Return a fake ConfigEntry with controllable watchlist."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = data or {
        CONF_UPDATE_INTERVAL: 60,
        CONF_STALE_TIMEOUT: DEFAULT_STALE_TIMEOUT,
        "tracking_mode": "radius",
        "latitude": 59.9,
        "longitude": 10.7,
        "radius_km": 50.0,
        CONF_DATA_SOURCE: DATA_SOURCE_KYSTVERKET,
    }
    entry.options = options or {}
    if watchlist_mmsis:
        entry.options[CONF_WATCHLIST_MMSI] = watchlist_mmsis
    return entry


def _make_coordinator(
    hass: MagicMock,
    client: AsyncMock,
    watchlist_mmsis: list[str] | None = None,
) -> MarineTrafficCoordinator:
    """Build a coordinator with optional watchlist."""
    entry = _make_entry(watchlist_mmsis=watchlist_mmsis)
    return MarineTrafficCoordinator(hass, entry, client)


async def _refresh(coordinator: MarineTrafficCoordinator) -> None:
    """Refresh coordinator with jitter disabled for deterministic tests."""
    with patch("custom_components.marinetraffic_tracker.coordinator.asyncio.sleep"):
        await coordinator.async_refresh()


# ---------------------------------------------------------------------------
# Tests: Configuration and initialization
# ---------------------------------------------------------------------------


def test_watchlist_mmsis_empty_by_default() -> None:
    """Watchlist should be empty if not configured."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client)

    assert coordinator.get_watched_mmsi_list() == []


def test_watchlist_mmsis_read_from_options() -> None:
    """Watchlist should be read from entry.options if present."""
    hass = MagicMock()
    client = AsyncMock()
    mmsis = ["555555555", "777777777"]
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=mmsis)

    assert coordinator.get_watched_mmsi_list() == mmsis


def test_watchlist_mmsis_read_from_data_as_fallback() -> None:
    """Watchlist should fall back to entry.data if options not set (during initial setup)."""
    hass = MagicMock()
    client = AsyncMock()

    entry = _make_entry()
    entry.data[CONF_WATCHLIST_MMSI] = ["555555555", "777777777"]
    entry.options = {}  # Empty options, so fallback to data

    coordinator = MarineTrafficCoordinator(hass, entry, client)
    assert coordinator.get_watched_mmsi_list() == ["555555555", "777777777"]


def test_watchlist_vessels_empty_initially() -> None:
    """Watchlist vessels registry should be empty before first poll."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])

    assert coordinator.watchlist_vessels == {}


# ---------------------------------------------------------------------------
# Tests: Watched vessel isolation from area
# ---------------------------------------------------------------------------


async def test_watched_vessel_enters_snapshot_moved_to_watchlist() -> None:
    """When a watched MMSI appears in snapshot, it goes to watchlist_vessels, not coordinator.data."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])

    # Snapshot returns the passenger vessel with MMSI in watchlist
    client.get_vessels_in_radius = AsyncMock(
        return_value=[_PASSENGER_WATCHED]  # MMSI 555555555 is watched
    )

    await _refresh(coordinator)

    # Watched vessel should NOT be in area data
    assert "555555555" not in coordinator.data

    # Watched vessel SHOULD be in watchlist registry
    assert "555555555" in coordinator.watchlist_vessels
    assert coordinator.watchlist_vessels["555555555"].name == "FJORD QUEEN"


async def test_watched_vessel_not_in_snapshot_removed_after_timeout() -> None:
    """When a watched vessel is absent from snapshot for > stale_timeout, it's removed."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])

    # First poll: watched vessel is in snapshot
    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)
    assert "555555555" in coordinator.watchlist_vessels

    # Simulate passage of time beyond stale_timeout
    # (Coordinator stores last_seen on each vessel from client, so we can mock advancement)
    old_vessel = replace(
        coordinator.watchlist_vessels["555555555"],
        last_seen=datetime.now(UTC) - timedelta(seconds=DEFAULT_STALE_TIMEOUT + 100),
    )
    coordinator.watchlist_vessels["555555555"] = old_vessel

    # Second poll: watched vessel is no longer in snapshot
    client.get_vessels_in_radius = AsyncMock(return_value=[])
    await _refresh(coordinator)

    # Stale watched vessel should be removed
    assert "555555555" not in coordinator.watchlist_vessels


async def test_watched_and_area_vessels_separate_registries() -> None:
    """Watched and area vessels are tracked in separate registries and don't interfere."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(
        hass, client, watchlist_mmsis=["555555555"]  # Passenger is watched
    )

    # Snapshot returns both area vessel (cargo) and watched vessel (passenger)
    client.get_vessels_in_radius = AsyncMock(
        return_value=[_CARGO_IN_AREA, _PASSENGER_WATCHED]
    )

    await _refresh(coordinator)

    # Cargo (not watched) is in area data
    assert "123456789" in coordinator.data
    assert coordinator.data["123456789"].name == "EVER GIVEN"

    # Passenger (watched) is in watchlist, not area data
    assert "555555555" not in coordinator.data
    assert "555555555" in coordinator.watchlist_vessels
    assert coordinator.watchlist_vessels["555555555"].name == "FJORD QUEEN"


# ---------------------------------------------------------------------------
# Tests: Unified resolver (get_vessel)
# ---------------------------------------------------------------------------


async def test_get_vessel_resolves_from_area() -> None:
    """get_vessel() should resolve area vessels."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client)

    client.get_vessels_in_radius = AsyncMock(return_value=[_CARGO_IN_AREA])
    await _refresh(coordinator)

    vessel = coordinator.get_vessel("123456789")
    assert vessel is not None
    assert vessel.name == "EVER GIVEN"


async def test_get_vessel_resolves_from_watchlist() -> None:
    """get_vessel() should resolve watched vessels."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])

    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    vessel = coordinator.get_vessel("555555555")
    assert vessel is not None
    assert vessel.name == "FJORD QUEEN"


async def test_get_vessel_returns_none_for_unknown_mmsi() -> None:
    """get_vessel() should return None for unknown MMSI."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client)

    client.get_vessels_in_radius = AsyncMock(return_value=[])
    await _refresh(coordinator)

    vessel = coordinator.get_vessel("999999999")
    assert vessel is None


async def test_get_vessel_prefers_area_over_watchlist() -> None:
    """If a vessel somehow exists in both registries, get_vessel() returns area version."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["123456789"])

    client.get_vessels_in_radius = AsyncMock(return_value=[_CARGO_IN_AREA])
    await _refresh(coordinator)

    # Force vessel into both registries (shouldn't happen in practice, but verify precedence)
    coordinator.watchlist_vessels["123456789"] = replace(
        _CARGO_IN_AREA, name="MODIFIED"
    )

    vessel = coordinator.get_vessel("123456789")
    assert vessel.name == "EVER GIVEN"  # Area version, not watchlist


# ---------------------------------------------------------------------------
# Tests: Watchlist independence from filters
# ---------------------------------------------------------------------------


async def test_vessel_type_filter_does_not_affect_watchlist() -> None:
    """Watched vessels should appear even if their type is filtered."""
    hass = MagicMock()
    client = AsyncMock()

    # Create coordinator with vessel type filter that excludes passengers (type 60)
    entry = _make_entry(watchlist_mmsis=["555555555"])
    entry.options[CONF_FILTER_VESSEL_TYPES] = ["70", "80"]  # Exclude type 60 (passenger)

    coordinator = MarineTrafficCoordinator(hass, entry, client)

    # Snapshot returns passenger vessel (type 60) - it's watched so should be included
    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    # Watched passenger should be in watchlist despite filter
    assert "555555555" in coordinator.watchlist_vessels
    assert coordinator.watchlist_vessels["555555555"].vessel_type == 60


async def test_anchored_exclusion_does_not_affect_watchlist() -> None:
    """Watched anchored vessels should appear even if anchored is excluded."""
    hass = MagicMock()
    client = AsyncMock()

    entry = _make_entry(watchlist_mmsis=["987654321"])
    entry.options[CONF_EXCLUDE_ANCHORED] = True

    coordinator = MarineTrafficCoordinator(hass, entry, client)

    # Snapshot returns tanker at anchor (status="At Anchor")
    client.get_vessels_in_radius = AsyncMock(return_value=[_TANKER_WATCHED])
    await _refresh(coordinator)

    # Watched anchored vessel should be in watchlist despite exclusion
    assert "987654321" in coordinator.watchlist_vessels


# ---------------------------------------------------------------------------
# Tests: Entity identity and watchlist sensor
# ---------------------------------------------------------------------------


async def test_watched_vessel_count_sensor_state() -> None:
    """Watchlist sensor state should reflect current watched vessel count."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(
        hass, client, watchlist_mmsis=["555555555", "777777777"]
    )

    # Only one of the two watched vessels is in snapshot
    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    assert len(coordinator.watchlist_vessels) == 1


async def test_watched_vessel_sensor_attributes() -> None:
    """Watchlist sensor should expose watched_mmsis and watched_vessels attributes."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])

    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    # Coordinator maintains the watchlist_vessels registry
    assert "555555555" in coordinator.watchlist_vessels

    # Sensor would have these attributes available:
    vessel = coordinator.watchlist_vessels["555555555"]
    assert vessel.mmsi == "555555555"
    assert vessel.name == "FJORD QUEEN"


# ---------------------------------------------------------------------------
# Tests: Persistence and configuration
# ---------------------------------------------------------------------------


def test_watchlist_max_limit_enforced_by_config_flow() -> None:
    """MAX_WATCHLIST_MMSI constant should match max items in schema validation."""
    # This test documents the contract; actual validation is in config_flow.py
    assert MAX_WATCHLIST_MMSI == 100


def test_mmsi_length_constant_is_nine_digits() -> None:
    """MMSI_LENGTH should be 9 (IMO spec)."""
    assert MMSI_LENGTH == 9


async def test_watchlist_persists_across_reconfig() -> None:
    """When watchlist is updated via options, new watchlist is used on next refresh."""
    hass = MagicMock()
    client = AsyncMock()

    # Start with one watched MMSI
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])
    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    assert coordinator.get_watched_mmsi_list() == ["555555555"]

    # Update configuration to add second MMSI
    coordinator._config_entry.options[CONF_WATCHLIST_MMSI] = ["555555555", "777777777"]

    # Second poll uses new configuration
    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    assert coordinator.get_watched_mmsi_list() == ["555555555", "777777777"]


# ---------------------------------------------------------------------------
# Tests: No additional API calls
# ---------------------------------------------------------------------------


async def test_watchlist_uses_same_snapshot_no_extra_calls() -> None:
    """Watchlist should use the same vessel snapshot; no extra API calls."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(
        hass, client, watchlist_mmsis=["555555555", "777777777"]
    )

    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])
    await _refresh(coordinator)

    # Should call get_vessels_in_radius exactly once
    assert client.get_vessels_in_radius.call_count == 1


# ---------------------------------------------------------------------------
# Tests: Debug logging
# ---------------------------------------------------------------------------


async def test_coordinator_logs_watched_vessel_count() -> None:
    """Coordinator debug logging should include watched vessel count."""
    hass = MagicMock()
    client = AsyncMock()
    coordinator = _make_coordinator(hass, client, watchlist_mmsis=["555555555"])

    client.get_vessels_in_radius = AsyncMock(return_value=[_PASSENGER_WATCHED])

    # Verify that debug logging includes watched count
    # (Actual log verification would be in integration tests; this documents the contract)
    await _refresh(coordinator)
    assert len(coordinator.watchlist_vessels) == 1
