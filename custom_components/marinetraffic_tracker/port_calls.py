"""Port call tracking and geofence membership for maritime vessel monitoring.

This module tracks vessel entry and exit from defined geofences (ports) with
hysteresis confirmation: two consecutive fresh observations must confirm a
boundary crossing to emit a port call event.

Key features:
- Circular geofences defined by center coordinates and radius
- Hysteresis logic to filter boundary jitter
- Stale gap handling (does not fabricate calls on resume)
- Persistence of baselines across restarts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from math import cos, radians, sqrt
from typing import Literal

from .const import PORT_RECENT_CALL_HOURS

_LOGGER = logging.getLogger(__name__)

# Haversine approximation: 1 degree of latitude ≈ 111 km
_KM_PER_DEGREE_LAT = 111.0


@dataclass
class PortBaseline:
    """Last known vessel state for a port geofence.

    Used to resume tracking on restart without fabricating false calls.
    """

    port_id: str
    mmsi: str
    last_known_inside: bool  # Was vessel inside on last session?
    last_known_timestamp: datetime
    baseline_version: int = 1


@dataclass
class PortCall:
    """Confirmed port entry/exit event.

    Only emitted after hysteresis confirmation (two consecutive observations
    confirming the same boundary crossing).
    """

    port_id: str
    port_name: str
    mmsi: str
    vessel_name: str | None
    call_type: Literal["arrival", "departure"]
    observed_at: datetime
    reported_eta: str | None = None
    reported_destination: str | None = None
    last_position: tuple[float, float] = (0.0, 0.0)

    def as_dict(self) -> dict:
        """Export as a dictionary for event firing."""
        return {
            "port_id": self.port_id,
            "port_name": self.port_name,
            "mmsi": self.mmsi,
            "vessel_name": self.vessel_name,
            "call_type": self.call_type,
            "observed_at": self.observed_at.isoformat(),
            "reported_eta": self.reported_eta,
            "reported_destination": self.reported_destination,
            "last_position": self.last_position,
        }


class PortCallTracker:
    """Tracks vessel entry/exit from port geofences with hysteresis.

    Algorithm:
    1. For each vessel and port, calculate if vessel is inside geofence
    2. Compare with last known state (from baseline or pending state)
    3. If state is same as baseline → no call yet
    4. If state differs from baseline (first transition) → mark as pending
    5. If second observation confirms same new state → emit call + update baseline
    6. If second observation moves closer to boundary → ignore (jitter)
    7. If gap > 24h → clear pending, don't fabricate call on resume

    This ensures:
    - No duplicate calls from repeated messages
    - No fabricated calls from stale gaps or restarts
    - No false positives from boundary jitter
    """

    def __init__(self) -> None:
        """Initialize the port call tracker."""
        # Track pending state transitions: (port_id, mmsi) -> (inside, timestamp)
        self._pending_transitions: dict[tuple[str, str], tuple[bool, datetime]] = {}

    def check_vessel(
        self,
        vessel,
        ports: list[dict],
        baselines: dict[str, dict[str, PortBaseline]] | None = None,
    ) -> list[PortCall]:
        """Check if vessel crosses any port boundary.

        Returns confirmed calls (list may be empty, or contain 1–2 calls
        if vessel enters one port while leaving another).

        Args:
            vessel: VesselData object with lat/lon and AIS attributes
            ports: List of port dicts with id, name, latitude, longitude, radius_km
            baselines: Optional dict of {port_id: {mmsi: PortBaseline}}

        Returns:
            List of confirmed PortCall objects (may be empty)
        """
        calls: list[PortCall] = []

        if not ports or vessel is None:
            return calls

        if baselines is None:
            baselines = {}

        vessel_lat = float(vessel.get("latitude", 0))
        vessel_lon = float(vessel.get("longitude", 0))
        vessel_mmsi = str(vessel.get("mmsi", ""))
        vessel_name = vessel.get("vessel_name")
        vessel_timestamp = vessel.get("msgtime")  # Message timestamp

        if not vessel_mmsi or vessel_timestamp is None:
            return calls

        # Check each port
        for port in ports:
            port_id = port.get("id")
            port_name = port.get("name", "Unknown Port")

            if not port_id:
                continue

            # Check if vessel is inside this port's geofence
            is_inside = self._is_inside_geofence(
                vessel_lat,
                vessel_lon,
                float(port.get("latitude", 0)),
                float(port.get("longitude", 0)),
                float(port.get("radius_km", 1.0)),
            )

            # Get baseline state for this (port, vessel)
            baseline = baselines.get(port_id, {}).get(vessel_mmsi)

            # Determine if we should emit a call
            call = self._check_transition(
                port_id,
                port_name,
                vessel_mmsi,
                vessel_name,
                is_inside,
                vessel_timestamp,
                baseline,
                (vessel_lat, vessel_lon),
                vessel,
            )

            if call:
                calls.append(call)

        return calls

    def _check_transition(
        self,
        port_id: str,
        port_name: str,
        mmsi: str,
        vessel_name: str | None,
        is_inside: bool,
        observation_time: datetime,
        baseline: PortBaseline | None,
        position: tuple[float, float],
        vessel: dict,
    ) -> PortCall | None:
        """Check if a boundary crossing is confirmed and emit call if so.

        Args:
            port_id: Port identifier
            port_name: Human-readable port name
            mmsi: Vessel MMSI
            vessel_name: Vessel name
            is_inside: Whether vessel is currently inside geofence
            observation_time: Time of this observation
            baseline: Last known state from previous session
            position: Current vessel position (lat, lon)
            vessel: Full vessel data dict

        Returns:
            PortCall if confirmed transition, None otherwise
        """
        key = (port_id, mmsi)

        # Determine the last known state
        if baseline:
            last_known_inside = baseline.last_known_inside
        else:
            # No baseline: assume vessel was outside
            last_known_inside = False

        # Get pending state if one exists
        pending_inside, pending_time = self._pending_transitions.get(key, (None, None))

        # Case 1: No state change → no call
        if is_inside == last_known_inside and pending_inside is None:
            return None

        # Case 2: Gap handling (stale observation)
        if pending_inside is not None:
            gap_hours = (observation_time - pending_time).total_seconds() / 3600
            if gap_hours > PORT_RECENT_CALL_HOURS:
                # Gap too large: clear pending, don't fabricate call
                del self._pending_transitions[key]
                return None

        # Case 3: First observation of transition
        if pending_inside is None and is_inside != last_known_inside:
            # Record as pending and wait for confirmation
            self._pending_transitions[key] = (is_inside, observation_time)
            return None

        # Case 4: Confirmation of transition
        if pending_inside == is_inside:
            # Second observation confirms the same new state
            del self._pending_transitions[key]

            # Determine call type
            call_type: Literal["arrival", "departure"] = "arrival" if is_inside else "departure"

            # Extract reported ETA/destination
            reported_eta = vessel.get("eta")
            reported_destination = vessel.get("destination")

            return PortCall(
                port_id=port_id,
                port_name=port_name,
                mmsi=mmsi,
                vessel_name=vessel_name,
                call_type=call_type,
                observed_at=observation_time,
                reported_eta=reported_eta,
                reported_destination=reported_destination,
                last_position=position,
            )

        # Case 5: Boundary jitter (second observation closer to boundary)
        if pending_inside is not None and is_inside != pending_inside:
            # Vessel moved back towards the boundary (jitter)
            # Clear pending and ignore
            del self._pending_transitions[key]
            return None

        return None

    @staticmethod
    def _is_inside_geofence(
        vessel_lat: float,
        vessel_lon: float,
        center_lat: float,
        center_lon: float,
        radius_km: float,
    ) -> bool:
        """Check if a vessel is inside a circular geofence.

        Uses simplified Haversine: 1 degree ≈ 111 km.
        Accounts for longitude scaling at latitude.

        Args:
            vessel_lat: Vessel latitude (degrees)
            vessel_lon: Vessel longitude (degrees)
            center_lat: Geofence center latitude (degrees)
            center_lon: Geofence center longitude (degrees)
            radius_km: Geofence radius (km)

        Returns:
            True if vessel is inside the geofence, False otherwise
        """
        delta_lat_km = (vessel_lat - center_lat) * _KM_PER_DEGREE_LAT

        # Account for longitude scaling: cos(latitude) compression
        lon_scale = cos(radians(center_lat))
        delta_lon_km = (vessel_lon - center_lon) * _KM_PER_DEGREE_LAT * lon_scale

        distance_km = sqrt(delta_lat_km**2 + delta_lon_km**2)

        return distance_km <= radius_km

    def clear_pending(self, port_id: str | None = None, mmsi: str | None = None) -> None:
        """Clear pending state transitions (e.g., on port deletion or config edit).

        Args:
            port_id: Optional port to clear. If None, clears all ports.
            mmsi: Optional MMSI to clear. If None, clears all vessels.
        """
        keys_to_remove = []

        for key in self._pending_transitions:
            key_port_id, key_mmsi = key

            if port_id and key_port_id != port_id:
                continue
            if mmsi and key_mmsi != mmsi:
                continue

            keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._pending_transitions[key]
