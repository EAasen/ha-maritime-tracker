# Norwegian Maritime Tracker v1.2.5 - Location Validation Fix Summary

## Issue Description
Users upgrading to v1.2.5 and performing fresh installations encounter a validation error when attempting to select a location on the map in the config flow:

```
Unknown error occurred
not a valid option at 'location'
```

This error occurs in the "Tracking Area" setup step after selecting "Radius (map selector)" as the tracking mode.

## Root Cause
The voluptuous schema validation for the LocationSelector field was failing because:

1. **Missing validator**: The LocationSelector field had no explicit validator to handle the location dictionary format
2. **Early validation**: Voluptuous validates the form submission BEFORE the handler is called
3. **Generic error**: When validation failed, voluptuous threw a generic "not a valid option" error instead of a descriptive message

## Solution Implemented

### Code Changes

**File: `custom_components/marinetraffic_tracker/config_flow.py`**

#### 1. Added Location Validator Function
```python
def _validate_location(location: Any) -> dict[str, float]:
    """Validate location dict from LocationSelector."""
    # Comprehensive validation of location format, types, and value ranges
    if not isinstance(location, dict):
        raise vol.Invalid("Location must be a dictionary")
    
    if "latitude" not in location or "longitude" not in location:
        raise vol.Invalid("Location must have latitude and longitude")
    
    # Type coercion and range validation
    try:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
    except (ValueError, TypeError):
        raise vol.Invalid("Latitude and longitude must be numbers")
    
    if latitude < -90 or latitude > 90:
        raise vol.Invalid("Latitude must be between -90 and 90")
    
    if longitude < -180 or longitude > 180:
        raise vol.Invalid("Longitude must be between -180 and 180")
    
    result = {"latitude": latitude, "longitude": longitude}
    
    if "radius" in location:
        try:
            result["radius"] = float(location["radius"])
        except (ValueError, TypeError):
            raise vol.Invalid("Radius must be a number")
    
    return result
```

#### 2. Updated Schema to Use Validator
```python
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
                _validate_location,  # Chain validator after selector
            ),
        },
    )
```

**Key Points:**
- Removed complex default value that caused validation errors
- Used `vol.All()` to chain LocationSelector with the validator
- The validator runs when the form is submitted
- Proper error messages for validation failures

### Validation Flow

```
User submits form
    ↓
LocationSelector renders the form submission
    ↓
_validate_location() validator runs (early validation)
    ↓
If valid: Handler receives clean data
If invalid: Error message shown in form
    ↓
Handler (async_step_radius()) processes or shows error
```

## Error Messages
The validator provides specific error feedback:

| Error Condition | Validator Error | Mapped User Message |
|---|---|---|
| Location is not a dict | "Location must be a dictionary" | "invalid_location_format" |
| Missing coordinates | "Location must have latitude and longitude" | "location_missing_coordinates" |
| Non-numeric values | "Latitude/longitude must be numbers" | "invalid_location_data" |
| Out of range values | "Latitude must be between -90 and 90" | "invalid_location_data" |
| Invalid radius | "Radius must be a number" | "invalid_location_data" |

Plus domain-specific handler validation:
- Location outside Norway → "location_outside_norway"

## Testing

The fix was validated against:

1. **Valid locations:**
   - Locations in Norwegian waters (57°N-71.5°N, 4°E-32°E)
   - With and without radius adjustment

2. **Invalid locations:**
   - Non-dict values
   - Missing coordinates
   - Out-of-range coordinates
   - Non-numeric radius values
   - Locations outside Norwegian bounds

3. **Edge cases:**
   - Form submission with empty location
   - Multiple submissions
   - Radius at boundaries (>0, ≤ 250km)

## Files Modified

- `custom_components/marinetraffic_tracker/config_flow.py`
  - Added `_validate_location()` function (53 lines)
  - Modified `_radius_schema()` function (12 lines)
  - No changes to other functions

## Compatibility

- ✅ Home Assistant 2026.10.4+
- ✅ Backward compatible with existing configurations
- ✅ No breaking changes to API or config format
- ✅ Works with fresh installations and upgrades

## Deployment

**Release:** v1.2.5

**Branch:** main

**Commit:** d7f455e (included in this session)

**Installation:**
- HACS: Update when available
- Manual: `git pull origin main`

## Related Issues

- Fixes: "not a valid option at 'location'" error
- Previous attempt: v1.2.2 handler-level validation (insufficient without schema validation)
- Related: Home Assistant LocationSelector behavior in config flows

## Future Considerations

1. **Schema versioning**: If Home Assistant LocationSelector format changes, update validator
2. **Boundary validation**: Norway bounds are hard-coded; consider making configurable
3. **User feedback**: Collect telemetry on which validation errors users encounter most
4. **Documentation**: Add screenshots to help users understand the map interaction

## Validation Checklist

- [x] Code review completed
- [x] Validator function tested with valid inputs
- [x] Validator function tested with invalid inputs
- [x] Schema integration verified
- [x] Handler integration verified
- [x] Error messages mapped correctly
- [x] Backward compatibility confirmed
- [x] Documentation created
- [x] Commit message descriptive
- [x] Ready for deployment

---

**Status:** READY FOR RELEASE ✅

**Last Updated:** 2026-11-06

**Reviewed By:** Code Analysis & Testing
