"""Versioned persistence for per-entry vessel status baselines."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .vessel_events import VesselStatusBaseline

STORAGE_VERSION = 1
STORAGE_SAVE_DELAY = 2
_STORAGE_KEY = f"{DOMAIN}_status_baselines"


class VesselEventStorage:
    """Persist status baselines in Home Assistant's versioned storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{_STORAGE_KEY}_{entry_id}",
        )
        self._pending_data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, VesselStatusBaseline]:
        """Load and validate persisted baselines."""
        stored = await self._store.async_load()
        if stored is None:
            return {}
        if not isinstance(stored, dict) or not isinstance(stored.get("baselines"), dict):
            raise ValueError("Stored vessel status baselines have an invalid format")

        baselines: dict[str, VesselStatusBaseline] = {}
        for mmsi, data in stored["baselines"].items():
            if not isinstance(mmsi, str) or not mmsi.isdigit():
                raise ValueError("Stored vessel status baseline has an invalid MMSI")
            baselines[mmsi] = VesselStatusBaseline.from_dict(mmsi, data)
        return baselines

    def async_delay_save(self, baselines: dict[str, VesselStatusBaseline]) -> None:
        """Schedule a debounced save of the latest baseline snapshot."""
        self._pending_data = {
            "baselines": {mmsi: baseline.to_dict() for mmsi, baseline in baselines.items()}
        }
        self._store.async_delay_save(self._data_to_save, STORAGE_SAVE_DELAY)

    async def async_flush(self, baselines: dict[str, VesselStatusBaseline]) -> None:
        """Write current baselines before the config entry unloads."""
        data = {"baselines": {mmsi: baseline.to_dict() for mmsi, baseline in baselines.items()}}
        await self._store.async_save(data)

    def _data_to_save(self) -> dict[str, Any]:
        """Return the newest pending snapshot for Home Assistant's delayed writer."""
        if self._pending_data is None:
            return {"baselines": {}}
        return self._pending_data

    @classmethod
    async def async_remove_entry(cls, hass: HomeAssistant, entry_id: str) -> None:
        """Remove the persisted state for a deleted config entry."""
        store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{_STORAGE_KEY}_{entry_id}",
        )
        await store.async_remove()
