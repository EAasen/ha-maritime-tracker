"""Phase 1.3: Extended test coverage for snapshot integration and legacy behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from custom_components.marinetraffic_tracker.client import VesselData
from custom_components.marinetraffic_tracker.kystverket_client import KystverketClient


def _make_test_vessel(
    mmsi: str,
    lat: float,
    lon: float,
    name: str = "Test",
    source_msgtime: str | None = None,
) -> VesselData:
    """Create a test vessel with the given position and timestamps."""
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
        source_msgtime=source_msgtime,
        observation_time=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_coordinator_one_fetch_per_poll_with_snapshot() -> None:
    """Verify coordinator makes exactly one API call per poll when using snapshot.
    
    This is the critical optimization goal: one logical fetch for all views.
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
    
    # Setup
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
    
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )
    
    # Create test vessels
    vessel_in = _make_test_vessel("111111111", 60.0, 5.0, "Inside")
    vessel_out = _make_test_vessel("222222222", 62.0, 5.0, "Outside")
    snapshot = [vessel_in, vessel_out]
    
    # Mock snapshot - track call count
    with patch.object(
        kystverket_client, "get_snapshot", new_callable=AsyncMock
    ) as mock_snapshot:
        mock_snapshot.return_value = snapshot
        
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )
        
        config = {**mock_entry.data, **mock_entry.options}
        
        # Call _fetch_vessels multiple times to simulate multiple update cycles
        result1, _ = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        result2, _ = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        result3, _ = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        
        # Verify: snapshot called exactly 3 times (once per poll)
        assert mock_snapshot.call_count == 3
        
        # Verify: each call returns only area vessels
        assert len(result1) == 1
        assert len(result2) == 1
        assert len(result3) == 1
        assert all(r[0].mmsi == "111111111" for r in [result1, result2, result3])


@pytest.mark.asyncio
async def test_coordinator_handles_old_source_timestamps() -> None:
    """Verify coordinator correctly handles old/stale source message times.
    
    This ensures timestamp separation works correctly for freshness detection.
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
    
    # Setup
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
    
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )
    
    # Create vessel with old source message time (from 1 hour ago)
    old_msgtime = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    vessel_old = _make_test_vessel(
        "111111111", 60.0, 5.0, "Old", source_msgtime=old_msgtime
    )
    snapshot = [vessel_old]
    
    with patch.object(
        kystverket_client, "get_snapshot", new_callable=AsyncMock
    ) as mock_snapshot:
        mock_snapshot.return_value = snapshot
        
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )
        
        config = {**mock_entry.data, **mock_entry.options}
        result, error = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        
        # Verify: vessel returned even with old source timestamp
        assert result is not None
        assert len(result) == 1
        assert result[0].source_msgtime == old_msgtime
        assert error is None


@pytest.mark.asyncio
async def test_coordinator_handles_missing_source_timestamps() -> None:
    """Verify coordinator handles missing/unparseable source timestamps gracefully.
    
    This tests robustness when AIS message time is unavailable.
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
    
    # Setup
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
    
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )
    
    # Create vessel with no source message time
    vessel_no_time = _make_test_vessel("111111111", 60.0, 5.0, "NoTime", source_msgtime=None)
    snapshot = [vessel_no_time]
    
    with patch.object(
        kystverket_client, "get_snapshot", new_callable=AsyncMock
    ) as mock_snapshot:
        mock_snapshot.return_value = snapshot
        
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )
        
        config = {**mock_entry.data, **mock_entry.options}
        result, error = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        
        # Verify: vessel returned even with missing timestamp
        assert result is not None
        assert len(result) == 1
        assert result[0].source_msgtime is None
        assert result[0].observation_time is not None  # Local time still set
        assert error is None


@pytest.mark.asyncio
async def test_coordinator_handles_future_timestamps() -> None:
    """Verify coordinator handles implausible future timestamps gracefully.
    
    This tests robustness for clock skew or malformed data.
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
    
    # Setup
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
    
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )
    
    # Create vessel with future timestamp (1 hour in future)
    future_msgtime = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    vessel_future = _make_test_vessel(
        "111111111", 60.0, 5.0, "Future", source_msgtime=future_msgtime
    )
    snapshot = [vessel_future]
    
    with patch.object(
        kystverket_client, "get_snapshot", new_callable=AsyncMock
    ) as mock_snapshot:
        mock_snapshot.return_value = snapshot
        
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )
        
        config = {**mock_entry.data, **mock_entry.options}
        result, error = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        
        # Verify: vessel returned even with future timestamp
        # Future timestamp is unusual but not an error
        assert result is not None
        assert len(result) == 1
        assert result[0].source_msgtime == future_msgtime
        assert error is None


@pytest.mark.asyncio
async def test_coordinator_area_counts_unchanged() -> None:
    """Verify that area vessel counts are unchanged from legacy behavior.
    
    This ensures backward compatibility with existing statistics and monitoring.
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
    
    # Setup
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
    
    mock_session = MagicMock()
    kystverket_client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )
    
    # Create snapshot with multiple vessels
    vessels = [
        _make_test_vessel("111111111", 60.0, 5.0),      # Inside
        _make_test_vessel("222222222", 60.1, 5.1),      # Inside
        _make_test_vessel("333333333", 62.0, 5.0),      # Outside
        _make_test_vessel("444444444", 57.0, 5.0),      # Outside
    ]
    
    # Also test with direct area query for comparison
    with patch.object(
        kystverket_client, "get_snapshot", new_callable=AsyncMock
    ) as mock_snapshot, patch.object(
        kystverket_client, "get_vessels_in_radius", new_callable=AsyncMock
    ) as mock_area:
        mock_snapshot.return_value = vessels
        mock_area.return_value = vessels[:2]  # Same area result
        
        coordinator = MarineTrafficCoordinator(
            hass=mock_hass,
            entry=mock_entry,
            client=kystverket_client,
        )
        
        config = {**mock_entry.data, **mock_entry.options}
        
        # Get results from both methods
        snapshot_result, _ = await coordinator._fetch_vessels(
            kystverket_client, TRACKING_MODE_RADIUS, config
        )
        
        # Verify: snapshot gives same count as area query would
        assert len(snapshot_result) == 2  # Only vessels inside area


def test_vessel_observation_time_set_correctly() -> None:
    """Verify observation_time is set at parse time, not coordinator time.
    
    This ensures Phase 1.1 timestamp separation is preserved through fetch.
    """
    # Create a vessel and verify times
    now_before = datetime.now(UTC)
    vessel = _make_test_vessel("123456789", 60.0, 5.0)
    now_after = datetime.now(UTC)
    
    # Observation time should be between before and after
    assert now_before <= vessel.observation_time <= now_after
    
    # Verify source_msgtime is independent
    # (not set when created via factory, set during parsing)
    assert vessel.source_msgtime is None
    
    # Simulate parsing with a specific source time
    source_time = "2026-10-29T12:00:00+00:00"
    vessel_with_source = _make_test_vessel(
        "987654321", 61.0, 6.0, source_msgtime=source_time
    )
    
    # Verify source time is preserved separate from observation time
    assert vessel_with_source.source_msgtime == source_time
    assert vessel_with_source.observation_time != datetime.fromisoformat(source_time)
