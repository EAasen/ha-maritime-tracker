"""Tests for per-entry versioned vessel status storage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.marinetraffic_tracker.storage import (
    STORAGE_SAVE_DELAY,
    STORAGE_VERSION,
    VesselEventStorage,
)
from custom_components.marinetraffic_tracker.vessel_events import VesselStatusBaseline


def _baseline(mmsi: str = "123456789") -> VesselStatusBaseline:
    return VesselStatusBaseline(
        mmsi=mmsi,
        status="Under Way Using Engine",
        source_msgtime="2026-10-30T12:00:00+00:00",
        observation_time=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        name="NORDIC STAR",
        source="kystverket",
        latitude=60.4,
        longitude=5.3,
    )


@pytest.mark.asyncio
async def test_load_restores_versioned_baselines() -> None:
    store = MagicMock()
    store.async_load = AsyncMock(return_value={"baselines": {"123456789": _baseline().to_dict()}})
    hass = MagicMock()

    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ) as store_factory:
        storage = VesselEventStorage(hass, "entry-1")
        restored = await storage.async_load()

    assert restored["123456789"] == _baseline()
    assert store_factory.call_args.args[1] == STORAGE_VERSION
    assert "entry-1" in store_factory.call_args.args[2]


@pytest.mark.asyncio
async def test_missing_storage_returns_empty_baselines() -> None:
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ):
        storage = VesselEventStorage(MagicMock(), "entry-1")
        assert await storage.async_load() == {}


@pytest.mark.asyncio
async def test_invalid_persisted_baseline_is_reported() -> None:
    store = MagicMock()
    store.async_load = AsyncMock(return_value={"baselines": {"123456789": {"status": "Moored"}}})
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ):
        storage = VesselEventStorage(MagicMock(), "entry-1")
        with pytest.raises(ValueError, match="Invalid baseline"):
            await storage.async_load()


def test_save_is_debounced_with_latest_baseline_snapshot() -> None:
    store = MagicMock()
    store.async_delay_save = MagicMock()
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ):
        storage = VesselEventStorage(MagicMock(), "entry-1")
        storage.async_delay_save({"123456789": _baseline()})
        storage.async_delay_save({"123456789": _baseline(), "987654321": _baseline("987654321")})

    assert store.async_delay_save.call_count == 2
    assert store.async_delay_save.call_args.args[1] == STORAGE_SAVE_DELAY
    assert store.async_delay_save.call_args.args[0]() == {
        "baselines": {
            "123456789": _baseline().to_dict(),
            "987654321": _baseline("987654321").to_dict(),
        }
    }


@pytest.mark.asyncio
async def test_flush_writes_all_baselines_immediately() -> None:
    store = MagicMock()
    store.async_save = AsyncMock()
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ):
        storage = VesselEventStorage(MagicMock(), "entry-1")
        await storage.async_flush({"123456789": _baseline()})

    store.async_save.assert_awaited_once_with({"baselines": {"123456789": _baseline().to_dict()}})


@pytest.mark.asyncio
async def test_delete_removes_only_the_requested_entry_storage() -> None:
    store = MagicMock()
    store.async_remove = AsyncMock()
    hass = MagicMock()
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ) as store_factory:
        await VesselEventStorage.async_remove_entry(hass, "entry-2")

    assert "entry-2" in store_factory.call_args.args[2]
    store.async_remove.assert_awaited_once()


def test_storage_keys_are_isolated_per_entry() -> None:
    stores = [MagicMock(), MagicMock()]
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        side_effect=stores,
    ) as store_factory:
        VesselEventStorage(MagicMock(), "entry-1")
        VesselEventStorage(MagicMock(), "entry-2")

    first_key = store_factory.call_args_list[0].args[2]
    second_key = store_factory.call_args_list[1].args[2]
    assert first_key != second_key
    assert "entry-1" in first_key
    assert "entry-2" in second_key


@pytest.mark.asyncio
async def test_storage_errors_are_not_silently_discarded() -> None:
    store = MagicMock()
    store.async_load = AsyncMock(side_effect=OSError("disk unavailable"))
    with patch(
        "custom_components.marinetraffic_tracker.storage.Store",
        return_value=store,
    ):
        storage = VesselEventStorage(MagicMock(), "entry-1")
        with pytest.raises(OSError, match="disk unavailable"):
            await storage.async_load()
