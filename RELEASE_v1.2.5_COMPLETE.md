# v1.2.5 Release - Published to GitHub ✅

## Release Information

**Version:** 1.2.5  
**Release Date:** November 6, 2026  
**GitHub Release:** https://github.com/EAasen/ha-maritime-tracker/releases/tag/v1.2.5  
**Status:** Published and Available

## What's Fixed

### 🐛 Critical Bug Fix: Location Validation Error

Users were experiencing this error during setup:
```
not a valid option at 'location'
```

This has been **completely fixed** with a comprehensive schema-level validator.

### The Fix

Added proper voluptuous schema validation for the LocationSelector field:

1. **New Function:** `_validate_location()` 
   - Validates location dictionary format
   - Checks latitude/longitude presence and range
   - Validates radius if provided
   - Type coercion to floats

2. **Updated Schema:** `_radius_schema()`
   - Uses `vol.All()` to chain validator with LocationSelector
   - Runs validation at form submission time
   - Prevents generic voluptuous errors

3. **Benefits:**
   - ✅ Clear, specific error messages
   - ✅ Early validation catches issues
   - ✅ Better user experience
   - ✅ Backward compatible

## Release Contents

### Code Changes
- `custom_components/marinetraffic_tracker/config_flow.py`
  - Added `_validate_location()` function
  - Updated `_radius_schema()` to use validator
  - Improved error handling

### Documentation
- `docs/v1.2.5_LOCATION_FIX.md` - Technical documentation
- `docs/v1.2.5_QUICK_FIX.md` - User troubleshooting guide
- `FIX_SUMMARY_v1.2.5.md` - Implementation summary
- `RELEASE_NOTES_v1.2.5.txt` - GitHub release notes

## Installation

### For HACS Users
Updates will be available through Home Assistant's built-in HACS integration manager within 24-48 hours.

**To update manually:**
1. Settings → Devices & Services → Integrations
2. Find "Norwegian Maritime Tracker"
3. Click the menu (⋮) → "Remove"
4. Search for "Norwegian Maritime Tracker" again
5. Click "Create Integration"

### For Manual Installation
```bash
cd ha-maritime-tracker
git pull origin main
# Restart Home Assistant
```

## Testing Checklist

✅ Valid locations in Norwegian waters  
✅ Invalid locations show proper errors  
✅ Missing coordinates handled gracefully  
✅ Out-of-range values validated  
✅ Radius validation working  
✅ Error messages user-friendly  
✅ Backward compatible with existing configs  
✅ Fresh installations work correctly  

## Commits Included

1. **d7f455e** - v1.2.5 patch: Fix location validation in config flow with schema-level validator
2. **265b7c7** - Add comprehensive documentation for v1.2.5 location validation fix
3. **77f1376** - Add release notes for v1.2.5

## GitHub Release Page

The release is now live at:
👉 https://github.com/EAasen/ha-maritime-tracker/releases/tag/v1.2.5

## Compatibility

- ✅ Home Assistant 2026.10.4+
- ✅ Python 3.11+
- ✅ All platforms (Linux, macOS, Windows)
- ✅ HACS compatible

## Next Steps

1. **Users:** Update through HACS or manually pull the latest version
2. **Testing:** Verify the location selection works on your setup
3. **Feedback:** Report any issues on GitHub

## Support

If users encounter issues:

1. **First:** Clear browser cache and restart Home Assistant
2. **Check:** Home Assistant version (Settings → About)
3. **Review:** [v1.2.5_QUICK_FIX.md](docs/v1.2.5_QUICK_FIX.md)
4. **Report:** Open an issue on GitHub with:
   - Home Assistant version
   - Steps to reproduce
   - Browser and OS
   - Screenshots of errors

## Summary

✅ Bug fixed and tested  
✅ Code committed to main branch  
✅ Documentation created and included  
✅ GitHub release published  
✅ Ready for user deployment  

**Status: PRODUCTION READY 🚀**

---

**Last Updated:** November 6, 2026  
**Released By:** Copilot SDK  
**Release Quality:** Stable
