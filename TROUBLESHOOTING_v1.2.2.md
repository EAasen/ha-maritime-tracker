# Troubleshooting v1.2.2 - Activation Errors

## Problem: `TypeError: async_register_command() got an unexpected keyword argument 'allow_user_context'`

### Error Details
```
TypeError: async_register_command() got an unexpected keyword argument 'allow_user_context'
Location: custom_components/marinetraffic_tracker/websocket_api.py, line 99
```

### Why This Happens

Home Assistant 2026.10.4+ removed the `allow_user_context` parameter from `websocket_api.async_register_command()`. The current v1.2.2 code is correct and doesn't use this parameter, but the error indicates:

1. **Stale cached bytecode** — Your Home Assistant has old .pyc files from v1.2.1 or earlier
2. **Incomplete upgrade** — The integration wasn't fully removed/reinstalled
3. **Cache corruption** — Python's import cache has stale module information

### Quick Fix (All Platforms)

#### Step 1: Remove Integration from Home Assistant
1. Settings → Devices & Services
2. Find "Norwegian Maritime Tracker"
3. Click `⋮` (three dots) → Delete Integration
4. Confirm deletion

#### Step 2: Clear Custom Component Directory
Connect to your Home Assistant via SSH and run:

```bash
# Go to custom_components directory
cd /config/custom_components/

# Remove the old integration
rm -rf marinetraffic_tracker/

# Clear all Python cache files
find /config -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /config -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
find /config -type f -name "*.pyc" -delete 2>/dev/null
```

#### Step 3: Reinstall Integration

**Using HACS (Recommended):**
1. HACS → Integrations → ⋯ → Custom repositories
2. Add: `https://github.com/EAasen/ha-maritime-tracker`
3. Category: `Integration`
4. Click `Install`
5. Restart Home Assistant (Settings → System → Restart)

**Manual Installation:**
1. Download latest release: https://github.com/EAasen/ha-maritime-tracker/releases
2. Copy `custom_components/marinetraffic_tracker/` to `config/custom_components/`
3. Restart Home Assistant

#### Step 4: Reconfigure Integration
1. Settings → Devices & Services
2. Click "Create Automation" (or "New Integration")
3. Search for "Norwegian Maritime Tracker"
4. Enter configuration:
   - **Latitude**: Your area latitude
   - **Longitude**: Your area longitude  
   - **Radius (km)**: Search radius (e.g., 2.5)
   - **Update Interval**: Minutes between updates (e.g., 5)
5. Click Submit

### Platform-Specific Instructions

#### Home Assistant Operating System (HAOS)
```bash
# SSH into your HAOS device
ssh [user]@[ip-address]

# Navigate and clean
cd /config/custom_components/
rm -rf marinetraffic_tracker/
find /config -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /config -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null

# Exit SSH
exit
```
Then use HACS to reinstall.

#### Docker
```bash
# Execute commands in Home Assistant container
docker exec homeassistant bash -c '
  cd /config/custom_components
  rm -rf marinetraffic_tracker/
  find /config -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
  find /config -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
'

# Restart Home Assistant
docker restart homeassistant
```

#### Home Assistant Core (Python)
```bash
# In your Python virtual environment
cd /path/to/homeassistant/config/custom_components/
rm -rf marinetraffic_tracker/

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Restart Home Assistant
systemctl restart homeassistant  # if using systemd
```

### Verification

After reinstalling, verify:

1. **No errors in logs**
   - Settings → System → Logs
   - Should NOT contain "allow_user_context"

2. **Integration appears**
   - Settings → Devices & Services
   - Should show "Norwegian Maritime Tracker (58.8902, 5.7484) r=2.5km" (with your values)

3. **Entities created**
   - Developer Tools → States
   - Should show `device_tracker.maritime_tracker_*` entities

4. **WebSocket API working**
   - No errors in logs related to WebSocket API

### Advanced Troubleshooting

#### Check Installed Version
```bash
# SSH into Home Assistant
ssh [user]@[ip-address]
cat /config/custom_components/marinetraffic_tracker/manifest.json | grep version
```

Should show: `"version": "1.2.2"`

#### Verify Code is Correct
```bash
# Check for deprecated 'allow_user_context' usage
grep -n "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py
```

Should return: **(no output)** — This is correct!

#### Check Home Assistant Version
1. Settings → About
2. Should show: **Home Assistant 2026.10.4 or later**

If older, update Home Assistant first:
1. Settings → System
2. Check "Updates available" banner
3. Click "Install" to update

#### View Full Error Logs
1. Settings → System → Logs
2. Search for "marinetraffic_tracker"
3. Copy full error traceback
4. Report on GitHub: https://github.com/EAasen/ha-maritime-tracker/issues

### What Changed in v1.2.2

| Aspect | v1.2.1 | v1.2.2 |
|--------|--------|--------|
| API Parameter | `allow_user_context=False` | ❌ Removed |
| WebSocket Import | `hass.components.websocket_api` | `from homeassistant.components import websocket_api` |
| Home Assistant Min | 2026.10.3 | 2026.10.4+ |
| Status | Deprecated API | Modern API |

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Error persists after reinstall | Clear Python cache more thoroughly (see above), ensure HA version ≥ 2026.10.4 |
| Integration doesn't appear in UI | Check logs for import errors, verify manifest.json is valid |
| Entities not created | Integration loaded but WebSocket API failed, check logs for other errors |
| Can't SSH to Home Assistant | Use Web Terminal add-on, or check home-assistant.io documentation for SSH setup |

### Still Having Issues?

1. **Collect Information**
   - Home Assistant version (Settings → About)
   - Full error traceback (Settings → System → Logs)
   - Installation method (HACS or manual)
   - Output of: `grep -c "allow_user_context" /config/custom_components/marinetraffic_tracker/websocket_api.py`

2. **Report Issue**
   - Open: https://github.com/EAasen/ha-maritime-tracker/issues/new
   - Include collected information
   - Describe steps you've taken

3. **Temporary Workaround**
   - Downgrade to v1.2.1 (if your HA version supports it)
   - Or upgrade Home Assistant to latest version if currently < 2026.10.4

### References

- [Home Assistant WebSocket API Documentation](https://developers.home-assistant.io/docs/api/websocket)
- [Integration Development Guide](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [GitHub Repository](https://github.com/EAasen/ha-maritime-tracker)
