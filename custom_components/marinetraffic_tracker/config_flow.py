"""Config flow for Norwegian Maritime Tracker."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_BARENTSWATCH_CLIENT_ID,
    CONF_BARENTSWATCH_CLIENT_SECRET,
    CONF_CREATE_AREA_ZONE,
    CONF_DATA_SOURCE,
    CONF_EAST,
    CONF_EXCLUDE_ANCHORED,
    CONF_EXCLUDE_MOORED,
    CONF_FILTER_VESSEL_TYPES,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NORTH,
    CONF_PORTS,
    CONF_RADIUS_KM,
    CONF_SOUTH,
    CONF_STALE_TIMEOUT,
    CONF_TRACKING_MODE,
    CONF_UPDATE_INTERVAL,
    CONF_VESSEL_LOG,
    CONF_VESSEL_LOG_FORMAT,
    CONF_VESSEL_LOG_RETENTION_DAYS,
    CONF_WATCHLIST_MMSI,
    CONF_WEST,
    DATA_SOURCE_KYSTVERKET,
    DEFAULT_CREATE_AREA_ZONE,
    DEFAULT_EXCLUDE_ANCHORED,
    DEFAULT_EXCLUDE_MOORED,
    DEFAULT_RADIUS_KM,
    DEFAULT_STALE_TIMEOUT,
    DEFAULT_TRACKING_MODE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_VESSEL_LOG,
    DEFAULT_VESSEL_LOG_FORMAT,
    DEFAULT_VESSEL_LOG_RETENTION_DAYS,
    DEFAULT_WATCHLIST_MMSI,
    DOMAIN,
    MAX_PORTS,
    MAX_WATCHLIST_MMSI,
    MIN_UPDATE_INTERVAL_API,
    MMSI_LENGTH,
    PORT_MAX_RADIUS_KM,
    PORT_MIN_RADIUS_KM,
    TRACKING_MODE_BOX,
    TRACKING_MODE_RADIUS,
    VESSEL_LOG_FORMATS,
    VESSEL_TYPE_LABELS,
)
from .kystverket_client import KystverketAuthError, KystverketClient

_LOGGER = logging.getLogger(__name__)
_CONF_LOCATION = "location"
_METRES_PER_KM = 1000.0
_NORWAY_LATITUDE = 60.4720
_NORWAY_LONGITUDE = 8.4689
_NORWAY_BOUNDS = {
    "north": 71.5,
    "south": 57.0,
    "east": 32.0,
    "west": 4.0,
}

_TRACKING_MODE_OPTIONS: list[selector.SelectOptionDict] = [
    selector.SelectOptionDict(value=TRACKING_MODE_RADIUS, label="Radius (map selector)"),
    selector.SelectOptionDict(value=TRACKING_MODE_BOX, label="Bounding box"),
]

_VESSEL_TYPE_OPTIONS: list[selector.SelectOptionDict] = [
    selector.SelectOptionDict(value=value, label=label)
    for value, label in VESSEL_TYPE_LABELS.items()
]

_STEP_INTRO_SCHEMA = vol.Schema({})
_STEP_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TRACKING_MODE, default=DEFAULT_TRACKING_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_TRACKING_MODE_OPTIONS,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


def _is_within_norway(latitude: float | None, longitude: float | None) -> bool:
    """Return whether coordinates fall within a broad Norwegian bounding box."""
    if latitude is None or longitude is None:
        return False
    return (
        _NORWAY_BOUNDS["south"] <= latitude <= _NORWAY_BOUNDS["north"]
        and _NORWAY_BOUNDS["west"] <= longitude <= _NORWAY_BOUNDS["east"]
    )


def _validate_location(location: Any) -> dict[str, float]:
    """Validate location dict from LocationSelector.
    
    Args:
        location: A location dict with latitude, longitude, and optionally radius.
    
    Returns:
        The validated location dict.
    
    Raises:
        vol.Invalid: If the location format is invalid.
    """
    if not isinstance(location, dict):
        raise vol.Invalid("Location must be a dictionary")
    
    if "latitude" not in location or "longitude" not in location:
        raise vol.Invalid("Location must have latitude and longitude")
    
    try:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
    except (ValueError, TypeError) as err:
        raise vol.Invalid("Latitude and longitude must be numbers") from err
    
    if latitude < -90 or latitude > 90:
        raise vol.Invalid("Latitude must be between -90 and 90")
    
    if longitude < -180 or longitude > 180:
        raise vol.Invalid("Longitude must be between -180 and 180")
    
    result = {
        "latitude": latitude,
        "longitude": longitude,
    }
    
    if "radius" in location:
        try:
            result["radius"] = float(location["radius"])
        except (ValueError, TypeError) as err:
            raise vol.Invalid("Radius must be a number") from err
    
    return result


def _validate_mmsi(value: str) -> str:
    """Validate and normalize a single MMSI string.

    Args:
        value: A string representation of an MMSI.

    Returns:
        The normalized MMSI string.

    Raises:
        vol.Invalid: If the MMSI is not a valid 9-digit string.
    """
    mmsi_str = str(value).strip()
    if not mmsi_str:
        raise vol.Invalid("MMSI cannot be empty")
    if len(mmsi_str) != MMSI_LENGTH:
        raise vol.Invalid(f"MMSI must be exactly {MMSI_LENGTH} digits")
    if not mmsi_str.isdigit():
        raise vol.Invalid("MMSI must contain only digits")
    return mmsi_str


def _validate_watchlist_mmsi(value: list[str]) -> list[str]:
    """Validate and normalize a list of MMSI strings.

    Args:
        value: A list of MMSI strings.

    Returns:
        The normalized and deduplicated list of MMSI strings.

    Raises:
        vol.Invalid: If any MMSI is invalid or the list exceeds the maximum.
    """
    if not isinstance(value, list):
        raise vol.Invalid("Watchlist MMSIs must be a list")

    if len(value) > MAX_WATCHLIST_MMSI:
        raise vol.Invalid(f"Watchlist cannot exceed {MAX_WATCHLIST_MMSI} MMSIs")

    validated = set()
    for mmsi in value:
        validated.add(_validate_mmsi(mmsi))

    return sorted(list(validated))


def _validate_port(port: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a single port definition.

    Args:
        port: A port dict with id, name, latitude, longitude, radius_km.

    Returns:
        The validated port dict.

    Raises:
        vol.Invalid: If any field is invalid.
    """
    if not isinstance(port, dict):
        raise vol.Invalid("Port must be a dictionary")

    # Validate name
    name = str(port.get("name", "")).strip()
    if not name:
        raise vol.Invalid("Port name cannot be empty")
    if len(name) > 50:
        raise vol.Invalid("Port name cannot exceed 50 characters")

    # Validate latitude
    try:
        latitude = float(port.get("latitude", 0))
        if latitude < -90 or latitude > 90:
            raise vol.Invalid("Latitude must be between -90 and 90")
    except (ValueError, TypeError) as err:
        raise vol.Invalid("Latitude must be a number") from err

    # Validate longitude
    try:
        longitude = float(port.get("longitude", 0))
        if longitude < -180 or longitude > 180:
            raise vol.Invalid("Longitude must be between -180 and 180")
    except (ValueError, TypeError) as err:
        raise vol.Invalid("Longitude must be a number") from err

    # Validate radius
    try:
        radius_km = float(port.get("radius_km", 1.0))
        if radius_km < PORT_MIN_RADIUS_KM or radius_km > PORT_MAX_RADIUS_KM:
            raise vol.Invalid(
                f"Port radius must be between {PORT_MIN_RADIUS_KM} and {PORT_MAX_RADIUS_KM} km"
            )
    except (ValueError, TypeError) as err:
        raise vol.Invalid("Radius must be a number") from err

    # Ensure ID exists
    port_id = port.get("id")
    if not port_id:
        port_id = str(uuid4())

    return {
        "id": port_id,
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "radius_km": radius_km,
    }


def _validate_ports(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize a list of port definitions.

    Args:
        value: A list of port dicts.

    Returns:
        The validated and deduplicated list of port dicts.

    Raises:
        vol.Invalid: If any port is invalid or the list exceeds the maximum.
    """
    if not isinstance(value, list):
        raise vol.Invalid("Ports must be a list")

    if len(value) > MAX_PORTS:
        raise vol.Invalid(f"Maximum of {MAX_PORTS} ports allowed")

    validated_ports = []
    seen_names = set()

    for port_data in value:
        validated_port = _validate_port(port_data)

        # Check for duplicate names
        port_name_lower = validated_port["name"].lower()
        if port_name_lower in seen_names:
            raise vol.Invalid("Port names must be unique")
        seen_names.add(port_name_lower)

        validated_ports.append(validated_port)

    return validated_ports


def _default_coordinates(hass: HomeAssistant, defaults: dict[str, Any]) -> tuple[float, float]:
    """Return sensible Norwegian coordinates for the selector default."""
    lat = defaults.get(CONF_LATITUDE)
    lon = defaults.get(CONF_LONGITUDE)
    if lat is not None and lon is not None and _is_within_norway(lat, lon):
        return float(lat), float(lon)

    hass_lat = getattr(hass.config, "latitude", None)
    hass_lon = getattr(hass.config, "longitude", None)
    if hass_lat is not None and hass_lon is not None and _is_within_norway(hass_lat, hass_lon):
        return float(hass_lat), float(hass_lon)

    return _NORWAY_LATITUDE, _NORWAY_LONGITUDE


def _credentials_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the credential step schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_BARENTSWATCH_CLIENT_ID,
                default=defaults.get(CONF_BARENTSWATCH_CLIENT_ID, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_BARENTSWATCH_CLIENT_SECRET,
                default=defaults.get(CONF_BARENTSWATCH_CLIENT_SECRET, ""),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


def _radius_schema(hass: HomeAssistant, defaults: dict[str, Any]) -> vol.Schema:
    """Build the radius/location step schema with proper validation."""
    return vol.Schema(
        {
            vol.Required(_CONF_LOCATION): vol.All(
                selector.LocationSelector(
                    selector.LocationSelectorConfig(
                        radius=True,
                        icon="mdi:ferry",
                    ),
                ),
                _validate_location,
            ),
        },
    )


def _box_schema(defaults: dict[str, Any]) -> vol.Schema:
    suggested_lat = float(defaults.get(CONF_LATITUDE, _NORWAY_LATITUDE))
    suggested_lon = float(defaults.get(CONF_LONGITUDE, _NORWAY_LONGITUDE))
    north = defaults.get(CONF_NORTH, round(suggested_lat + 0.4, 4))
    south = defaults.get(CONF_SOUTH, round(suggested_lat - 0.4, 4))
    east = defaults.get(CONF_EAST, round(suggested_lon + 0.8, 4))
    west = defaults.get(CONF_WEST, round(suggested_lon - 0.8, 4))
    return vol.Schema(
        {
            vol.Required(CONF_NORTH, default=north): vol.All(
                vol.Coerce(float),
                vol.Range(min=-90, max=90),
            ),
            vol.Required(CONF_EAST, default=east): vol.All(
                vol.Coerce(float),
                vol.Range(min=-180, max=180),
            ),
            vol.Required(CONF_SOUTH, default=south): vol.All(
                vol.Coerce(float),
                vol.Range(min=-90, max=90),
            ),
            vol.Required(CONF_WEST, default=west): vol.All(
                vol.Coerce(float),
                vol.Range(min=-180, max=180),
            ),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the shared non-authentication options schema."""
    try:
        raw_interval = int(defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    except (ValueError, TypeError):
        raw_interval = DEFAULT_UPDATE_INTERVAL

    return vol.Schema(
        {
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=max(raw_interval, MIN_UPDATE_INTERVAL_API),
            ): vol.All(int, vol.Range(min=MIN_UPDATE_INTERVAL_API, max=3600)),
            vol.Required(
                CONF_STALE_TIMEOUT,
                default=defaults.get(CONF_STALE_TIMEOUT, DEFAULT_STALE_TIMEOUT),
            ): vol.All(int, vol.Range(min=60, max=86400)),
            vol.Optional(
                CONF_FILTER_VESSEL_TYPES,
                default=defaults.get(CONF_FILTER_VESSEL_TYPES, []),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_VESSEL_TYPE_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_EXCLUDE_ANCHORED,
                default=defaults.get(CONF_EXCLUDE_ANCHORED, DEFAULT_EXCLUDE_ANCHORED),
            ): bool,
            vol.Required(
                CONF_EXCLUDE_MOORED,
                default=defaults.get(CONF_EXCLUDE_MOORED, DEFAULT_EXCLUDE_MOORED),
            ): bool,
            vol.Required(
                CONF_CREATE_AREA_ZONE,
                default=defaults.get(CONF_CREATE_AREA_ZONE, DEFAULT_CREATE_AREA_ZONE),
            ): bool,
            vol.Required(
                CONF_VESSEL_LOG,
                default=defaults.get(CONF_VESSEL_LOG, DEFAULT_VESSEL_LOG),
            ): bool,
            vol.Required(
                CONF_VESSEL_LOG_FORMAT,
                default=defaults.get(CONF_VESSEL_LOG_FORMAT, DEFAULT_VESSEL_LOG_FORMAT),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=VESSEL_LOG_FORMATS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="vessel_log_format",
                )
            ),
            vol.Required(
                CONF_VESSEL_LOG_RETENTION_DAYS,
                default=defaults.get(
                    CONF_VESSEL_LOG_RETENTION_DAYS, DEFAULT_VESSEL_LOG_RETENTION_DAYS
                ),
            ): vol.All(int, vol.Range(min=0, max=365)),
            vol.Optional(
                CONF_WATCHLIST_MMSI,
                default=defaults.get(CONF_WATCHLIST_MMSI, DEFAULT_WATCHLIST_MMSI),
            ): vol.All(_validate_watchlist_mmsi),
        }
    )


async def _async_validate_credentials(
    hass: HomeAssistant,
    client_id: str,
    client_secret: str,
) -> str | None:
    """Validate BarentsWatch credentials against the live token endpoint."""
    client = KystverketClient(
        async_get_clientsession(hass),
        client_id=client_id,
        client_secret=client_secret,
    )
    try:
        await client.async_validate_credentials()
    except KystverketAuthError:
        return "invalid_auth"
    except (aiohttp.ClientError, TimeoutError):
        return "cannot_connect"
    return None


class MarineTrafficConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a UI config flow for Norwegian Maritime Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {CONF_DATA_SOURCE: DATA_SOURCE_KYSTVERKET}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show setup instructions before collecting credentials."""
        if user_input is not None:
            return await self.async_step_credentials()

        return self.async_show_form(step_id="user", data_schema=_STEP_INTRO_SCHEMA)

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and validate BarentsWatch credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = str(user_input.get(CONF_BARENTSWATCH_CLIENT_ID, "")).strip()
            client_secret = str(user_input.get(CONF_BARENTSWATCH_CLIENT_SECRET, "")).strip()

            if not client_id:
                errors[CONF_BARENTSWATCH_CLIENT_ID] = "barentswatch_client_id_required"
            if not client_secret:
                errors[CONF_BARENTSWATCH_CLIENT_SECRET] = "barentswatch_client_secret_required"

            if not errors:
                credential_error = await _async_validate_credentials(
                    self.hass, client_id, client_secret
                )
                if credential_error is None:
                    self._data[CONF_BARENTSWATCH_CLIENT_ID] = client_id
                    self._data[CONF_BARENTSWATCH_CLIENT_SECRET] = client_secret
                    return await self.async_step_mode()
                errors["base"] = credential_error

        return self.async_show_form(
            step_id="credentials",
            data_schema=_credentials_schema(self._data),
            errors=errors,
        )

    async def async_step_mode(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose the tracking mode."""
        if user_input is not None:
            self._data[CONF_TRACKING_MODE] = user_input[CONF_TRACKING_MODE]
            if user_input[CONF_TRACKING_MODE] == TRACKING_MODE_RADIUS:
                return await self.async_step_radius()
            return await self.async_step_box()

        return self.async_show_form(step_id="mode", data_schema=_STEP_MODE_SCHEMA)

    async def async_step_radius(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Collect center coordinates and radius."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                if _CONF_LOCATION not in user_input:
                    errors["base"] = "location_required"
                else:
                    loc = user_input[_CONF_LOCATION]
                    
                    # Validate location has required fields
                    if not isinstance(loc, dict):
                        errors["base"] = "invalid_location_format"
                    elif "latitude" not in loc or "longitude" not in loc:
                        errors["base"] = "location_missing_coordinates"
                    elif not _is_within_norway(loc.get("latitude"), loc.get("longitude")):
                        errors["base"] = "location_outside_norway"
                    else:
                        self._data[CONF_LATITUDE] = float(loc["latitude"])
                        self._data[CONF_LONGITUDE] = float(loc["longitude"])
                        
                        # Handle radius - it might be in meters or might not be present
                        radius = loc.get("radius")
                        if radius is not None:
                            self._data[CONF_RADIUS_KM] = float(radius) / _METRES_PER_KM
                        else:
                            self._data[CONF_RADIUS_KM] = DEFAULT_RADIUS_KM
                        
                        return await self.async_step_options()
            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Error processing location: %s", err)
                errors["base"] = "invalid_location_data"

        if errors:
            # Show form again with errors
            return self.async_show_form(
                step_id="radius",
                data_schema=_radius_schema(self.hass, self._data),
                errors=errors,
            )

        return self.async_show_form(
            step_id="radius",
            data_schema=_radius_schema(self.hass, self._data),
        )

    async def async_step_box(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Collect bounding box coordinates."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_SOUTH] >= user_input[CONF_NORTH]:
                errors["base"] = "south_gte_north"
            elif user_input[CONF_WEST] >= user_input[CONF_EAST]:
                errors["base"] = "west_gte_east"
            else:
                self._data.update(user_input)
                return await self.async_step_options()

        defaults = dict(self._data)
        lat, lon = _default_coordinates(self.hass, defaults)
        defaults.setdefault(CONF_LATITUDE, lat)
        defaults.setdefault(CONF_LONGITUDE, lon)
        return self.async_show_form(
            step_id="box",
            data_schema=_box_schema(defaults),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect non-authentication options and create the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validated = _options_schema(self._data)(user_input)
            except vol.Invalid as err:
                _LOGGER.debug("Invalid config flow options submission: %s", err)
                errors["base"] = "invalid_options"
            else:
                self._data.update(validated)
                await self.async_set_unique_id(self._unique_id())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=self._make_title(), data=self._data)

        return self.async_show_form(
            step_id="options",
            data_schema=_options_schema(self._data),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle import from YAML configuration.

        Enables YAML-based configuration while still showing the integration
        in the Services & Devices UI discovery list.
        """
        # Forward to the user step to handle via UI flow
        self._data = {CONF_DATA_SOURCE: DATA_SOURCE_KYSTVERKET}
        self._data.update(import_data)
        return await self.async_step_credentials()

    def _unique_id(self) -> str:
        """Build a stable unique ID for the tracking area."""
        mode = self._data.get(CONF_TRACKING_MODE, TRACKING_MODE_RADIUS)
        if mode == TRACKING_MODE_RADIUS:
            return (
                f"{self._data[CONF_LATITUDE]}_{self._data[CONF_LONGITUDE]}"
                f"_{self._data[CONF_RADIUS_KM]}_kystverket"
            )
        return (
            f"{self._data[CONF_NORTH]}_{self._data[CONF_EAST]}"
            f"_{self._data[CONF_SOUTH]}_{self._data[CONF_WEST]}_kystverket"
        )

    def _make_title(self) -> str:
        """Generate a human-readable config entry title."""
        mode = self._data.get(CONF_TRACKING_MODE, TRACKING_MODE_RADIUS)
        if mode == TRACKING_MODE_RADIUS:
            lat = self._data.get(CONF_LATITUDE, _NORWAY_LATITUDE)
            lon = self._data.get(CONF_LONGITUDE, _NORWAY_LONGITUDE)
            radius = self._data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
            return f"Norwegian Maritime Tracker ({lat:.4f}, {lon:.4f}) r={radius}km"
        north = self._data.get(CONF_NORTH, 0)
        east = self._data.get(CONF_EAST, 0)
        south = self._data.get(CONF_SOUTH, 0)
        west = self._data.get(CONF_WEST, 0)
        return f"Norwegian Maritime Tracker [{south:.2f},{west:.2f}]–[{north:.2f},{east:.2f}]"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MarineTrafficOptionsFlow:
        """Return the options flow handler for an existing entry."""
        return MarineTrafficOptionsFlow(config_entry)


class MarineTrafficOptionsFlow(OptionsFlow):
    """Allow users to update non-authentication tracking options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial options menu step."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["options", "ports"],
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the tracking options step."""
        current = {**self._config_entry.data, **self._config_entry.options}
        current.setdefault(CONF_DATA_SOURCE, DATA_SOURCE_KYSTVERKET)
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validated = _options_schema(current)(user_input)
            except vol.Invalid as err:
                _LOGGER.debug("Invalid options flow submission: %s", err)
                errors["base"] = "invalid_options"
            else:
                validated[CONF_DATA_SOURCE] = DATA_SOURCE_KYSTVERKET
                # Preserve existing ports if not modified
                if CONF_PORTS not in validated:
                    validated[CONF_PORTS] = current.get(CONF_PORTS, [])
                return self.async_create_entry(data=validated)

        return self.async_show_form(
            step_id="options",
            data_schema=_options_schema(current),
            errors=errors,
        )

    async def async_step_ports(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the port configuration step."""
        current = {**self._config_entry.data, **self._config_entry.options}
        current.setdefault(CONF_DATA_SOURCE, DATA_SOURCE_KYSTVERKET)
        current.setdefault(CONF_PORTS, [])
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate the ports list
                ports_input = user_input.get(CONF_PORTS, [])
                validated_ports = _validate_ports(ports_input) if ports_input else []

            except vol.Invalid as err:
                _LOGGER.debug("Invalid ports configuration: %s", err)
                errors["base"] = str(err) if str(err) else "invalid_options"
            else:
                # Update only the ports, preserve other options
                current[CONF_PORTS] = validated_ports
                return self.async_create_entry(data=current)

        # Build ports options for the selector
        port_options = [
            selector.SelectOptionDict(
                value=(
                    f"{p['id']}|{p['name']}|{p['latitude']}|{p['longitude']}|" f"{p['radius_km']}"
                ),
                label=(
                    f"{p['name']} ({p['latitude']:.4f}, {p['longitude']:.4f}) "
                    f"r={p['radius_km']}km"
                ),
            )
            for p in current.get(CONF_PORTS, [])
        ]

        # Build schema based on whether there are any ports
        if port_options:
            ports_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_PORTS,
                        default=current.get(CONF_PORTS, []),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=port_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            )
        else:
            # No ports configured yet - show empty form
            ports_schema = vol.Schema({})

        return self.async_show_form(
            step_id="ports",
            data_schema=ports_schema,
            errors=errors,
            description_placeholders={
                "port_count": str(len(current.get(CONF_PORTS, []))),
                "max_ports": str(MAX_PORTS),
            },
        )
