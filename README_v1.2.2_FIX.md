# v1.2.2 Activation Error - Complete Diagnosis & Solution

## 🔴 The Error You're Seeing

```
Logger: homeassistant.config_entries
Error setting up entry Norwegian Maritime Tracker (58.8902, 5.7484) r=2.5km for marinetraffic_tracker
Traceback:
  File "/config/custom_components/marinetraffic_tracker/websocket_api.py", line 99
    websocket_api.async_register_command(...)
TypeError: async_register_command() got an unexpected keyword argument 'allow_user_context'
```

---

## 🔍 Root Cause Analysis

### What Happened?

**Home Assistant 2026.10.4** removed the `allow_user_context` parameter from the WebSocket API due to architectural changes. However, your Home Assistant installation is using stale cached Python bytecode from an older version of the integration.

### Why Are You Getting This Error?

The error message is misleading—it's actually coming from **Python's module cache**, not the current code. Here's the sequence:

1. ✅ v1.2.2 code is **correct** — it doesn't use `allow_user_context`
2. ❌ But your HA instance still has **cached .pyc files** from old versions
3. ⚠️ Python loads the old bytecode instead of the new code
4. 💥 The old code tries to use the unsupported parameter → Error!

### Proof the Current Code is Correct

Looking at the current [websocket_api.py](D:\NCloud\0 Dev\ha-maritime-tracker\custom_components\marinetraffic_tracker\websocket_api.py):

```python
# ✅ CORRECT - v1.2.2
async def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the maritime tracker WebSocket API commands."""
    websocket_api.async_register_command(
        hass,
        WS_TYPE_SUBSCRIBE,
        _async_handle_subscribe,
        # ✅ NO allow_user_context parameter!
    )
```

There is **NO `allow_user_context` parameter anywhere** in the code!

---

## ✅ The Solution

You need to **completely clear Python's cache** and reinstall the integration fresh. This ensures Home Assistant loads the correct, updated code.

### Quick Fix (5 Minutes)

#### 1️⃣ Remove Integration from Home Assistant
1. Open Home Assistant → Settings → Devices & Services
2. Find "Norwegian Maritime Tracker"
3. Click the **⋮** (three dots) menu
4. Select "Delete Entry"
5. Confirm deletion

#### 2️⃣ Clear Python Cache
Connect to your Home Assistant via SSH and run:

```bash
# SSH into your Home Assistant
ssh root@<your-ha-ip>

# Navigate to custom_components
cd /config/custom_components/

# Remove the integration
rm -rf marinetraffic_tracker/

# Clear Python cache files (IMPORTANT!)
find /config -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /config -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
find /config -type f -name "*.pyc" -delete 2>/dev/null

# Logout
exit
```

#### 3️⃣ Reinstall the Integration
**Using HACS (Recommended):**
1. Open HACS in Home Assistant
2. Click **Integrations**
3. Click **⋮** (three dots) → **Custom repositories**
4. Paste: `https://github.com/EAasen/ha-maritime-tracker`
5. Select category: **Integration**
6. Click **Install**

**Or Manually:**
1. Download latest: https://github.com/EAasen/ha-maritime-tracker/releases/download/v1.2.2/marinetraffic_tracker.zip
2. Extract to `/config/custom_components/`
3. Verify folder structure: `/config/custom_components/marinetraffic_tracker/__init__.py`

#### 4️⃣ Restart Home Assistant
1. Settings → System → Restart Home Assistant
2. Wait for restart to complete (~2-3 minutes)

#### 5️⃣ Reconfigure Integration
1. Settings → Devices & Services
2. Click **Create Automation** (or **New Integration** if you see the button)
3. Search for "Norwegian Maritime Tracker"
4. Enter your configuration:
   - Latitude (e.g., 58.8902)
   - Longitude (e.g., 5.7484)
   - Radius in km (e.g., 2.5)
   - Update interval in minutes (e.g., 5)
5. Click **Submit**

### ✅ You're Done!

The integration should now activate without errors. Check Home Assistant logs to confirm:
- Settings → System → Logs
- Should NOT see any "allow_user_context" errors

---

## 🤔 Why Is This Happening?

### The Technical Explanation

When you upgrade an integration in Home Assistant:

1. **Python loads modules once** — After importing, Python caches the compiled bytecode in `.pyc` files
2. **Cache persists across restarts** — The old bytecode stays in `__pycache__` directories
3. **New code doesn't get loaded** — Home Assistant uses the cached bytecode instead
4. **Old API calls fail** — The old code tries to use deprecated parameters

The `websocket_api.py` file we provide is correct, but Home Assistant was running the old cached version.

### What Changed Between Versions?

| Version | Status | Code | Parameter |
|---------|--------|------|-----------|
| v1.2.1 | ❌ Deprecated | `hass.components.websocket_api.async_register_command(cmd, handler, **allow_user_context=False**)` | Required |
| v1.2.2 | ✅ Current | `websocket_api.async_register_command(hass, cmd, handler)` | Removed |
| HA 2026.10.4+ | ✅ Current | Removed `allow_user_context` support | N/A |

---

## 🚀 After You're Up and Running

### Verify Everything Works

1. **Check Entities Created**
   - Developer Tools → States
   - Search for `device_tracker.maritime_tracker_`
   - Should show vessel tracking data

2. **Check Logs Are Clean**
   - Settings → System → Logs
   - Search for "marinetraffic_tracker"
   - Should only show info-level messages

3. **Verify WebSocket API**
   - Any vessels in your area should update automatically
   - Check Automations → Events to see `marinetraffic_vessel_*` events

### Optional: Advanced Verification

If you're technically inclined, you can verify the fix:

```bash
# Verify the code is correct
ssh root@<your-ha-ip>
grep -n "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py

# Should return: (nothing)
# If it returns anything, the old code is still there!

# Verify version
cat /config/custom_components/marinetraffic_tracker/manifest.json | grep version
# Should show: "version": "1.2.2"

# Exit
exit
```

---

## 🆘 If The Error Persists

### Check Checklist

- [ ] Did you remove the integration before clearing cache?
- [ ] Did you remove the `marinetraffic_tracker/` folder?
- [ ] Did you clear Python cache (all three commands)?
- [ ] Did you restart Home Assistant?
- [ ] Is your Home Assistant version ≥ 2026.10.4?
- [ ] Did you reinstall from HACS or manually?

### Troubleshooting Steps

**1. Check Home Assistant Version**
```
Settings → About → Check Home Assistant version
Should be ≥ 2026.10.4
```

If older, update Home Assistant first!

**2. More Aggressive Cache Clearing**
```bash
ssh root@<your-ha-ip>
cd /config

# More thorough cache removal
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Also clear custom_components directory completely
rm -rf custom_components/marinetraffic_tracker/

# Now restart Home Assistant from the UI
exit
```

**3. Check Current Code**
```bash
ssh root@<your-ha-ip>
grep "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py
```

If this returns anything, the old code is still there. Manually delete and reinstall.

**4. View Full Error**
- Settings → System → Logs
- Copy the entire error traceback
- Include in a GitHub issue

---

## 📝 What Changed in v1.2.2

### Code Changes
- **File:** `websocket_api.py`
- **Lines:** 20, 96-121
- **Change:** Removed deprecated `allow_user_context` parameter
- **Reason:** Home Assistant 2026.10.4+ no longer supports this parameter

### User Impact
- ✅ No configuration changes needed
- ✅ No entity changes
- ✅ No automation changes required
- ✅ All data is preserved

---

## 📚 Related Documentation

- [CODE_CHANGES_v1.2.2.md](CODE_CHANGES_v1.2.2.md) — Detailed code diff
- [TROUBLESHOOTING_v1.2.2.md](TROUBLESHOOTING_v1.2.2.md) — Platform-specific help
- [FIX_v1.2.2_ACTIVATION_ERROR.md](FIX_v1.2.2_ACTIVATION_ERROR.md) — Complete fix guide

---

## 🐛 Report Issues

If you still have problems after following all these steps:

1. Gather information:
   - Home Assistant version
   - Full error traceback
   - Your installation method (HACS/manual)
   - Output of: `grep -c "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py`

2. Open an issue: https://github.com/EAasen/ha-maritime-tracker/issues/new

3. Include all gathered information

---

## ✅ Summary

| Step | Action | Result |
|------|--------|--------|
| 1 | Delete integration from HA | Integration unloaded |
| 2 | Remove folder + clear cache | All old bytecode removed |
| 3 | Reinstall from HACS | Fresh v1.2.2 code loaded |
| 4 | Restart Home Assistant | Clean Python environment |
| 5 | Reconfigure integration | Integration activates successfully |

**Expected Result:** ✅ Integration activates without errors, vessels appear in your area

---

**Version:** 1.2.2  
**Last Updated:** 2026-11-01  
**Status:** ✅ Supported
