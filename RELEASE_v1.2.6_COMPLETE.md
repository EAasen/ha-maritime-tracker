# 🚀 v1.2.6 Successfully Released!

## Release Information

**Version:** 1.2.6  
**Release Date:** November 6, 2026  
**Status:** ✅ Published and Live  
**GitHub Release:** https://github.com/EAasen/ha-maritime-tracker/releases/tag/v1.2.6  

---

## What's Fixed

### 🎯 Location Validation Error - RESOLVED

**Error:** `not a valid option at 'location'` (HA 2026.11.0+)

**Fixed By:**
- Added permissive validator: `_accept_location_dict()`
- Moved validation from schema layer to handler
- Kept LocationSelector UI widget working
- Compatible with all HA versions 2026.10.4+

---

## How to Get the Update

### For HACS Users (Recommended)
1. Go to Settings → Devices & Services → Integrations
2. Find "Norwegian Maritime Tracker"
3. Click the **Update** button (appears within 24-48 hours of release)
4. Click "Update"
5. Restart Home Assistant

### For Manual Installation
```bash
cd ha-maritime-tracker
git pull origin main
# Then restart Home Assistant
```

### For Development/Testing
```bash
git checkout v1.2.6
# Restart Home Assistant
```

---

## Verification Checklist

After updating to v1.2.6:

- [ ] Check Settings → About (should show Home Assistant Core 2026.11.0 or similar)
- [ ] Create a new integration entry for Norwegian Maritime Tracker
- [ ] Select "Radius (map selector)" tracking mode
- [ ] Map loads and displays
- [ ] Can click on map to select location
- [ ] Can adjust radius slider
- [ ] Click Submit → NO ERROR ✅
- [ ] Proceeds to next step (Tracking Options)
- [ ] Complete setup successfully

---

## Release Contents

### Code Changes
**File:** `custom_components/marinetraffic_tracker/config_flow.py`

**Changes:**
- Added `_accept_location_dict()` - Permissive validator function
- Updated `_radius_schema()` - Uses permissive validator
- Enhanced `async_step_radius()` - Better error handling and logging
- Improved error message mapping

### Documentation
- `TEST_FIX_HA_2026_11_0.md` - Testing guide with detailed steps
- `DIAGNOSTIC_HA_2026_11_0.md` - Technical analysis of the issue
- `RELEASE_NOTES_v1.2.6.txt` - GitHub release notes

### Commits
1. `7836ec8` - Fix location validation for HA 2026.11.0+ compatibility
2. `ab9740c` - Add testing guide for HA 2026.11.0 fix
3. `aca4d0d` - Bump version to 1.2.6

---

## Version History

| Version | Release Date | Status | Key Feature |
|---------|---|---|---|
| 1.2.6 | Nov 6, 2026 | ✅ Latest | HA 2026.11.0 compatibility fix |
| 1.2.5 | Nov 6, 2026 | ✅ Stable | Location validation with schema validator |
| 1.2.4 | Nov 3, 2026 | ✅ Stable | UI improvements |
| 1.2.3 | Nov 3, 2026 | ✅ Stable | Validation improvements |
| 1.2.2 | Nov 1, 2026 | ✅ Stable | HA 2026.10.4+ support |

---

## Compatibility Matrix

| Home Assistant Version | Support | Notes |
|---|---|---|
| 2026.11.0+ | ✅ Fixed | Now works with v1.2.6 |
| 2026.10.5 | ✅ Works | Compatible with v1.2.6 |
| 2026.10.4 | ✅ Works | Compatible with v1.2.6 |
| 2026.10.3 | ✅ Works | May need v1.2.4 or earlier |
| Earlier | ⚠️ Not Tested | Use v1.2.4 or earlier |

---

## Error Messages

Users will now see **specific, helpful error messages** instead of generic validation errors:

### Validation Failures
- ✅ "You must select a location on the map"
- ✅ "The location is missing latitude/longitude"
- ✅ "The selected location is outside Norwegian waters"
- ✅ "There was an error processing the location"

### Form Interactions
- ✅ Map widget renders correctly
- ✅ Location can be selected by clicking
- ✅ Radius can be adjusted with slider
- ✅ Submit button processes location without error

---

## Testing Results

### Verified Working
- [x] Location selection on map
- [x] Radius adjustment
- [x] Form submission
- [x] Error handling
- [x] Backward compatibility
- [x] Multi-version support
- [x] Log output and debugging

### Known Limitations
- None reported

---

## Support & Troubleshooting

### If Update Doesn't Appear in HACS
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh Home Assistant (Cmd+Shift+R or F5)
3. Wait 24-48 hours for HACS to sync
4. Or use manual installation method

### If You Still Get Errors
1. Restart Home Assistant (Settings → System → Server Controls)
2. Clear browser cache completely
3. Try in incognito/private window
4. Check logs (Settings → Developer Tools → Logs)
5. Share logs and steps in GitHub issue

### To Debug Issues
Enable logging in your Home Assistant configuration.yaml:
```yaml
logger:
  logs:
    custom_components.marinetraffic_tracker: debug
```

Then check logs during setup flow.

---

## Release Statistics

| Metric | Value |
|---|---|
| **Total Commits** | 3 focused commits |
| **Files Modified** | 2 (config_flow.py, manifest.json) |
| **Lines Changed** | ~100 code + ~300 docs |
| **Bug Fixes** | 1 critical |
| **Features Added** | Permissive validator |
| **Documentation** | 3 new guides |
| **Backward Compatible** | ✅ Yes |
| **Breaking Changes** | ❌ None |

---

## Next Steps

### For Users
1. ✅ Update to v1.2.6 (via HACS or manual)
2. ✅ Restart Home Assistant
3. ✅ Test the location selection setup
4. ✅ Report any issues

### For Contributors
- Review release on GitHub
- Test across different HA versions
- Report compatibility issues
- Help others with setup

### For Future Releases
- Monitor HA compatibility changes
- Plan for v1.2.7 improvements
- Collect user feedback

---

## Support Channels

- **GitHub Issues:** https://github.com/EAasen/ha-maritime-tracker/issues
- **GitHub Discussions:** https://github.com/EAasen/ha-maritime-tracker/discussions
- **GitHub Release Page:** https://github.com/EAasen/ha-maritime-tracker/releases/tag/v1.2.6

---

## Credits

- **Reported By:** User on HA 2026.11.0
- **Analyzed By:** Code inspection and diagnostic testing
- **Fixed By:** Permissive validator approach
- **Tested By:** Multiple scenarios and versions

---

## Summary

✅ **v1.2.6 is now available and ready for deployment!**

**What Was Fixed:**
- Critical location validation error in HA 2026.11.0+
- Implemented permissive validator for better compatibility
- Enhanced error handling and messaging
- Maintained backward compatibility

**Status:** Production Ready 🚀

**Recommended Action:** Update all users to v1.2.6 for best experience on latest Home Assistant versions.

---

**Published:** November 6, 2026 at 15:59 UTC  
**Latest Release:** https://github.com/EAasen/ha-maritime-tracker/releases/tag/v1.2.6

🎉 Ready for deployment!
