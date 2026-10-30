"""Versioned persistence for per-entry vessel status baselines and port calls."""

from __future__ import annotations

from typing import Any
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, MAX_PORT_CALL_ROWS
from .vessel_events import VesselStatusBaseline
from .port_calls import PortBaseline, PortCall

STORAGE_VERSION = 1
STORAGE_SAVE_DELAY = 2
_STORAGE_KEY = f"{DOMAIN}_status_baselines"
_PORT_STORAGE_KEY = f"{DOMAIN}_port_calls"


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


class PortEventStorage:
    """Persist port call baselines and bounded call history."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize port event storage.
        
        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID
        """
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{_PORT_STORAGE_KEY}_{entry_id}",
        )
        self._hass = hass
        self._entry_id = entry_id
        self._pending_data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, dict[str, PortBaseline]]:
        """Load and validate persisted port baselines.
        
        Returns:
            Dict of {port_id: {mmsi: PortBaseline}}
        """
        stored = await self._store.async_load()
        if stored is None:
            return {}
        
        if not isinstance(stored, dict) or not isinstance(stored.get("baselines"), dict):
            return {}
        
        baselines_dict: dict[str, dict[str, PortBaseline]] = {}
        
        for port_id, port_data in stored["baselines"].items():
            if not isinstance(port_data, dict):
                continue
            
            baselines_dict[port_id] = {}
            for mmsi, baseline_data in port_data.items():
                if not isinstance(mmsi, str) or not mmsi.isdigit():
                    continue
                try:
                    baseline = PortBaseline(
                        port_id=port_id,
                        mmsi=mmsi,
                        last_known_inside=bool(baseline_data.get("last_known_inside", False)),
                        last_known_timestamp=datetime.fromisoformat(
                            baseline_data["last_known_timestamp"]
                        ),
                        baseline_version=int(baseline_data.get("baseline_version", 1)),
                    )
                    baselines_dict[port_id][mmsi] = baseline
                except (ValueError, KeyError, TypeError) as e:
                    # Skip malformed entries
                    _LOGGER.warning(
                        "Failed to load port baseline for port %s, mmsi %s: %s",
                        port_id,
                        mmsi,
                        e,
                    )
                    continue
        
        return baselines_dict

    async def async_load_calls(self) -> dict[str, list[PortCall]]:
        """Load all persisted port calls.
        
        Returns:
            Dict of {port_id: [PortCall, ...]}
        """
        stored = await self._store.async_load()
        if stored is None:
            return {}
        
        if not isinstance(stored, dict) or not isinstance(stored.get("calls"), dict):
            return {}
        
        calls_dict: dict[str, list[PortCall]] = {}
        
        for port_id, port_calls in stored["calls"].items():
            if not isinstance(port_calls, list):
                continue
            
            calls_dict[port_id] = []
            for call_data in port_calls:
                if not isinstance(call_data, dict):
                    continue
                try:
                    call = PortCall(
                        port_id=port_id,
                        port_name=call_data["port_name"],
                        mmsi=call_data["mmsi"],
                        vessel_name=call_data.get("vessel_name"),
                        call_type=call_data["call_type"],
                        observed_at=datetime.fromisoformat(call_data["observed_at"]),
                        reported_eta=call_data.get("reported_eta"),
                        reported_destination=call_data.get("reported_destination"),
                        last_position=tuple(call_data.get("last_position", [0.0, 0.0])),
                    )
                    calls_dict[port_id].append(call)
                except (ValueError, KeyError, TypeError) as e:
                    _LOGGER.warning(
                        "Failed to load port call for port %s: %s",
                        port_id,
                        e,
                    )
                    continue
        
        return calls_dict

    async def async_save_baseline(
        self,
        port_id: str,
        mmsi: str,
        baseline: PortBaseline,
    ) -> None:
        """Save or update a vessel baseline for a port.
        
        Args:
            port_id: Port identifier
            mmsi: Vessel MMSI
            baseline: PortBaseline object
        """
        # Load current data
        stored = await self._store.async_load() or {}
        
        if "baselines" not in stored:
            stored["baselines"] = {}
        if port_id not in stored["baselines"]:
            stored["baselines"][port_id] = {}
        
        # Update baseline
        stored["baselines"][port_id][mmsi] = {
            "last_known_inside": baseline.last_known_inside,
            "last_known_timestamp": baseline.last_known_timestamp.isoformat(),
            "baseline_version": baseline.baseline_version,
        }
        
        # Schedule save
        self._pending_data = stored
        self._store.async_delay_save(self._data_to_save, STORAGE_SAVE_DELAY)

    async def async_save_call(
        self,
        call: PortCall,
    ) -> None:
        """Persist a confirmed port call.
        
        Args:
            call: PortCall object to save
        """
        # Load current data
        stored = await self._store.async_load() or {}
        
        if "calls" not in stored:
            stored["calls"] = {}
        if call.port_id not in stored["calls"]:
            stored["calls"][call.port_id] = []
        
        # Add new call
        stored["calls"][call.port_id].append({
            "port_name": call.port_name,
            "mmsi": call.mmsi,
            "vessel_name": call.vessel_name,
            "call_type": call.call_type,
            "observed_at": call.observed_at.isoformat(),
            "reported_eta": call.reported_eta,
            "reported_destination": call.reported_destination,
            "last_position": list(call.last_position),
        })
        
        # Enforce retention limits: keep only the most recent MAX_PORT_CALL_ROWS
        if len(stored["calls"][call.port_id]) > MAX_PORT_CALL_ROWS:
            stored["calls"][call.port_id] = stored["calls"][call.port_id][-MAX_PORT_CALL_ROWS:]
        
        # Schedule save
        self._pending_data = stored
        self._store.async_delay_save(self._data_to_save, STORAGE_SAVE_DELAY)

    async def async_get_recent_calls(
        self,
        port_id: str,
        hours: int = 24,
        limit: int = 50,
    ) -> list[PortCall]:
        """Retrieve recent calls for a port.
        
        Args:
            port_id: Port identifier
            hours: Look back window in hours
            limit: Maximum number of calls to return
        
        Returns:
            List of recent PortCall objects
        """
        calls_dict = await self.async_load_calls()
        port_calls = calls_dict.get(port_id, [])
        
        # Filter by time window and limit
        now = datetime.now()
        recent_calls = []
        
        for call in reversed(port_calls):  # Most recent first
            age_hours = (now - call.observed_at).total_seconds() / 3600
            if age_hours <= hours:
                recent_calls.append(call)
                if len(recent_calls) >= limit:
                    break
        
        return list(reversed(recent_calls))  # Chronological order

    async def async_clear_port(self, port_id: str) -> None:
        """Clear all data for a port (e.g., on port deletion).
        
        Args:
            port_id: Port identifier to clear
        """
        # Load current data
        stored = await self._store.async_load() or {}
        
        # Remove port from baselines and calls
        if "baselines" in stored and port_id in stored["baselines"]:
            del stored["baselines"][port_id]
        if "calls" in stored and port_id in stored["calls"]:
            del stored["calls"][port_id]
        
        # Save immediately
        self._pending_data = stored
        await self._store.async_save(stored)

    async def async_flush(
        self,
        baselines_dict: dict[str, dict[str, PortBaseline]] | None = None,
    ) -> None:
        """Write current state before config entry unloads.
        
        Args:
            baselines_dict: Optional dict of baselines to save
        """
        stored = await self._store.async_load() or {"baselines": {}, "calls": {}}
        
        if baselines_dict:
            stored["baselines"] = {
                port_id: {
                    mmsi: {
                        "last_known_inside": baseline.last_known_inside,
                        "last_known_timestamp": baseline.last_known_timestamp.isoformat(),
                        "baseline_version": baseline.baseline_version,
                    }
                    for mmsi, baseline in port_baselines.items()
                }
                for port_id, port_baselines in baselines_dict.items()
            }
        
        await self._store.async_save(stored)

    def _data_to_save(self) -> dict[str, Any]:
        """Return the newest pending snapshot for Home Assistant's delayed writer."""
        if self._pending_data is None:
            return {"baselines": {}, "calls": {}}
        return self._pending_data

    @classmethod
    async def async_remove_entry(cls, hass: HomeAssistant, entry_id: str) -> None:
        """Remove persisted port data for a deleted config entry.
        
        Args:
            hass: Home Assistant instance
            entry_id: Config entry ID
        """
        store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{_PORT_STORAGE_KEY}_{entry_id}",
        )
        await store.async_remove()

