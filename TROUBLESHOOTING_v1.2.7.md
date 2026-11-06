# Troubleshooting Guide: v1.2.7 Validation Issues

## If You're Still Seeing Errors After Updating to v1.2.7

### Quick Checklist

1. **Verify you're on v1.2.7 or later**
   - Go to Settings → Devices & Services → Norwegian Maritime Tracker
   - Check the version number
   - If still on v1.2.6, update the integration

2. **Restart Home Assistant**
   - After updating to v1.2.7, restart HA completely
   - Simply reloading the integration is not enough
   - Go to Settings → System → Restart Home Assistant

3. **Clear browser cache**
   - Sometimes browser caches old form UI
   - Press Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
   - Clear cache for the HA domain
   - Refresh the page

### Still Getting "not a valid option at 'tracking_mode'"?

**If the error persists after v1.2.7 update and HA restart:**

1. Check Home Assistant version
   - Go to Settings → System → About
   - If NOT on 2026.11.0+, different issue
   - If on 2026.11.0+, continue below

2. Try removing and re-adding the integration
   - Settings → Devices & Services
   - Find Norwegian Maritime Tracker
   - Click the three dots → Delete
   - Click Create Integration
   - Select "Norwegian Maritime Tracker"
   - Start fresh setup

3. Check the HA logs for errors
   - Settings → System → Logs
   - Search for "marinetraffic"
   - Copy any error messages

### Still Getting "not a valid option at 'location'"?

**This should NOT happen in v1.2.7:**

1. Verify version again
   - Must be v1.2.7 or later
   - If still on v1.2.5 or v1.2.6, update now

2. Try on a different browser
   - Sometimes browser cache/cookies interfere
   - Try incognito/private mode
   - Try different browser (Chrome, Firefox, Safari)

3. Check if you're using a proxy/VPN
   - Some proxies modify form data
   - Try without proxy/VPN temporarily
   - Check HA logs for validation details

### Still Getting "not a valid option" on OTHER fields?

If you see validation errors on fields NOT listed above (options screen, port names, etc.):

1. **This is a different issue** - Not related to v1.2.7 fix
2. Make note of:
   - Exact field name
   - Exact error message
   - Home Assistant version
   - Integration version

3. Report on GitHub issues with this information

### Validation Error Scenarios

**Scenario 1: Error on first setup**
```
Error: "not a valid option at 'tracking_mode'"
Home Assistant: 2026.11.0
Integration: v1.2.7
Solution: Restart HA, clear browser cache, try again
```

**Scenario 2: Error after updating from v1.2.6**
```
Error: still seeing "tracking_mode" error
Solution: Fully restart HA (not just reload), clear cache
```

**Scenario 3: Error on location selection**
```
Error: "not a valid option at 'location'"
Home Assistant: 2026.11.0
Integration: v1.2.7
Solution: Check version again - this should be fixed in v1.2.7
```

**Scenario 4: Error on options screen**
```
Error: "not a valid option at 'vessel_log_format'"
Integration: v1.2.7
Solution: This is a v1.2.7 fix - report if still seeing
```

### How to Report Issues

If none of the above solutions work:

1. **Go to**: https://github.com/EAasen/ha-maritime-tracker/issues

2. **Include in your report**:
   - Home Assistant version (exact number, e.g., 2026.11.0)
   - Supervisor version
   - Integration version (1.2.7 or higher)
   - Python version (Settings → System → Restart → check logs)
   - Exact error message (copy from browser console if possible)
   - Screenshot of error screen
   - Steps to reproduce

3. **Example good report**:
   ```
   Title: v1.2.7 still shows "not a valid option at 'tracking_mode'"
   
   Version Info:
   - HA Core: 2026.11.0
   - Supervisor: 2026.10.5
   - Integration: 1.2.7
   - Python: 3.12.4
   
   Steps to Reproduce:
   1. Fresh install of integration v1.2.7
   2. Go to create new device
   3. Select Norwegian Maritime Tracker
   4. Get "not a valid option at 'tracking_mode'" error on step 2
   
   Error Message (from browser console):
   "error": "not a valid option at 'tracking_mode'"
   
   Browser: Chrome on Windows 11
   ```

### Common Solutions

| Problem | Solution | Status |
|---------|----------|--------|
| "not a valid option at 'tracking_mode'" | Update to v1.2.7, restart HA | ✅ Fixed in v1.2.7 |
| "not a valid option at 'location'" | Update to v1.2.7, restart HA | ✅ Fixed in v1.2.7 |
| "not a valid option at 'vessel_log_format'" | Update to v1.2.7, restart HA | ✅ Fixed in v1.2.7 |
| Form appears but no error | Try another browser/incognito | Usually cache issue |
| Error on other fields | Different issue - report it | Report to GitHub |

### Debug Mode

**If you want to see what data is being sent:**

1. Open browser developer tools (F12)
2. Go to Network tab
3. Try to proceed through setup
4. Look for POST requests to `/api/config/flow`
5. Check the request/response data

**To see Home Assistant internal logs:**

1. Settings → System → Logs
2. Look for entries with "marinetraffic"
3. Or filter by "voluptuous" for schema errors
4. Copy full logs for issue reporting

### Performance Notes

- If setup is very slow, might be location selector rendering
- Location map can take 2-3 seconds to load initially
- This is normal and not a validation error
- Just wait for the UI to fully load before interacting

### Browser Compatibility

Tested on:
- ✅ Chrome 120+
- ✅ Firefox 121+
- ✅ Safari 17+
- ✅ Edge 120+

If using older browser versions, update if possible.

---

**Need more help?**
- Check GitHub issues for similar problems: https://github.com/EAasen/ha-maritime-tracker/issues
- Join Home Assistant Discord for general HA questions: https://discord.gg/home-assistant
- See main documentation: https://github.com/EAasen/ha-maritime-tracker

**Last Updated**: 2024 (v1.2.7)
