"""Norwegian Maritime Tracker — Home Assistant custom integration.

Domain: marinetraffic_tracker

Entry point for integration setup and teardown.  The coordinator is created
here so all platforms share one polling instance per config entry.
"""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AREA_ZONE_ENTITY_PREFIX,
    CONF_BARENTSWATCH_CLIENT_ID,
    CONF_BARENTSWATCH_CLIENT_SECRET,
    CONF_CREATE_AREA_ZONE,
    DEFAULT_CREATE_AREA_ZONE,
    DOMAIN,
)
from .coordinator import MarineTrafficCoordinator, VesselClient
from .geo_filter import area_centre_and_radius
from .kystverket_client import KystverketClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.GEO_LOCATION,
]

# Maps entry_id -> entity_id of the synthetic zone drawn for that entry's area.
DATA_AREA_ZONES: Final = f"{DOMAIN}_area_zones"

# Minimum Home Assistant version required by this integration.
MIN_HA_VERSION: Final = "2023.1.0"


def _check_ha_version() -> None:
    """Log the running HA version and warn if it is below the minimum required."""
    _LOGGER.info(
        "Norwegian Maritime Tracker: running on Home Assistant %s (minimum required: %s)",
        HA_VERSION,
        MIN_HA_VERSION,
    )
    try:
        running = tuple(int(x) for x in HA_VERSION.split(".")[:3])
        minimum = tuple(int(x) for x in MIN_HA_VERSION.split(".")[:3])
    except ValueError:
        _LOGGER.debug(
            "Norwegian Maritime Tracker: could not parse HA version string '%s'; skipping check.",
            HA_VERSION,
        )
        return
    if running < minimum:
        _LOGGER.warning(
            "Norwegian Maritime Tracker requires Home Assistant %s or newer. "
            "You are running %s. Some features may not work correctly.",
            MIN_HA_VERSION,
            HA_VERSION,
        )


def _build_client(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> VesselClient:
    """Instantiate the active Kystverket client."""
    config: dict = {**entry.data, **entry.options}
    return KystverketClient(
        async_get_clientsession(hass),
        client_id=str(config.get(CONF_BARENTSWATCH_CLIENT_ID, "")).strip(),
        client_secret=str(config.get(CONF_BARENTSWATCH_CLIENT_SECRET, "")).strip(),
    )


@callback
def _async_create_area_zone(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Draw the tracked area as a zone so it is visible on the Home Assistant map.

    Home Assistant offers no supported way for an integration to register a real
    zone entity, so the state is written directly. The zone is *not* passive
    because the map card only draws active zones.
    """
    config: dict = {**entry.data, **entry.options}
    if not config.get(CONF_CREATE_AREA_ZONE, DEFAULT_CREATE_AREA_ZONE):
        return

    area = area_centre_and_radius(config)
    if area is None:
        _LOGGER.debug("Tracked area is not configured; skipping zone creation")
        return
    latitude, longitude, radius_km = area

    entity_id = AREA_ZONE_ENTITY_PREFIX
    if hass.states.get(entity_id) is not None:
        entity_id = f"{AREA_ZONE_ENTITY_PREFIX}_{entry.entry_id[:8]}"

    hass.states.async_set(
        entity_id,
        "zoning",
        {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius_km * 1000,
            "passive": False,
            "editable": False,
            "icon": "mdi:ferry",
            "friendly_name": entry.title or "Maritime tracking area",
        },
    )
    hass.data.setdefault(DATA_AREA_ZONES, {})[entry.entry_id] = entity_id


@callback
def _async_remove_area_zone(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the tracked-area zone state created for *entry*."""
    entity_id = hass.data.get(DATA_AREA_ZONES, {}).pop(entry.entry_id, None)
    if entity_id:
        hass.states.async_remove(entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Norwegian Maritime Tracker from a config entry."""
    _check_ha_version()
    client = _build_client(hass, entry)
    coordinator = MarineTrafficCoordinator(hass, entry, client)

    # Perform the first refresh so entities are available immediately.
    # If the initial fetch fails, the setup is aborted and HA will retry.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _async_create_area_zone(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when options are changed so the new interval takes effect.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and clean up resources."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        _async_remove_area_zone(hass, entry)
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
