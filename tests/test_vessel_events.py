"""Tests for reliable AIS status-transition detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.marinetraffic_tracker.client import VesselData
from custom_components.marinetraffic_tracker.const import (
    CONF_FILTER_VESSEL_TYPES,
    CONF_STALE_TIMEOUT,
    CONF_TRACKING_MODE,
    CONF_UPDATE_INTERVAL,
    EVENT_VESSEL_STATUS_CHANGED,
    TRACKING_MODE_RADIUS,
)
from custom_components.marinetraffic_tracker.coordinator import MarineTrafficCoordinator
from custom_components.marinetraffic_tracker.vessel_events import (
    VesselEventTracker,
    VesselStatusBaseline,
)

_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _vessel(
    *,
    status: str | None = "Under Way Using Engine",
    source_time: datetime | None = _NOW - timedelta(seconds=1),
    observation_time: datetime = _NOW,
    mmsi: str = "123456789",
    vessel_type: int = 70,
) -> VesselData:
    return VesselData(
        mmsi=mmsi,
        name="NORDIC STAR",
        vessel_type=vessel_type,
        latitude=60.4,
        longitude=5.3,
        heading=90,
        course=90,
        speed=10.0,
        status=status,
        origin=None,
        destination=None,
        eta=None,
        source_msgtime=source_time.isoformat() if source_time else None,
        observation_time=observation_time,
        source="kystverket",
    )


def test_first_observation_establishes_baseline_without_event() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600)

    transition, changed = tracker.observe(_vessel(), _NOW)

    assert transition is None
    assert changed
    assert tracker.baselines["123456789"].status == "Under Way Using Engine"


def test_status_change_fires_once_with_entry_and_observation_data() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600)
    tracker.observe(_vessel(), _NOW)
    next_time = _NOW + timedelta(seconds=30)
    changed = _vessel(
        status="Moored",
        source_time=_NOW + timedelta(seconds=29),
        observation_time=next_time,
    )

    transition, saved = tracker.observe(changed, next_time)
    repeated, repeated_saved = tracker.observe(changed, next_time)

    assert transition is not None
    assert transition.old_status == "Under Way Using Engine"
    assert transition.new_status == "Moored"
    assert transition.as_event_data("entry-1") == {
        "entry_id": "entry-1",
        "mmsi": "123456789",
        "name": "NORDIC STAR",
        "old_status": "Under Way Using Engine",
        "new_status": "Moored",
        "source_msgtime": changed.source_msgtime,
        "observation_time": next_time.isoformat(),
        "source": "kystverket",
        "position": {"latitude": 60.4, "longitude": 5.3},
    }
    assert saved
    assert repeated is None
    assert not repeated_saved


def test_out_of_order_source_message_does_not_change_baseline() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600)
    tracker.observe(_vessel(), _NOW)
    before = tracker.baselines["123456789"]

    transition, changed = tracker.observe(
        _vessel(
            status="Moored",
            source_time=_NOW - timedelta(seconds=2),
            observation_time=_NOW + timedelta(seconds=10),
        ),
        _NOW + timedelta(seconds=10),
    )

    assert transition is None
    assert not changed
    assert tracker.baselines["123456789"] == before


def test_unknown_status_invalidates_then_next_valid_observation_rebaselines() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600)
    tracker.observe(_vessel(), _NOW)

    unknown_time = _NOW + timedelta(seconds=10)
    transition, changed = tracker.observe(
        _vessel(
            status="Unknown",
            source_time=unknown_time - timedelta(seconds=1),
            observation_time=unknown_time,
        ),
        unknown_time,
    )
    baseline = tracker.baselines["123456789"]

    assert transition is None
    assert changed
    assert baseline.status is None
    assert not baseline.continuity_valid

    valid_time = unknown_time + timedelta(seconds=10)
    transition, _ = tracker.observe(
        _vessel(
            status="Moored",
            source_time=valid_time - timedelta(seconds=1),
            observation_time=valid_time,
        ),
        valid_time,
    )
    assert transition is None
    assert tracker.baselines["123456789"].continuity_valid


def test_stale_gap_rebaselines_without_transition() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=60)
    tracker.observe(_vessel(), _NOW)
    next_time = _NOW + timedelta(seconds=61)

    transition, changed = tracker.observe(
        _vessel(
            status="Moored",
            source_time=next_time - timedelta(seconds=1),
            observation_time=next_time,
        ),
        next_time,
    )

    assert transition is None
    assert changed
    assert tracker.baselines["123456789"].status == "Moored"


def test_stale_source_message_invalidates_continuity() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=60)
    tracker.observe(_vessel(), _NOW)

    transition, changed = tracker.observe(
        _vessel(
            status="Moored",
            source_time=_NOW - timedelta(seconds=90),
            observation_time=_NOW + timedelta(seconds=10),
        ),
        _NOW + timedelta(seconds=10),
    )

    assert transition is None
    assert changed
    assert not tracker.baselines["123456789"].continuity_valid


def test_future_source_message_invalidates_continuity() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600)
    tracker.observe(_vessel(), _NOW)

    transition, changed = tracker.observe(
        _vessel(
            status="Moored",
            source_time=_NOW + timedelta(minutes=6),
            observation_time=_NOW + timedelta(seconds=10),
        ),
        _NOW + timedelta(seconds=10),
    )

    assert transition is None
    assert changed
    assert not tracker.baselines["123456789"].continuity_valid


def test_missing_source_time_uses_local_observation_time() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600)
    tracker.observe(_vessel(source_time=None), _NOW)
    next_time = _NOW + timedelta(seconds=10)

    transition, _ = tracker.observe(
        _vessel(status="Moored", source_time=None, observation_time=next_time),
        next_time,
    )

    assert transition is not None
    assert transition.source_msgtime is None


def test_baseline_limit_evicts_oldest_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=600, max_baselines=2)
    tracker.observe(_vessel(mmsi="111111111"), _NOW)
    tracker.observe(
        _vessel(mmsi="222222222", source_time=_NOW, observation_time=_NOW + timedelta(seconds=1)),
        _NOW + timedelta(seconds=1),
    )
    tracker.observe(
        _vessel(mmsi="333333333", source_time=_NOW, observation_time=_NOW + timedelta(seconds=2)),
        _NOW + timedelta(seconds=2),
    )

    assert set(tracker.baselines) == {"222222222", "333333333"}
    assert "Evicted oldest status baseline" in caplog.text


def test_restore_expires_stale_baseline() -> None:
    tracker = VesselEventTracker("entry-1", stale_timeout=60)
    baseline = VesselStatusBaseline(
        mmsi="123456789",
        status="Moored",
        source_msgtime=None,
        observation_time=_NOW - timedelta(seconds=61),
        name="NORDIC STAR",
        source="kystverket",
        latitude=60.4,
        longitude=5.3,
    )

    changed = tracker.restore({"123456789": baseline}, _NOW)

    assert changed
    assert tracker.baselines == {}


def test_restored_baseline_preserves_transition_continuity() -> None:
    first_tracker = VesselEventTracker("entry-1", stale_timeout=600)
    first_tracker.observe(_vessel(), _NOW)
    restored_tracker = VesselEventTracker("entry-1", stale_timeout=600)
    restored_tracker.restore(first_tracker.baselines, _NOW + timedelta(seconds=10))
    next_time = _NOW + timedelta(seconds=20)

    transition, _ = restored_tracker.observe(
        _vessel(
            status="Moored",
            source_time=next_time - timedelta(seconds=1),
            observation_time=next_time,
        ),
        next_time,
    )

    assert transition is not None
    assert transition.old_status == "Under Way Using Engine"


@pytest.mark.asyncio
async def test_coordinator_emits_status_event_before_display_filters() -> None:
    hass = MagicMock()
    hass.bus.async_fire = MagicMock()
    client = MagicMock()
    first_time = datetime.now(UTC)
    first = _vessel(
        source_time=first_time - timedelta(seconds=1),
        observation_time=first_time,
    )
    client.get_vessels_in_radius = AsyncMock(return_value=[first])
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        CONF_UPDATE_INTERVAL: 60,
        CONF_STALE_TIMEOUT: 600,
        CONF_TRACKING_MODE: TRACKING_MODE_RADIUS,
        "latitude": 60.4,
        "longitude": 5.3,
        "radius_km": 50,
    }
    entry.options = {CONF_FILTER_VESSEL_TYPES: ["80"]}
    coordinator = MarineTrafficCoordinator(hass, entry, client)

    await coordinator._async_update_data()
    next_time = first_time + timedelta(seconds=30)
    client.get_vessels_in_radius.return_value = [
        _vessel(
            status="Moored",
            source_time=next_time - timedelta(seconds=1),
            observation_time=next_time,
        )
    ]
    result = await coordinator._async_update_data()

    status_events = [
        call
        for call in hass.bus.async_fire.call_args_list
        if call.args[0] == EVENT_VESSEL_STATUS_CHANGED
    ]
    assert len(status_events) == 1
    assert status_events[0].args[1]["entry_id"] == "entry-1"
    assert status_events[0].args[1]["old_status"] == "Under Way Using Engine"
    assert status_events[0].args[1]["new_status"] == "Moored"
    assert "123456789" not in result
