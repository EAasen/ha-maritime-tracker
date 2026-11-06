# Diagnostic: Location Validation Error in HA 2026.11.0

## Problem Description

Users on Home Assistant Core 2026.11.0 are getting:
```
not a valid option at 'location'
```

When trying to submit the "Tracking Area" form after selecting a location on the map.

**Test Case:**
- Home Assistant version: 2026.11.0 (Supervisor 2026.10.5)
- Integration version: 1.2.5
- Tracking Mode: Radius (map selector)
- Steps: Select location on map → Set radius (e.g., 2500m) → Click Submit

## Root Cause Analysis

The error "not a valid option at 'location'" is being thrown by voluptuous BEFORE our handler is called. This indicates:

1. **Home Assistant is validating the LocationSelector data against a strict schema**
2. **The LocationSelector in HA 2026.11.0 might have changed its output format**
3. **Our schema definition might not be compatible with this new version**

## Potential Issues

### Issue 1: LocationSelector Output Format Changed
Home Assistant 2026.11.0 might have changed how LocationSelector returns data. Previously it might have been:
```python
{"latitude": 59.9, "longitude": 10.75, "radius": 2500.0}
```

But in 2026.11.0 it might be:
```python
{"latitude": 59.9, "longitude": 10.75, "radius_m": 2500.0}  # radius_m instead of radius
```

Or it might reject non-standard dict keys.

### Issue 2: LocationSelector Needs Special Schema Definition
The LocationSelector widget might require specific schema configuration that we're missing.

### Issue 3: Voluptuous Validation Chain
Using `vol.All()` with LocationSelector might cause voluptuous to apply multiple validators in a way that breaks the data.

## Solutions to Test

### Solution 1: Check LocationSelector Output Format
The first step is to log what data Home Assistant is actually sending to our handler.

### Solution 2: Modify Schema for HA 2026.11.0 Compatibility
We might need to use a different approach to the schema that doesn't conflict with Home Assistant's internal validation.

### Solution 3: Bypass LocationSelector Validation Entirely
Instead of trying to validate via voluptuous, we could make the schema accept anything and do all validation in the handler.

## Next Steps for User

1. **Enable Debug Logging:**
   - Go to Settings → Developer Tools → Logs
   - Search for "marinetraffic_tracker" 
   - Look for our debug output

2. **Capture Error Details:**
   - Note the exact form state (coordinates, radius) when error occurs
   - Check if error appears immediately or only after certain inputs

3. **Test Alternative:**
   - Try using "Bounding box" mode instead of "Radius (map selector)"
   - This would help confirm if issue is LocationSelector-specific

## Technical Investigation

The error is coming from Home Assistant's form validation layer, not our code. This means:

**Flow:**
1. User submits form with location data
2. Home Assistant validates form data against schema
3. Home Assistant throws "not a valid option" error
4. Our handler is never called

**Why This Happens:**
- The LocationSelector validator in Home Assistant 2026.11.0 might have strict requirements
- Our schema might not match what Home Assistant expects
- There might be a mismatch between widget output and schema validation

## Proposed Fix Approach

Instead of trying to validate via voluptuous (which causes the error), we should:

1. Remove strict voluptuous validation from the schema
2. Let LocationSelector return raw data without validation
3. Do ALL validation in the async_step_radius() handler
4. Display clear error messages for validation failures

This approach:
- Bypasses the voluptuous error
- Gives us full control over error messages
- Works regardless of Home Assistant version changes
- Is more flexible for custom validation (like Norway bounds)

## Code Changes Required

Current problematic schema:
```python
def _radius_schema(hass, defaults):
    return vol.Schema({
        vol.Required(_CONF_LOCATION): selector.LocationSelector(...)
    })
```

Proposed fix:
```python
def _radius_schema(hass, defaults):
    return vol.Schema({
        vol.Required(_CONF_LOCATION): dict  # Accept any dict without validation
    })
```

Then in the handler, validate comprehensively and show errors via the form.

## Status

🔴 **CRITICAL** - Blocks all new installations on HA 2026.11.0+
⚠️ **Urgent** - Needs immediate fix for compatibility

## Testing Matrix

| HA Version | Status | Notes |
|---|---|---|
| 2026.10.4 | ✅ Works | Original tested version |
| 2026.11.0 | ❌ Fails | Current user's version |
| 2026.10.5 | ? | Unknown |
| 2026.12+ | ? | Unknown |

---

**Next Action:** Implement bypass solution to remove voluptuous validation from LocationSelector field.
