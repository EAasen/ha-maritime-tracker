# Fix for v1.2.2 Activation Error

## Error
```
TypeError: async_register_command() got an unexpected keyword argument 'allow_user_context'
```

## Root Cause
This error occurs due to:
1. Stale Python bytecode (.pyc files) in Home Assistant's custom_components cache
2. Version mismatch between the deployed code and the source
3. The old `allow_user_context=False` parameter being referenced by cached bytecode

## Solution: Complete Clean Install

### Step 1: Remove the Integration from Home Assistant
1. Open Home Assistant Settings → Devices & Services
2. Find "Norwegian Maritime Tracker" integration
3. Click the three dots → Delete → Confirm

### Step 2: Remove Custom Component Files
On your Home Assistant machine, SSH into the host and run:

```bash
# Navigate to custom_components
cd /config/custom_components/

# Remove the entire marinetraffic_tracker directory
rm -rf marinetraffic_tracker/

# Clear Python cache
find /config -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /config -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

# Restart Home Assistant through the UI or:
# (This requires SSH access with proper credentials)
```

### Step 3: Reinstall the Integration

#### Option A: Using HACS (Recommended)
1. Open HACS in Home Assistant
2. Click "Integrations"
3. Click "⋯" (three dots) → "Repositories"
4. Paste: `https://github.com/EAasen/ha-maritime-tracker`
5. Select "Integration" category
6. Click "Install"
7. Restart Home Assistant
8. Go to Settings → Devices & Services → Create Automation
9. Select "Norwegian Maritime Tracker"
10. Fill in your configuration

#### Option B: Manual Installation
1. Download the latest release from GitHub
2. Copy `custom_components/marinetraffic_tracker/` to your Home Assistant `config/custom_components/`
3. Clear the Python cache as shown in Step 2
4. Restart Home Assistant
5. Configure the integration through Settings → Devices & Services

### Step 4: Verify the Fix

After restarting Home Assistant:

1. Go to Settings → Devices & Services
2. Click "Create Automation"
3. Select "Norwegian Maritime Tracker"
4. Enter your configuration:
   - Latitude/Longitude of your area
   - Search radius (km)
   - Update interval (minutes)
5. Submit

The integration should now activate without errors.

## Verification

If the integration activates successfully, you should see:
- No errors in Home Assistant logs
- A new "maritime_tracker" entity in Developer Tools → States
- A new area with the name you provided

## If the Error Persists

If you still see the error after following these steps:

1. **Check Home Assistant version**
   - Settings → About → Home Assistant version should be 2026.10.4 or later
   - If older, update Home Assistant first

2. **Check the websocket_api.py file directly**
   - SSH into Home Assistant
   - Run: `grep -n "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py`
   - This should return NO matches

3. **Check Home Assistant logs for more details**
   - Settings → System → Logs
   - Look for additional context around the error

4. **Clear all Python bytecode**
   ```bash
   find /config -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
   find /config -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
   find /config -type f -name "*.pyc" -delete 2>/dev/null || true
   ```

5. **Restart Home Assistant**
   - Settings → System → Restart

## What Changed in v1.2.2

The integration was updated to:
- Remove `allow_user_context` parameter (not supported in HA 2026.10.4+)
- Use modern `websocket_api.async_register_command()` API
- Maintain full compatibility with Home Assistant 2026.10.4+

## Files Modified
- `custom_components/marinetraffic_tracker/websocket_api.py` (Lines 96-121)

## Compatibility
- ✅ Home Assistant 2026.10.4+
- ✅ Python 3.10+
- ✅ All previous configurations

## Support

If you continue to have issues:
1. Open an issue on GitHub: https://github.com/EAasen/ha-maritime-tracker/issues
2. Include:
   - Your Home Assistant version
   - Full error traceback from logs
   - Output of: `grep -n "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py`
   - Your installation method (HACS or manual)
