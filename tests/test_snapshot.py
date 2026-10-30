"""Tests for shared snapshot and observation metadata (Phase 1.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.marinetraffic_tracker.client import VesselData


@pytest.mark.asyncio
async def test_vessel_data_observation_metadata() -> None:
    """Test that VesselData properly tracks observation metadata.
    
    Verifies that source_msgtime (AIS message time) is kept distinct from
    observation_time (local reception time) and last_seen (coordinator timestamp).
    """
    now = datetime.now(UTC)
    
    vessel = VesselData(
        mmsi="123456789",
        name="Test Vessel",
        vessel_type=70,
        latitude=59.9,
        longitude=10.7,
        heading=45,
        course=45,
        speed=12.5,
        status="Under way",
        origin=None,
        destination="Oslo",
        eta=None,
        source="kystverket",
        source_msgtime="2024-01-15T10:00:00+00:00",
        observation_time=now,
        last_seen=now,
    )
    
    assert vessel.mmsi == "123456789"
    assert vessel.source_msgtime == "2024-01-15T10:00:00+00:00"
    assert vessel.observation_time == now
    assert vessel.last_seen == now


def test_vessel_data_with_defaults() -> None:
    """Test that VesselData can be created with default observation times."""
    now_before = datetime.now(UTC)
    
    vessel = VesselData(
        mmsi="123456789",
        name="Test Vessel",
        vessel_type=70,
        latitude=59.9,
        longitude=10.7,
        heading=45,
        course=45,
        speed=12.5,
        status="Under way",
        origin=None,
        destination="Oslo",
        eta=None,
        source="kystverket",
    )
    
    now_after = datetime.now(UTC)
    
    assert vessel.observation_time >= now_before
    assert vessel.observation_time <= now_after
    assert vessel.last_seen >= now_before
    assert vessel.last_seen <= now_after
    assert vessel.source_msgtime is None


@pytest.mark.asyncio
async def test_kystverket_client_get_snapshot_method_exists() -> None:
    """Test that KystverketClient has a get_snapshot method.
    
    This is a basic sanity check that the new Phase 1.1 method exists
    on the client and can be imported without errors.
    """
    from custom_components.marinetraffic_tracker.kystverket_client import KystverketClient
    
    # Verify method exists
    assert hasattr(KystverketClient, "get_snapshot")
    assert callable(getattr(KystverketClient, "get_snapshot"))


@pytest.mark.asyncio
async def test_kystverket_client_get_snapshot_returns_list() -> None:
    """Test that get_snapshot returns a list of VesselData.
    
    This test mocks the network call and verifies the happy path where
    a successful snapshot returns a list of vessels.
    """
    from custom_components.marinetraffic_tracker.kystverket_client import KystverketClient
    
    # Create mock session
    mock_session = MagicMock()
    
    client = KystverketClient(
        session=mock_session,
        client_id="test_id",
        client_secret="test_secret",
    )
    
    # Mock the token fetch
    with patch.object(client, "_get_access_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = "test_token"
        
        # Mock the payload fetch to return empty list
        with patch.object(
            client, "_fetch_payload_full", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = {"features": []}
            
            # Call get_snapshot
            result = await client.get_snapshot()
            
            # Verify result is a list
            assert isinstance(result, list)
            assert len(result) == 0


def test_vessel_data_source_msgtime_isolation() -> None:
    """Test that source_msgtime is distinct from msgtime and last_seen.
    
    This verifies the separation of concerns between:
    - source_msgtime: when the AIS message was created at the vessel/source
    - msgtime: legacy field, same value as source_msgtime
    - observation_time: local time we parsed it
    - last_seen: coordinator timestamp
    """
    source_time = "2024-01-15T10:00:00+00:00"
    observation = datetime(2024, 1, 15, 10, 1, 0, tzinfo=UTC)
    last_seen_time = datetime(2024, 1, 15, 10, 2, 0, tzinfo=UTC)
    
    vessel = VesselData(
        mmsi="123456789",
        name="Test Vessel",
        vessel_type=70,
        latitude=59.9,
        longitude=10.7,
        heading=45,
        course=45,
        speed=12.5,
        status="Under way",
        origin=None,
        destination="Oslo",
        eta=None,
        source="kystverket",
        msgtime=source_time,  # Legacy field
        source_msgtime=source_time,  # New field: source time as ISO string
        observation_time=observation,  # Local reception time
        last_seen=last_seen_time,  # Coordinator timestamp
    )
    
    # Verify all three timestamp concepts are distinct and preserved
    assert vessel.msgtime == source_time
    assert vessel.source_msgtime == source_time
    assert vessel.observation_time == observation
    assert vessel.last_seen == last_seen_time
    
    # Verify they're not accidentally aliased
    assert vessel.observation_time != vessel.last_seen
