# Location Selector Map Rendering Fix (v1.2.4)

## Problem Statement

When users attempted to set up v1.2.3, the location selection step showed a pop-up with only:
- Header: "Tracking area"
- Empty space (no map visible)
- A non-functional submit button (greyed out)

**User Impact**: Installation process blocked at location selection step.

---

## Root Cause Analysis

### The Issue
Home Assistant's `LocationSelector` component requires **initial coordinates** to render the map interface. Without default coordinates:
- The map canvas doesn't initialize
- The UI remains blank
- The form cannot be submitted (no valid data selected)

### Why It Happened
The original `_radius_schema()` function defined:
```python
vol.Required(
    _CONF_LOCATION,
): selector.LocationSelector(
    selector.LocationSelectorConfig(
        radius=True,
        icon="mdi:ferry",
    ),
),
```

**Problem**: No `default` value provided to the `vol.Required()` field. The LocationSelector had no initial coordinates to center the map on.

---

## Solution Implemented

### Code Changes

**File**: `custom_components/marinetraffic_tracker/config_flow.py`  
**Function**: `_radius_schema()` (lines 289-310)

#### Before
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
                    # Provide default center and radius for the location selector
                ),
            ),
        },
        extra=vol.PREVENT_EXTRA,
    )
```

#### After
```python
def _radius_schema(hass: HomeAssistant, defaults: dict[str, Any]) -> vol.Schema:
    lat, lon = _default_coordinates(hass, defaults)
    radius_m = defaults.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM) * _METRES_PER_KM
    
    # Prepare default location value with coordinates and radius
    default_location = {
        "latitude": lat,
        "longitude": lon,
        "radius": radius_m,
    }
    
    return vol.Schema(
        {
            vol.Required(
                _CONF_LOCATION,
                default=default_location,
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

### How It Works

1. **Get Initial Coordinates**
   - Uses `_default_coordinates()` helper (lines 265-276)
   - Priority order:
     1. Existing config values if present
     2. Home Assistant's configured location (if within Norway)
     3. Sensible Norway center coordinates (58.5°N, 5.75°E)

2. **Calculate Radius**
   - Converts stored radius from km to meters (multiply by 1000)
   - Uses existing config value or falls back to DEFAULT_RADIUS_KM (2.5 km)

3. **Create Default Dictionary**
   - Structures location as a dictionary with:
     - `latitude` (float): Center latitude
     - `longitude` (float): Center longitude  
     - `radius` (float): Radius in meters
   - Provides this as the `default` value to `vol.Required()`

4. **LocationSelector Initialization**
   - Receives the default location dictionary
   - Renders map centered on the coordinates
   - Shows radius selector with the default value
   - User can pan, zoom, and adjust as needed

---

## Impact Assessment

### What Works Now
- ✅ Map displays on location selection step
- ✅ Map centers on Norway by default
- ✅ Existing coordinates from config pre-populate the map
- ✅ Radius selector shows with sensible default (2.5 km)
- ✅ Users can seamlessly select their tracking area
- ✅ Submit button becomes active once location is confirmed

### Backward Compatibility
- ✅ No breaking changes
- ✅ Existing configurations still work
- ✅ Validation logic unchanged (still checks Norway bounds)
- ✅ Error handling preserved
- ✅ All v1.2.3 features retained

### Testing
All existing validation tests pass:
- `test_radius_step_rejects_missing_location` ✓
- `test_radius_step_rejects_location_outside_norway` ✓
- `test_radius_step_rejects_invalid_location_format` ✓
- `test_radius_step_rejects_missing_coordinates` ✓
- `test_radius_step_accepts_valid_location_with_radius` ✓
- `test_radius_step_uses_default_radius_when_missing` ✓

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.4   | 2026-11-03 | Location Selector map rendering fix |
| 1.2.3   | 2026-11-02 | Location validation improvements |
| 1.2.2   | 2026-11-01 | WebSocket API compatibility (stale cache issue) |
| 1.2.1   | 2026-10-31 | Initial release with location selection |

---

## User Guidance

### For Users Upgrading to v1.2.4

1. **Via HACS** (Recommended)
   - Settings → Devices & Services → HACS
   - Find "Norwegian Maritime Tracker"
   - Select v1.2.4 if available, or update
   - Restart Home Assistant

2. **Manual Update**
   - Delete `custom_components/marinetraffic_tracker/`
   - Clone latest: `git clone https://github.com/EAasen/ha-maritime-tracker.git`
   - Restart Home Assistant

3. **After Upgrade**
   - Reconfigure integration (it will ask for location again)
   - You should now see a fully rendered map
   - Select your tracking area with confidence

### Troubleshooting

**Map still not showing?**
1. Hard refresh browser cache (Ctrl+F5 / Cmd+Shift+R)
2. Clear Home Assistant cache: Settings → System → Advanced → Restart (multiple times)
3. Check browser console for JavaScript errors (F12 → Console tab)
4. Try in a different browser

**Coordinates way off?**
1. Check Home Assistant's configured location (Settings → System → General → Home location)
2. The integration uses HA's location as fallback
3. You can always manually adjust once the map appears

---

## Technical Details

### Default Location Initialization
The default location structure returned by this fix:
```python
{
    "latitude": 58.5,          # Norway center lat
    "longitude": 5.75,         # Norway center lon
    "radius": 2500.0           # Default 2.5 km in meters
}
```

### Why This Approach Works
- Home Assistant's LocationSelector **expects** the default value in this exact format
- The selector uses this to initialize the Leaflet map
- Without it, the map component has no center point to render
- By providing sensible defaults, users get an excellent UX without extra steps

### Related Components
- `selector.LocationSelector()` - Home Assistant's map widget
- `selector.LocationSelectorConfig()` - Configuration for the selector
- `_default_coordinates()` - Helper to determine initial center point
- `vol.Required()` - voluptuous schema field with default support

---

## Links

- [GitHub Release v1.2.4](https://github.com/EAasen/ha-maritime-tracker/releases/tag/v1.2.4)
- [GitHub Commit da5ba77](https://github.com/EAasen/ha-maritime-tracker/commit/da5ba77)
- [Related Issue Discussion](https://github.com/EAasen/ha-maritime-tracker/issues)
- [Installation Guide](docs/installation.md)

---

## Summary

v1.2.4 resolves the location selector UI rendering issue by providing proper default coordinates to Home Assistant's LocationSelector component. This was a simple but critical fix that restores functionality and user experience during the setup flow.

**Status**: ✅ Complete | **Severity**: 🔴 CRITICAL | **Impact**: All new/reconfiguring users
