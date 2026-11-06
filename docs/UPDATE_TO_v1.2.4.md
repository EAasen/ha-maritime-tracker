# ✅ Update to v1.2.4 - Quick Guide

## What Was Fixed

**Issue**: Location selector showed blank pop-up with no map  
**Cause**: Missing default coordinates for the map to render  
**Fix**: Added proper initialization coordinates to LocationSelector

---

## How to Update

### Option 1: Via HACS (Recommended)
```
1. Go to Settings → Devices & Services → HACS
2. Click "Custom repositories"
3. Find "Norwegian Maritime Tracker"
4. Update to v1.2.4
5. Restart Home Assistant
```

### Option 2: Manual Git Pull
```bash
cd custom_components/marinetraffic_tracker
git pull origin main
# Restart Home Assistant
```

### Option 3: Full Reinstall
```bash
rm -r custom_components/marinetraffic_tracker
git clone https://github.com/EAasen/ha-maritime-tracker.git custom_components/marinetraffic_tracker
# Restart Home Assistant
```

---

## After Updating

1. ✅ The integration will ask you to re-configure the tracking location
2. ✅ You should now see a **fully rendered map**
3. ✅ The map will show **Norway as the center point**
4. ✅ You can **pan, zoom, and select** your tracking area
5. ✅ The **submit button** will work once you confirm a location

---

## Technical Summary

### What Changed
- **File**: `config_flow.py` line 289-310
- **Function**: `_radius_schema()`
- **Change**: Added `default=default_location` parameter to `vol.Required()` field
- **Lines Added**: 9 lines
- **Breaking Changes**: None

### Default Behavior
- Map centers on **Norway** (58.5°N, 5.75°E)
- Shows **2.5 km radius** by default
- Falls back to Home Assistant's configured location if set within Norway

---

## Version Timeline

| Version | Fix |
|---------|-----|
| 1.2.4 | ✅ **Location selector map now renders** |
| 1.2.3 | Location validation improved |
| 1.2.2 | WebSocket API compatibility |

---

## Questions?

- **Still showing blank map?** → Hard refresh browser (Ctrl+F5)
- **Wrong coordinates?** → Check HA location settings (Settings → System → General)
- **Need help?** → See [LOCATION_SELECTOR_MAP_RENDERING_FIX.md](LOCATION_SELECTOR_MAP_RENDERING_FIX.md)

---

**Status**: ✅ **Ready to install**  
**Time to update**: **~2 minutes**  
**Restarts required**: **1** (Home Assistant)
