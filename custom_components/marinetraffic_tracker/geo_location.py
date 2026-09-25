"""Geolocation platform for the Norwegian Maritime Tracker integration.

Publishes one transient ``geo_location`` entity per vessel currently inside the
tracked area.  Unlike the per-vessel ``device_tracker`` entities (which are
disabled by default to avoid entity-registry explosion), these entities carry
no unique ID, so Home Assistant never persists them in the entity registry or
the recorder.  They appear and disappear as vessels enter and leave the area,
which is exactly the lifecycle the Map card expects.

Map usage
---------
Add the source to a Map card to see every tracked vessel without enabling a
single entity manually::

    type: map
    geo_location_sources:
      - marinetraffic_tracker
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import VesselData, _haversine_km
from .const import (
    ATTR_COURSE,
    ATTR_DESTINATION,
    ATTR_HEADING,
    ATTR_LAST_SEEN,
    ATTR_MMSI,
    ATTR_SPEED,
    ATTR_STATUS,
    ATTR_VESSEL_NAME,
    ATTR_VESSEL_TYPE,
    DEFAULT_VESSEL_ICON,
    DOMAIN,
    GEO_LOCATION_SOURCE,
    VESSEL_TYPE_ICONS,
    VESSEL_TYPE_MAP,
)
from .coordinator import MarineTrafficCoordinator
from .geo_filter import area_centre_and_radius

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up geolocation entities from a config entry."""
    coordinator: MarineTrafficCoordinator = hass.data[DOMAIN][entry.entry_id]
    area = area_centre_and_radius({**entry.data, **entry.options})
    if area is None:
        _LOGGER.warning("Tracked area is not configured; vessel map markers disabled")
        return
    centre_lat, centre_lon, _ = area

    entities: dict[str, MarineTrafficVesselLocation] = {}

    @callback
    def _handle_coordinator_update() -> None:
        """Add entities for new vessels and remove those that have left."""
        vessels: dict[str, VesselData] = coordinator.data or {}

        new_entities = [
            MarineTrafficVesselLocation(coordinator, mmsi, centre_lat, centre_lon)
            for mmsi in set(vessels) - set(entities)
        ]
        for entity in new_entities:
            entities[entity.mmsi] = entity
        if new_entities:
            _LOGGER.debug("Adding %d vessel geolocation entity/entities", len(new_entities))
            async_add_entities(new_entities)

        for mmsi in set(entities) - set(vessels):
            hass.async_create_task(entities.pop(mmsi).async_remove())

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))
    _handle_coordinator_update()


class MarineTrafficVesselLocation(GeolocationEvent):
    """A transient map marker for one AIS-tracked vessel.

    Deliberately has no unique ID: geolocation events are ephemeral by design
    and must not accumulate in the entity registry.
    """

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: MarineTrafficCoordinator,
        mmsi: str,
        centre_lat: float,
        centre_lon: float,
    ) -> None:
        """Initialise the marker for the given MMSI."""
        self._coordinator = coordinator
        self._mmsi = mmsi
        self._centre_lat = centre_lat
        self._centre_lon = centre_lon

    @property
    def mmsi(self) -> str:
        """Return the MMSI this marker represents."""
        return self._mmsi

    @property
    def source(self) -> str:
        """Return the value used in a Map card's ``geo_location_sources``."""
        return GEO_LOCATION_SOURCE

    @property
    def _vessel(self) -> VesselData | None:
        return (self._coordinator.data or {}).get(self._mmsi)

    async def async_added_to_hass(self) -> None:
        """Refresh the marker whenever the coordinator publishes new data."""
        self.async_on_remove(self._coordinator.async_add_listener(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        """Return True while the vessel is in the coordinator's active registry."""
        return self._coordinator.last_update_success and self._vessel is not None

    @property
    def name(self) -> str:
        """Return the vessel name, falling back to the MMSI when unknown."""
        vessel = self._vessel
        return vessel.name if vessel else f"Vessel {self._mmsi}"

    @property
    def icon(self) -> str:
        """Return an MDI icon appropriate for the vessel's AIS type code."""
        vessel = self._vessel
        if vessel is None:
            return DEFAULT_VESSEL_ICON
        return VESSEL_TYPE_ICONS.get(vessel.vessel_type, DEFAULT_VESSEL_ICON)

    @property
    def latitude(self) -> float | None:
        """Return the vessel's current latitude."""
        vessel = self._vessel
        return vessel.latitude if vessel else None

    @property
    def longitude(self) -> float | None:
        """Return the vessel's current longitude."""
        vessel = self._vessel
        return vessel.longitude if vessel else None

    @property
    def distance(self) -> float | None:
        """Return the distance in km from the centre of the tracked area."""
        vessel = self._vessel
        if vessel is None:
            return None
        return round(
            _haversine_km(self._centre_lat, self._centre_lon, vessel.latitude, vessel.longitude),
            2,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the AIS telemetry most useful in a map popup."""
        vessel = self._vessel
        if vessel is None:
            return {ATTR_MMSI: self._mmsi}
        return {
            ATTR_MMSI: vessel.mmsi,
            ATTR_VESSEL_NAME: vessel.name,
            ATTR_VESSEL_TYPE: VESSEL_TYPE_MAP.get(vessel.vessel_type, "Unknown"),
            ATTR_SPEED: vessel.speed,
            ATTR_HEADING: vessel.heading,
            ATTR_COURSE: vessel.course,
            ATTR_STATUS: vessel.status,
            ATTR_DESTINATION: vessel.destination,
            ATTR_LAST_SEEN: vessel.last_seen.isoformat() if vessel.last_seen else None,
        }
