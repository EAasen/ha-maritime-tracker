# Location Validation Error Fix (v1.2.2 Patch)

## Issue
When submitting the location on the map in the config flow's "Tracking Area" step, users were getting:
```
Unknown error occurred
not a valid option at 'location'
```

## Root Cause
The `LocationSelector` in Home Assistant wasn't properly validating the location dictionary format when submitted. The code was trying to access fields without checking if they existed or had the correct format, causing voluptuous schema validation to fail with a generic error message.

## Solution Implemented

### 1. Enhanced Validation in `async_step_radius()` (config_flow.py)

**Before:**
```python
async def async_step_radius(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
    """Collect center coordinates and radius."""
    if user_input is not None:
        loc = user_input[_CONF_LOCATION]
        self._data[CONF_LATITUDE] = loc["latitude"]
        self._data[CONF_LONGITUDE] = loc["longitude"]
        self._data[CONF_RADIUS_KM] = loc["radius"] / _METRES_PER_KM
        return await self.async_step_options()
    # ...
```

**After:**
```python
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
```

### 2. Improved Schema in `_radius_schema()` (config_flow.py)

Simplified the schema to let Home Assistant handle the default values properly, instead of trying to pass complex default values that might conflict:

```python
def _radius_schema(hass: HomeAssistant, defaults: dict[str, Any]) -> vol.Schema:
    lat, lon = _default_coordinates(hass, defaults)
    radius_m = defaults.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM) * _METRES_PER_KM
    return vol.Schema(
        {
            vol.Required(
                _CONF_LOCATION,
            ): selector.LocationSelector(
                selector.LocationSelectorConfig(
                    radius=True,
                    icon="mdi:ferry",
                ),
            ),
        },
        extra=vol.PREVENT_EXTRA,
    )
```

### 3. Added Error Messages in strings.json

Added 5 new error messages to help users understand what went wrong:

```json
"location_required": "You must select a location on the map.",
"invalid_location_format": "The location data format is invalid. Please try selecting the location again.",
"location_missing_coordinates": "The location is missing latitude and/or longitude. Please try selecting the location again.",
"location_outside_norway": "The selected location is outside Norwegian waters. Please select a location within Norway.",
"invalid_location_data": "There was an error processing the location. Please try selecting the location again."
```

## Benefits

1. **Better Error Messages** - Users now get clear, actionable error messages instead of generic "unknown error"
2. **Robust Validation** - Handles edge cases like missing coordinates, wrong data types, or locations outside Norway
3. **Graceful Fallback** - If radius is missing, uses the default radius instead of crashing
4. **Type Safety** - Ensures coordinates are floats before storing them
5. **Debugging** - Better logging helps developers troubleshoot issues

## Testing

To test this fix:

1. Go through the config flow normally
2. When you reach the "Tracking Area" step, click on the map to select a location
3. Try these scenarios:
   - **Valid location**: Select somewhere in Norwegian waters, adjust radius, submit
   - **Location outside Norway**: Try clicking on Sweden, Germany, or another country (should show "outside Norwegian waters" error)
   - **No location**: Try submitting without selecting a location (should show "must select a location" error)

## Files Changed

- `custom_components/marinetraffic_tracker/config_flow.py` - Enhanced validation
- `custom_components/marinetraffic_tracker/strings.json` - Added error messages

## Compatibility

- ✅ Home Assistant 2026.10.4+
- ✅ No breaking changes to configuration
- ✅ Backward compatible with existing configurations

## Related Issues

- Fixes: "not a valid option at 'location'" error in config flow
- Related to: Location selector validation in HA 2026.10.4+
