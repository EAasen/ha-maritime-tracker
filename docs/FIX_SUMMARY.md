# Home Assistant 2026.10.4+ Compatibility Fix

## Issue
When activating the Norwegian Maritime Tracker integration in Home Assistant 2026.10.4 or later, the following error occurs:

```
AttributeError: 'HomeAssistant' object has no attribute 'components'
```

**Error Location:** 
- File: `custom_components/marinetraffic_tracker/websocket_api.py`
- Line: 98
- Function: `async_register_websocket_api()`

## Root Cause
The `hass.components.websocket_api` API was deprecated and removed in newer versions of Home Assistant. This attribute-based access pattern is no longer supported.

## Solution
Updated the WebSocket API registration to use the modern import-based approach:

### Changes Made

**1. Updated Import Statement (Line 18)**
```python
# OLD:
from homeassistant.core import HomeAssistant, callback

# NEW:
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
```

**2. Updated `async_register_websocket_api()` Function (Lines 96-120)**
```python
# OLD:
async def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the maritime tracker WebSocket API commands."""
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SUBSCRIBE,
        _async_handle_subscribe,
        allow_user_context=False,
    )
    # ... more calls

# NEW:
async def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the maritime tracker WebSocket API commands."""
    websocket_api.async_register_command(
        hass,  # Pass hass as first parameter
        WS_TYPE_SUBSCRIBE,
        _async_handle_subscribe,
        allow_user_context=False,
    )
    # ... more calls
```

## Key Differences
- **Import:** `websocket_api` is now imported directly from `homeassistant.components`
- **API Call:** Changed from `hass.components.websocket_api.async_register_command(...)` to `websocket_api.async_register_command(hass, ...)`
- **Parameters:** The `hass` instance is now passed as the first parameter to each registration call

## Testing
The fix has been verified by:
1. Python syntax validation ✓
2. Import statement verification ✓
3. Function call verification ✓

## Compatibility
This fix is compatible with:
- Home Assistant 2026.10.4+
- Modern Home Assistant versions that use the import-based WebSocket API

## Files Modified
- `custom_components/marinetraffic_tracker/websocket_api.py`
