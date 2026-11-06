# Fix for HA 2026.11.0 Location Validation Error

## What Was Wrong

You were getting "not a valid option at 'location'" because Home Assistant 2026.11.0 has stricter validation for the LocationSelector field that conflicts with our schema.

## What I Fixed

I've implemented a **compatibility workaround** for Home Assistant 2026.11.0+:

1. **Permissive Validator**: Added `_accept_location_dict()` that accepts any dictionary without strict validation
2. **Deferred Validation**: Moved all validation from schema level to the handler function
3. **Preserved UI**: LocationSelector widget still renders the map properly

## How to Test the Fix

### Step 1: Update the Integration

```bash
cd ha-maritime-tracker
git pull origin main
```

### Step 2: Restart Home Assistant

- Go to Settings → Developer Tools → YAML
- Copy this and paste it in the "YAML" section:
```yaml
homeassistant:
  - action: restart
```

Or simply go to Settings → System → Server Controls → "Restart Home Assistant"

### Step 3: Test the Setup Flow

1. Go to Settings → Devices & Services → Create Integration
2. Search for "Norwegian Maritime Tracker"
3. Follow the setup:
   - Enter BarentsWatch credentials
   - Select "Radius (map selector)"
   - **Click on the map** to select your location
   - Adjust radius if desired (e.g., 2500m)
   - **Click Submit**
   - Should now work without errors! ✅

### Step 4: Check Logs for Debugging (if issues persist)

1. Settings → Developer Tools → Logs
2. Search for "marinetraffic_tracker"
3. Look for any error messages or warnings

If you still see errors, copy the log output and share it.

## What Changed in the Code

### Old Approach (HA 2026.10.4 - Broken in 2026.11.0)
```python
vol.Required(_CONF_LOCATION): vol.All(
    selector.LocationSelector(...),  # <- Strict validation happens here
    _validate_location,
),
```

### New Approach (HA 2026.11.0+ Compatible)
```python
vol.Required(_CONF_LOCATION): vol.All(
    selector.LocationSelector(...),  # <- UI rendering happens here
    _accept_location_dict,           # <- Permissive validator (accepts any dict)
),
```

Then comprehensive validation in `async_step_radius()` handler with clear error messages.

## Testing Checklist

- [ ] Git pull and restart completed
- [ ] Map appears on "Tracking Area" screen
- [ ] Can click on map to select location
- [ ] Radius adjustment works
- [ ] Submit button works without validation error
- [ ] Proceeds to next step (Tracking Options)
- [ ] Configuration completes successfully

## If Still Getting Error

1. **Clear browser cache:**
   - Ctrl+Shift+Delete (Windows/Linux)
   - Cmd+Shift+Delete (Mac)
   - Clear "All time" or "Since I closed my browser"

2. **Try incognito/private window:**
   - Open Home Assistant in a private/incognito browser
   - Test the setup again

3. **Hard restart Home Assistant:**
   - Settings → System → Server Controls
   - "Restart Home Assistant"
   - Wait 2-3 minutes for restart

4. **Check Home Assistant version:**
   - Settings → About
   - Confirm you're on 2026.11.0 or later

## Error Messages

If validation fails, you'll now see **specific error messages** instead of generic "not a valid option":

| Error | Meaning | Solution |
|-------|---------|----------|
| "You must select a location on the map" | No location selected | Click on the map to select a location |
| "The location data format is invalid" | Unexpected data format | Try again, clear cache if persists |
| "The location is missing latitude/longitude" | Incomplete location | Make sure you selected a location on the map |
| "The selected location is outside Norwegian waters" | Wrong geographic area | Click on a location in Norway (between 57-71°N, 4-32°E) |
| "There was an error processing the location" | Unexpected error | Check the logs and report if persists |

## Technical Details

### Root Cause
Home Assistant 2026.11.0 applies strict validation to LocationSelector results. When the selector returns a dictionary, HA's built-in validator rejects it if it doesn't match a very specific schema.

### Solution
We bypass this by using a **permissive validator** (`_accept_location_dict`) that:
- Accepts any dictionary format
- Passes data through unchanged
- Lets our handler do the real validation

This keeps the LocationSelector UI widget working while avoiding the strict validation conflict.

### Why This Works
- Home Assistant uses the schema to know HOW to render the form (LocationSelector = map widget)
- Home Assistant also uses the validator to check if the submitted data is valid
- By using a permissive validator, we get the UI we want without validation conflicts
- Our handler does the real validation with proper error handling

## Questions?

If you're still experiencing issues after testing:

1. Share the exact steps you took
2. Include any error messages from the logs
3. Provide your Home Assistant version (Settings → About)
4. Note your browser and OS

Then open an issue on GitHub with this information.

---

**Status: 🔧 AWAITING YOUR TEST FEEDBACK**

Please test the fix and let me know:
1. Did the update pull correctly?
2. Did the map appear?
3. Could you select a location?
4. Did the submit button work?
5. Any error messages?

Your feedback will help me know if this completely fixes the issue or if we need further adjustments.
