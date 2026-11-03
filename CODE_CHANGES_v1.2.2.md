# Code Changes in v1.2.2 - WebSocket API Compatibility Fix

## Overview
Fixed Home Assistant 2026.10.4+ compatibility by removing deprecated `allow_user_context` parameter from WebSocket API registration.

## File: `custom_components/marinetraffic_tracker/websocket_api.py`

### Change 1: Updated Import (Line 20)

**Before (v1.2.1):**
```python
from homeassistant.core import HomeAssistant, callback
```

**After (v1.2.2):**
```python
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
```

**Reason:** Direct import of `websocket_api` module to access `async_register_command()` function.

---

### Change 2: Updated `async_register_websocket_api()` Function (Lines 96-121)

#### OLD CODE (v1.2.1 - DEPRECATED)
```python
async def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the maritime tracker WebSocket API commands."""
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SUBSCRIBE,
        _async_handle_subscribe,
        allow_user_context=False,
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_UNSUBSCRIBE,
        _async_handle_unsubscribe,
        allow_user_context=False,
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_GET_SNAPSHOT,
        _async_handle_get_snapshot,
        allow_user_context=False,
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_GET_TRAIL,
        _async_handle_get_trail,
        allow_user_context=False,
    )
```

#### NEW CODE (v1.2.2 - CORRECT)
```python
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
```

---

## Key Differences

### 1. Module Access Pattern
| Aspect | v1.2.1 | v1.2.2 |
|--------|--------|--------|
| Pattern | `hass.components.websocket_api` | `websocket_api` (imported) |
| Status | ❌ Deprecated in HA 2026.10.4+ | ✅ Current API |

### 2. Function Signature
| Aspect | v1.2.1 | v1.2.2 |
|--------|--------|--------|
| First Param | `WS_TYPE_*` (command type) | `hass` (HomeAssistant instance) |
| Command Type | 2nd parameter | 2nd parameter |
| Handler | 3rd parameter | 3rd parameter |
| `allow_user_context` | ✅ Present (now unsupported) | ❌ Removed |

### 3. Why These Changes?

**Breaking API Change in HA 2026.10.4:**
- Home Assistant removed the `hass.components` attribute accessor
- WebSocket API signature changed to require `hass` as first parameter
- The `allow_user_context` parameter was deprecated and removed

**Impact:**
- Old code causes: `TypeError: async_register_command() got an unexpected keyword argument 'allow_user_context'`
- New code works seamlessly with HA 2026.10.4+

---

## What Remains Unchanged

All other code in `websocket_api.py` remains unchanged:
- Command type constants (WS_TYPE_SUBSCRIBE, etc.)
- Command handlers (_async_handle_subscribe, etc.)
- Response classes (BoundedSnapshot, VesselSnapshot, etc.)
- Error handling and validation logic
- JSON encoding and response formatting

---

## Backward Compatibility

**Breaking Change:** ✅ None for end users
- This is purely an internal API fix
- Configuration options are unchanged
- Entity behavior is unchanged
- No data migration required

**Minimum Home Assistant Version:** ✅ 2026.10.4+

---

## Testing

### Unit Tests
No changes to test suite needed. Existing tests pass with new code.

### Integration Tests
- WebSocket API registration succeeds
- Commands register without errors
- Handler functions work as expected

### Validation
```bash
# Verify no deprecated usage remains
grep -n "hass\.components\." custom_components/marinetraffic_tracker/websocket_api.py
# Returns: (nothing) ✅

# Verify imports are correct
grep -n "from homeassistant.components import websocket_api" custom_components/marinetraffic_tracker/websocket_api.py
# Returns: line 20 ✅

# Verify allow_user_context is gone
grep -n "allow_user_context" custom_components/marinetraffic_tracker/websocket_api.py
# Returns: (nothing) ✅
```

---

## Migration Guide

### For Developers
If you have forked this integration or custom code using the old pattern:

**Change this:**
```python
from homeassistant.core import HomeAssistant

async def setup_websocket(hass: HomeAssistant):
    hass.components.websocket_api.async_register_command(
        "my_command",
        handler,
        allow_user_context=False,
    )
```

**To this:**
```python
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

async def setup_websocket(hass: HomeAssistant):
    websocket_api.async_register_command(
        hass,
        "my_command",
        handler,
    )
```

---

## References

- [Home Assistant 2026.10.4 Release Notes](https://www.home-assistant.io/blog/)
- [WebSocket API Development](https://developers.home-assistant.io/docs/api/websocket)
- [Integration Development Guide](https://developers.home-assistant.io/docs/creating_integration_manifest/)

---

## Summary

The v1.2.2 update ensures the Norwegian Maritime Tracker integration works flawlessly with Home Assistant 2026.10.4 and later by:

1. ✅ Removing deprecated `hass.components` accessor pattern
2. ✅ Using direct module imports
3. ✅ Passing `hass` as first parameter to `async_register_command()`
4. ✅ Removing the unsupported `allow_user_context` parameter

No user-facing changes, just internal API compliance updates.
