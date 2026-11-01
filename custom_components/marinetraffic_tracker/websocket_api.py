"""WebSocket API for bounded maritime tracker dashboard transport.

Provides authenticated real-time vessel data, map updates, and port-board data
through WebSocket subscriptions. Manages paginated snapshots, bounded history,
live invalidations, and explicit error responses per-entry and per-subscription.

No large history payloads are stored in recorder-backed state; all data is
delivered through this API on demand with strict bounds.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import JSONEncoder

from .const import DOMAIN
from .coordinator import MarineTrafficCoordinator

_LOGGER = logging.getLogger(__name__)

# Maximum number of vessel snapshots in a single bounded response.
MAX_SNAPSHOT_ROWS = 100

# Maximum number of historical position points per vessel.
MAX_TRAIL_POINTS = 50

# Maximum number of recent port calls to return.
MAX_PORT_CALL_ROWS = 50

# Subscription types.
WS_TYPE_SUBSCRIBE = "subscribe"
WS_TYPE_UNSUBSCRIBE = "unsubscribe"
WS_TYPE_GET_SNAPSHOT = "get_snapshot"
WS_TYPE_GET_TRAIL = "get_trail"

# Response types.
WS_TYPE_SNAPSHOT = "snapshot"
WS_TYPE_TRAIL = "trail"
WS_TYPE_ERROR = "error"

# Error codes.
ERROR_INVALID_ENTRY = "invalid_entry"
ERROR_UNAUTHORIZED = "unauthorized"
ERROR_INVALID_MMSI = "invalid_mmsi"
ERROR_INVALID_REQUEST = "invalid_request"
ERROR_INTERNAL = "internal_error"


@dataclass
class VesselSnapshot:
    """Bounded vessel state for dashboard transport."""

    mmsi: str
    name: str | None
    position: tuple[float, float] | None
    heading: float | None
    course: float | None
    speed_knots: float | None
    draught_m: float | None
    destination: str | None
    eta: str | None
    status: str | None
    last_seen_at: datetime | None
    is_stale: bool = False
    is_watched: bool = False


@dataclass
class TrailPoint:
    """Single position point in a vessel trail."""

    lat: float
    lon: float
    timestamp: datetime


@dataclass
class BoundedSnapshot:
    """Paginated snapshot response for bounded transport."""

    entry_id: str
    timestamp: datetime
    vessels: list[VesselSnapshot] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = MAX_SNAPSHOT_ROWS
    has_next: bool = False


async def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the maritime tracker WebSocket API commands."""
    websocket_api.async_register_command(
        hass,
        WS_TYPE_SUBSCRIBE,
        _async_handle_subscribe,
    )
    websocket_api.async_register_command(
        hass,
        WS_TYPE_UNSUBSCRIBE,
        _async_handle_unsubscribe,
    )
    websocket_api.async_register_command(
        hass,
        WS_TYPE_GET_SNAPSHOT,
        _async_handle_get_snapshot,
    )
    websocket_api.async_register_command(
        hass,
        WS_TYPE_GET_TRAIL,
        _async_handle_get_trail,
    )


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> MarineTrafficCoordinator | None:
    """Get the coordinator for the given entry, or None if not found."""
    return hass.data.get(DOMAIN, {}).get(entry_id)


def _encode_response(data: Any) -> str:
    """Encode response data to JSON with datetime support."""
    return json.dumps(data, cls=JSONEncoder)


async def _async_handle_subscribe(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Handle subscribe command to receive live vessel updates."""
    try:
        entry_id = msg.get("entry_id")
        if not entry_id:
            connection.send_error(msg["id"], ERROR_INVALID_REQUEST, "entry_id required")
            return

        coordinator = _get_coordinator(hass, entry_id)
        if not coordinator:
            connection.send_error(msg["id"], ERROR_INVALID_ENTRY, f"Entry {entry_id} not found")
            return

        # Send initial snapshot.
        snapshot = _build_bounded_snapshot(coordinator, page=1)
        connection.send_result(
            msg["id"],
            _encode_response(asdict(snapshot)),
        )

        # Register for live updates from coordinator.
        def _on_update() -> None:
            """Send updated snapshot on coordinator update."""
            updated = _build_bounded_snapshot(coordinator, page=1)
            connection.send_message(
                {
                    "type": WS_TYPE_SNAPSHOT,
                    "data": asdict(updated),
                }
            )

        remove_listener = coordinator.async_add_listener(_on_update)

        @callback
        def _on_disconnect() -> None:
            """Clean up on WebSocket disconnect."""
            remove_listener()

        connection.subscriptions[msg["id"]] = _on_disconnect

    except Exception as err:
        _LOGGER.exception("Error in subscribe handler: %s", err)
        connection.send_error(msg["id"], ERROR_INTERNAL, str(err))


async def _async_handle_unsubscribe(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Handle unsubscribe command to stop receiving updates."""
    try:
        subscription_id = msg.get("subscription_id")
        if not subscription_id:
            connection.send_error(msg["id"], ERROR_INVALID_REQUEST, "subscription_id required")
            return

        # Remove the subscription cleanup callback.
        if subscription_id in connection.subscriptions:
            cleanup = connection.subscriptions.pop(subscription_id)
            cleanup()

        connection.send_result(msg["id"], {"success": True})

    except Exception as err:
        _LOGGER.exception("Error in unsubscribe handler: %s", err)
        connection.send_error(msg["id"], ERROR_INTERNAL, str(err))


async def _async_handle_get_snapshot(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Handle get_snapshot command for paginated vessel list."""
    try:
        entry_id = msg.get("entry_id")
        if not entry_id:
            connection.send_error(msg["id"], ERROR_INVALID_REQUEST, "entry_id required")
            return

        coordinator = _get_coordinator(hass, entry_id)
        if not coordinator:
            connection.send_error(msg["id"], ERROR_INVALID_ENTRY, f"Entry {entry_id} not found")
            return

        page = msg.get("page", 1)
        page_size = msg.get("page_size", MAX_SNAPSHOT_ROWS)
        page_size = min(page_size, MAX_SNAPSHOT_ROWS)

        snapshot = _build_bounded_snapshot(coordinator, page=page, page_size=page_size)
        connection.send_result(
            msg["id"],
            _encode_response(asdict(snapshot)),
        )

    except Exception as err:
        _LOGGER.exception("Error in get_snapshot handler: %s", err)
        connection.send_error(msg["id"], ERROR_INTERNAL, str(err))


async def _async_handle_get_trail(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Handle get_trail command for vessel position history."""
    try:
        entry_id = msg.get("entry_id")
        mmsi = msg.get("mmsi")
        if not entry_id or not mmsi:
            connection.send_error(msg["id"], ERROR_INVALID_REQUEST, "entry_id and mmsi required")
            return

        coordinator = _get_coordinator(hass, entry_id)
        if not coordinator:
            connection.send_error(msg["id"], ERROR_INVALID_ENTRY, f"Entry {entry_id} not found")
            return

        trail_points = _get_bounded_trail(coordinator, mmsi)
        connection.send_result(
            msg["id"],
            {
                "mmsi": mmsi,
                "points": [
                    {"lat": p.lat, "lon": p.lon, "timestamp": p.timestamp.isoformat()}
                    for p in trail_points
                ],
                "count": len(trail_points),
            },
        )

    except Exception as err:
        _LOGGER.exception("Error in get_trail handler: %s", err)
        connection.send_error(msg["id"], ERROR_INTERNAL, str(err))


def _build_bounded_snapshot(
    coordinator: MarineTrafficCoordinator,
    page: int = 1,
    page_size: int = MAX_SNAPSHOT_ROWS,
) -> BoundedSnapshot:
    """Build a paginated snapshot from coordinator data."""
    page = max(1, page)
    page_size = min(page_size, MAX_SNAPSHOT_ROWS)

    # Collect area vessels.
    area_vessels = list((coordinator.data or {}).values())
    # Collect watched vessels (if available).
    watched_vessels = getattr(coordinator, "_watchlist_vessels", {})
    watched_mmsis = {v.mmsi for v in watched_vessels.values()}

    # Combine and deduplicate.
    all_vessels_dict: dict[str, Any] = {v.mmsi: v for v in area_vessels}
    for v in watched_vessels.values():
        if v.mmsi not in all_vessels_dict:
            all_vessels_dict[v.mmsi] = v

    all_vessels = sorted(all_vessels_dict.values(), key=lambda v: v.mmsi or "")
    total_count = len(all_vessels)

    # Paginate.
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_vessels = all_vessels[start_idx:end_idx]

    # Build snapshots with stale detection.
    stale_timeout_sec = coordinator._status_tracker.stale_timeout
    now = datetime.now(UTC)
    snapshots = []

    for vessel in paginated_vessels:
        is_stale = False
        if vessel.last_seen:
            age_sec = (now - vessel.last_seen).total_seconds()
            is_stale = age_sec > stale_timeout_sec

        snapshot = VesselSnapshot(
            mmsi=vessel.mmsi or "unknown",
            name=vessel.name,
            position=(
                (vessel.latitude, vessel.longitude)
                if vessel.latitude is not None and vessel.longitude is not None
                else None
            ),
            heading=vessel.heading,
            course=vessel.course,
            speed_knots=vessel.speed,
            draught_m=vessel.draught,
            destination=vessel.destination,
            eta=vessel.eta,
            status=vessel.status,
            last_seen_at=vessel.last_seen,
            is_stale=is_stale,
            is_watched=vessel.mmsi in watched_mmsis,
        )
        snapshots.append(snapshot)

    return BoundedSnapshot(
        entry_id=coordinator._entry.entry_id,
        timestamp=now,
        vessels=snapshots,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=end_idx < total_count,
    )


def _get_bounded_trail(
    coordinator: MarineTrafficCoordinator,
    mmsi: str,
) -> list[TrailPoint]:
    """Get bounded position history for a vessel."""
    # Access position history from coordinator.
    position_history = getattr(coordinator, "_position_history", {})
    history_list = position_history.get(mmsi, [])

    # Limit to most recent points.
    limited = history_list[-MAX_TRAIL_POINTS:]

    trail = []
    for item in limited:
        if "latitude" in item and "longitude" in item and "timestamp" in item:
            try:
                ts = item["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                elif not isinstance(ts, datetime):
                    continue

                trail.append(
                    TrailPoint(
                        lat=float(item["latitude"]),
                        lon=float(item["longitude"]),
                        timestamp=ts,
                    )
                )
            except (ValueError, TypeError, KeyError):
                continue

    return trail
