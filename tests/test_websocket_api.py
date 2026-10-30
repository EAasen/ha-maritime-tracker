"""Tests for maritime tracker WebSocket API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.test.common import MockConfigEntry

from custom_components.marinetraffic_tracker.const import DOMAIN
from custom_components.marinetraffic_tracker.coordinator import MarineTrafficCoordinator
from custom_components.marinetraffic_tracker.client import VesselData
from custom_components.marinetraffic_tracker.websocket_api import (
    WS_TYPE_SUBSCRIBE,
    WS_TYPE_UNSUBSCRIBE,
    WS_TYPE_GET_SNAPSHOT,
    WS_TYPE_GET_TRAIL,
    MAX_SNAPSHOT_ROWS,
    MAX_TRAIL_POINTS,
    ERROR_INVALID_ENTRY,
    ERROR_INVALID_REQUEST,
    ERROR_INTERNAL,
    _build_bounded_snapshot,
    _get_bounded_trail,
)


@pytest.fixture
def mock_connection():
    """Create a mock WebSocket connection."""
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.send_message = MagicMock()
    conn.subscriptions = {}
    return conn


@pytest.fixture
def sample_vessel_data():
    """Create sample vessel data for testing."""
    return VesselData(
        mmsi="123456789",
        name="Test Vessel",
        call_sign="CALL",
        imo_number="1234567",
        vessel_type=30,
        length=100,
        width=20,
        draught=5.5,
        latitude=60.5,
        longitude=5.5,
        heading=180,
        course=185,
        speed=12.5,
        destination="Bergen",
        eta="2026-10-30T20:00:00Z",
        status="Underway using engine",
        source_time="2026-10-30T17:20:00Z",
        last_seen=datetime.now(UTC),
    )


@pytest.fixture
def sample_stale_vessel_data():
    """Create stale vessel data for testing."""
    vessel = VesselData(
        mmsi="999999999",
        name="Stale Vessel",
        call_sign="STALE",
        imo_number="9999999",
        vessel_type=50,
        length=80,
        width=15,
        draught=3.0,
        latitude=60.0,
        longitude=5.0,
        heading=None,
        course=None,
        speed=0.0,
        destination=None,
        eta=None,
        status="Moored",
        source_time="2026-10-29T17:20:00Z",
        last_seen=datetime.now(UTC) - timedelta(hours=2),
    )
    return vessel


class TestBoundedSnapshot:
    """Test bounded snapshot generation."""

    @pytest.mark.asyncio
    async def test_build_snapshot_basic(
        self, hass: HomeAssistant, sample_vessel_data: VesselData
    ):
        """Test basic snapshot building."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        coordinator.data = {"123456789": sample_vessel_data}
        coordinator._entry = entry
        coordinator._watchlist_vessels = {}
        coordinator._status_tracker = MagicMock()
        coordinator._status_tracker.stale_timeout = 3600

        snapshot = _build_bounded_snapshot(coordinator, page=1)

        assert snapshot.entry_id == "test_entry"
        assert len(snapshot.vessels) == 1
        assert snapshot.vessels[0].mmsi == "123456789"
        assert snapshot.vessels[0].name == "Test Vessel"
        assert snapshot.vessels[0].is_stale is False
        assert snapshot.vessels[0].is_watched is False
        assert snapshot.total_count == 1
        assert snapshot.page == 1
        assert snapshot.has_next is False

    @pytest.mark.asyncio
    async def test_build_snapshot_pagination(self, hass: HomeAssistant):
        """Test snapshot pagination."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        vessels = {}
        for i in range(150):
            v = VesselData(
                mmsi=f"{100000000 + i}",
                name=f"Vessel {i}",
                call_sign=f"CALL{i}",
                imo_number="0",
                vessel_type=30,
                length=100,
                width=20,
                draught=5.5,
                latitude=60.0,
                longitude=5.0,
                heading=180,
                course=185,
                speed=12.5,
                destination=None,
                eta=None,
                status="Underway using engine",
                source_time="2026-10-30T17:20:00Z",
                last_seen=datetime.now(UTC),
            )
            vessels[v.mmsi] = v

        coordinator.data = vessels
        coordinator._entry = entry
        coordinator._watchlist_vessels = {}
        coordinator._status_tracker = MagicMock()
        coordinator._status_tracker.stale_timeout = 3600

        # Page 1.
        snap1 = _build_bounded_snapshot(coordinator, page=1, page_size=100)
        assert len(snap1.vessels) == 100
        assert snap1.page == 1
        assert snap1.has_next is True
        assert snap1.total_count == 150

        # Page 2.
        snap2 = _build_bounded_snapshot(coordinator, page=2, page_size=100)
        assert len(snap2.vessels) == 50
        assert snap2.page == 2
        assert snap2.has_next is False

    @pytest.mark.asyncio
    async def test_build_snapshot_stale_detection(
        self,
        hass: HomeAssistant,
        sample_stale_vessel_data: VesselData,
    ):
        """Test stale vessel detection."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        coordinator.data = {"999999999": sample_stale_vessel_data}
        coordinator._entry = entry
        coordinator._watchlist_vessels = {}
        coordinator._status_tracker = MagicMock()
        coordinator._status_tracker.stale_timeout = 3600  # 1 hour

        snapshot = _build_bounded_snapshot(coordinator, page=1)

        # Vessel is 2 hours old, should be stale with 1-hour timeout.
        assert snapshot.vessels[0].is_stale is True

    @pytest.mark.asyncio
    async def test_build_snapshot_watched_vessels(
        self, hass: HomeAssistant, sample_vessel_data: VesselData
    ):
        """Test watched vessel marking in snapshot."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        watched_vessel = VesselData(
            mmsi="987654321",
            name="Watched Vessel",
            call_sign="WATCH",
            imo_number="9876543",
            vessel_type=30,
            length=100,
            width=20,
            draught=5.5,
            latitude=65.0,
            longitude=10.0,
            heading=0,
            course=0,
            speed=10.0,
            destination=None,
            eta=None,
            status="Underway using engine",
            source_time="2026-10-30T17:20:00Z",
            last_seen=datetime.now(UTC),
        )

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        coordinator.data = {"123456789": sample_vessel_data}
        coordinator._entry = entry
        coordinator._watchlist_vessels = {"987654321": watched_vessel}
        coordinator._status_tracker = MagicMock()
        coordinator._status_tracker.stale_timeout = 3600

        snapshot = _build_bounded_snapshot(coordinator, page=1)

        # Two vessels: one in area, one watched.
        assert snapshot.total_count == 2
        assert len(snapshot.vessels) == 2

        # Find and check watched vessel.
        watched_snap = next((v for v in snapshot.vessels if v.mmsi == "987654321"), None)
        assert watched_snap is not None
        assert watched_snap.is_watched is True


class TestBoundedTrail:
    """Test bounded trail history retrieval."""

    @pytest.mark.asyncio
    async def test_get_bounded_trail_basic(self, hass: HomeAssistant):
        """Test basic trail retrieval."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        coordinator._position_history = {
            "123456789": [
                {
                    "latitude": 60.5,
                    "longitude": 5.5,
                    "timestamp": datetime.now(UTC) - timedelta(minutes=5),
                },
                {
                    "latitude": 60.51,
                    "longitude": 5.51,
                    "timestamp": datetime.now(UTC),
                },
            ]
        }

        trail = _get_bounded_trail(coordinator, "123456789")

        assert len(trail) == 2
        assert trail[0].lat == 60.5
        assert trail[0].lon == 5.5
        assert trail[1].lat == 60.51
        assert trail[1].lon == 5.51

    @pytest.mark.asyncio
    async def test_get_bounded_trail_truncation(self, hass: HomeAssistant):
        """Test trail point truncation to MAX_TRAIL_POINTS."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        # Create more than MAX_TRAIL_POINTS.
        points = [
            {
                "latitude": 60.5 + (i * 0.001),
                "longitude": 5.5 + (i * 0.001),
                "timestamp": datetime.now(UTC) - timedelta(seconds=(100 - i) * 60),
            }
            for i in range(100)
        ]
        coordinator._position_history = {"123456789": points}

        trail = _get_bounded_trail(coordinator, "123456789")

        # Should be limited to MAX_TRAIL_POINTS.
        assert len(trail) <= MAX_TRAIL_POINTS
        # Most recent points should be included.
        assert trail[-1].timestamp > trail[0].timestamp

    @pytest.mark.asyncio
    async def test_get_bounded_trail_missing_vessel(self, hass: HomeAssistant):
        """Test trail retrieval for missing vessel."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        coordinator._position_history = {}

        trail = _get_bounded_trail(coordinator, "nonexistent")

        assert len(trail) == 0

    @pytest.mark.asyncio
    async def test_get_bounded_trail_invalid_points(self, hass: HomeAssistant):
        """Test trail with invalid/malformed points."""
        entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
        entry.add_to_hass(hass)

        coordinator = MagicMock(spec=MarineTrafficCoordinator)
        coordinator._position_history = {
            "123456789": [
                # Valid point.
                {
                    "latitude": 60.5,
                    "longitude": 5.5,
                    "timestamp": datetime.now(UTC),
                },
                # Missing latitude.
                {"longitude": 5.5, "timestamp": datetime.now(UTC)},
                # Missing timestamp.
                {"latitude": 60.5, "longitude": 5.5},
                # Non-numeric values.
                {
                    "latitude": "bad",
                    "longitude": 5.5,
                    "timestamp": datetime.now(UTC),
                },
            ]
        }

        trail = _get_bounded_trail(coordinator, "123456789")

        # Only one valid point should be returned.
        assert len(trail) == 1
        assert trail[0].lat == 60.5
        assert trail[0].lon == 5.5


class TestWebSocketHandlers:
    """Test WebSocket message handlers."""

    @pytest.mark.asyncio
    async def test_handler_invalid_entry(self, mock_connection):
        """Test handler with invalid entry_id."""
        from custom_components.marinetraffic_tracker.websocket_api import (
            _async_handle_get_snapshot,
        )

        hass = MagicMock()
        hass.data = {DOMAIN: {}}

        msg = {"id": 1, "entry_id": "nonexistent"}
        await _async_handle_get_snapshot(hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once()
        args = mock_connection.send_error.call_args[0]
        assert args[1] == ERROR_INVALID_ENTRY

    @pytest.mark.asyncio
    async def test_handler_invalid_request(self, mock_connection):
        """Test handler with missing required parameters."""
        from custom_components.marinetraffic_tracker.websocket_api import (
            _async_handle_get_snapshot,
        )

        hass = MagicMock()
        msg = {"id": 1}  # Missing entry_id.
        await _async_handle_get_snapshot(hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once()
        args = mock_connection.send_error.call_args[0]
        assert args[1] == ERROR_INVALID_REQUEST

    @pytest.mark.asyncio
    async def test_handler_error_exception(self, mock_connection):
        """Test error handling in handler."""
        from custom_components.marinetraffic_tracker.websocket_api import (
            _async_handle_get_snapshot,
        )

        hass = MagicMock()
        hass.data = {DOMAIN: {}}

        # Cause an exception in the handler.
        msg = {"id": 1, "entry_id": "entry1"}
        with patch("custom_components.marinetraffic_tracker.websocket_api._get_coordinator") as mock_get:
            mock_get.side_effect = RuntimeError("Unexpected error")
            await _async_handle_get_snapshot(hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once()
        args = mock_connection.send_error.call_args[0]
        assert args[1] == ERROR_INTERNAL
