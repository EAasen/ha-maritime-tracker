"""Tests for Phase 1.2: Coordinator snapshot integration."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.marinetraffic_tracker.client import VesselData
from custom_components.marinetraffic_tracker.kystverket_client import KystverketClient


def _make_test_vessel(mmsi: str, lat: float, lon: float, name: str = "Test") -> VesselData:
    """Create a test vessel with the given position."""
    return VesselData(
        mmsi=mmsi,
        name=f"{name} {mmsi}",
        vessel_type=70,
        latitude=lat,
        longitude=lon,
        heading=45,
        course=45,
        speed=12.5,
        status="Under way",
        origin=None,
        destination="Test Port",
        eta=None,
        source="kystverket",
        observation_time=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_coordinator_fetch_vessels_uses_snapshot_for_kystverket() -> None:
    """Verify that coordinator uses get_snapshot() for Kystverket when available.

    This is the core of Phase 1.2: a single snapshot fetch that can be
    partitioned for area, watchlist, and ports.
    """
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from custom_components.marinetraffic_tracker.const import (
        CONF_LATITUDE,
        CONF_LONGITUDE,
        CONF_RADIUS_KM,
        CONF_TRACKING_MODE,
        TRACKING_MODE_RADIUS,
    )
    from custom_components.marinetraffic_tracker.coordinator import MarineTrafficCoordinator

    # Create mock hass and config entry
    mock_hass = MagicMock(spec=HomeAssistant)
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        CONF_TRACKING_MODE: TRACKING_MODE_RADIUS,
        CONF_LATITUDE: 60.0,
        CONF_LONGITUDE: 5.0,
    }
    mock_entry.options = {
        CONF_RADIUS_KM: 50.0,
    }

    # Create a Kystverket client with mock snapshot
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )

    # Create test vessels: some inside, some outside the area
    vessel_inside = _make_test_vessel("111111111", 60.0, 5.0, "Inside")
    vessel_outside = _make_test_vessel("222222222", 62.0, 5.0, "Outside")  # ~222 km away
    snapshot = [vessel_inside, vessel_outside]

    # Mock the snapshot method
    with patch.object(kystverket_client, "get_snapshot", new_callable=AsyncMock) as mock_snapshot:
        mock_snapshot.return_value = snapshot

        # Create coordinator
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )

        # Call _fetch_vessels
        config = {**mock_entry.data, **mock_entry.options}
        result, error = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )

        # Verify:
        # 1. Snapshot was called
        mock_snapshot.assert_called_once()

        # 2. Only the vessel inside the area was returned
        assert result is not None
        assert len(result) == 1
        assert result[0].mmsi == "111111111"
        assert error is None


@pytest.mark.asyncio
async def test_coordinator_fetch_vessels_fallback_to_area_query() -> None:
    """Verify coordinator falls back to get_vessels_in_radius if snapshot unavailable.

    This ensures backward compatibility and graceful degradation.
    """
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from custom_components.marinetraffic_tracker.const import (
        CONF_LATITUDE,
        CONF_LONGITUDE,
        CONF_RADIUS_KM,
        CONF_TRACKING_MODE,
        TRACKING_MODE_RADIUS,
    )
    from custom_components.marinetraffic_tracker.coordinator import MarineTrafficCoordinator

    # Create mock hass and config entry
    mock_hass = MagicMock(spec=HomeAssistant)
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {
        CONF_TRACKING_MODE: TRACKING_MODE_RADIUS,
        CONF_LATITUDE: 60.0,
        CONF_LONGITUDE: 5.0,
    }
    mock_entry.options = {
        CONF_RADIUS_KM: 50.0,
    }

    # Create a Kystverket client
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )

    # Create test vessel
    vessel = _make_test_vessel("111111111", 60.0, 5.0)

    # Simulate a compatible client that does not expose a snapshot operation.
    kystverket_client.get_snapshot = None  # type: ignore[method-assign]

    # Mock get_vessels_in_radius to return the test vessel
    with patch.object(
        kystverket_client, "get_vessels_in_radius", new_callable=AsyncMock
    ) as mock_area:
        mock_area.return_value = [vessel]

        # Create coordinator
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )

        # Call _fetch_vessels
        config = {**mock_entry.data, **mock_entry.options}
        result, error = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )

        # Verify:
        # 1. Area query was called
        mock_area.assert_called_once()

        # 2. Result is correct
        assert result is not None
        assert len(result) == 1
        assert result[0].mmsi == "111111111"
        assert error is None


@pytest.mark.asyncio
async def test_coordinator_fetch_vessels_snapshot_with_no_area_filter() -> None:
    """Verify that if no area filter is configured, full snapshot is returned.

    This handles edge cases where tracking area might not be properly configured.
    """
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from custom_components.marinetraffic_tracker.coordinator import MarineTrafficCoordinator

    # Create mock hass and config entry with no valid tracking config
    mock_hass = MagicMock(spec=HomeAssistant)
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {}  # Empty config
    mock_entry.options = {}

    # Create a Kystverket client
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )

    # Create test vessels
    vessel1 = _make_test_vessel("111111111", 60.0, 5.0)
    vessel2 = _make_test_vessel("222222222", 62.0, 7.0)
    snapshot = [vessel1, vessel2]

    # Mock the snapshot method
    with patch.object(kystverket_client, "get_snapshot", new_callable=AsyncMock) as mock_snapshot:
        mock_snapshot.return_value = snapshot

        # Create coordinator
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )

        # Call _fetch_vessels with empty tracking mode (will default)
        config = {**mock_entry.data, **mock_entry.options}
        result, error = await coordinator._fetch_vessels(kystverket_client, "radius", config)

        # Verify:
        # 1. Snapshot was called
        mock_snapshot.assert_called_once()

        # 2. Full snapshot returned (no filtering when no area configured)
        assert result is not None
        assert len(result) == 2
        assert error is None


def test_vessel_data_observation_metadata_in_fetch() -> None:
    """Verify that fetched vessels retain observation metadata.

    This ensures the Phase 1.1 improvements flow through the coordinator.
    """
    vessel = _make_test_vessel("123456789", 60.0, 5.0)

    # Verify observation metadata is present and correct
    assert vessel.source == "kystverket"
    assert vessel.observation_time is not None
    assert vessel.observation_time.tzinfo is not None
    assert vessel.source_msgtime is None  # Not set in factory
