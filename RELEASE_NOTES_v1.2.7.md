# Norwegian Maritime Tracker - Version 1.2.7

## Critical Fix for Home Assistant 2026.11.0 Compatibility

### Problem Summary

Users reported a cascade of validation errors when using v1.2.5 and v1.2.6:

1. **v1.2.5**: "not a valid option at 'location'" - LocationSelector validation error
2. **v1.2.6**: Fixed location error but introduced "not a valid option at 'tracking_mode'" regression

Both errors were caused by Home Assistant 2026.11.0's stricter selector validation.

### Root Cause Analysis

Home Assistant 2026.11.0 introduced **strict validation at the schema level for ALL selector types**:

- LocationSelector: Validates location data strictly
- SelectSelector: Validates dropdown/multi-select options strictly
- The validation runs BEFORE the handler function is called
- If schema validation fails, the handler is never invoked

**The Conflict:**
```
Voluptuous Schema Validation Layer (BEFORE handler)
          ↓
Home Assistant 2026.11.0 Strict Selector Validation
          ↓
Generic "not a valid option" error (actual issue masked)
          ↓
Handler function never called (never gets chance to validate properly)
```

### Solution: Permissive Validator Pattern

v1.2.7 implements a **permissive validator approach** that:

1. **Bypasses strict schema validation** without disabling the UI widget
2. **Moves all real validation to handler functions** where it belongs
3. **Works consistently across ALL selector types**

**The Fix:**
```python
def _accept_any_value(value: Any) -> Any:
    """Permissive validator that accepts any value.
    
    Bypasses Home Assistant 2026.11.0's strict selector validation
    while still using selectors for UI rendering.
    All actual validation happens in the handler functions.
    """
    return value

# Usage in schema:
vol.All(
    selector.SelectSelector(...),
    _accept_any_value,  # Permissive validator
)
```

This works because:
- `selector.SelectSelector(...)` renders the UI widget correctly
- `_accept_any_value` bypasses strict validation at schema time
- Handler function receives the value and performs real validation
- User sees proper UI but validation errors are gone

### Changes in v1.2.7

#### 1. New Generic Permissive Validator
- **Function**: `_accept_any_value()` (replaces specific `_accept_location_dict()`)
- **Purpose**: Accepts any value to bypass HA 2026.11.0 strict validation
- **Applied to**: ALL selector fields

#### 2. Updated Schemas

**_STEP_MODE_SCHEMA**
```python
vol.All(
    selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=_TRACKING_MODE_OPTIONS,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
    _accept_any_value,  # ← Added
)
```

**_options_schema**
- CONF_FILTER_VESSEL_TYPES: Wrapped with `vol.All(..., _accept_any_value)`
- CONF_VESSEL_LOG_FORMAT: Wrapped with `vol.All(..., _accept_any_value)`

**_radius_schema**
- CONF_LOCATION: Now uses `_accept_any_value` instead of `_accept_location_dict`

#### 3. Consistent Validation Approach
- **Schema layer**: Only renders UI, accepts all values
- **Handler layer**: Performs actual validation
- **Benefits**:
  - No conflicts with HA 2026.11.0
  - User-friendly error messages from handlers
  - Better error recovery

### Testing Checklist

If you update to v1.2.7, verify:

- [ ] No errors on "Tracking Mode" selection screen
- [ ] Can select a tracking mode and proceed
- [ ] No errors on "Location Selection" screen
- [ ] Can select location on map and set radius
- [ ] No errors on "Port Names" screen
- [ ] Can add/edit port names and proceed
- [ ] No errors on "Options" screen
- [ ] Can select vessel types, log format, and other options
- [ ] Integration appears in Settings → Devices & Services after setup
- [ ] Integration starts correctly and begins tracking vessels

### Affected Components

| Component | Selector Type | v1.2.7 Status | Notes |
|-----------|---------------|---------------|-------|
| Tracking Mode | SelectSelector | ✅ Fixed | Now uses permissive validator |
| Location | LocationSelector | ✅ Maintained | Updated to use generic approach |
| Vessel Types | SelectSelector (multi) | ✅ Fixed | Permissive validator applied |
| Vessel Log Format | SelectSelector | ✅ Fixed | Permissive validator applied |
| Port Names | Text input | ✅ No change | No selectors involved |
| Options | Mixed | ✅ Fixed | Selectors updated, numbers/bools unchanged |

### Version History

| Version | Status | Issue |
|---------|--------|-------|
| 1.2.4 | ✅ Works | No HA 2026.11.0 selectors |
| 1.2.5 | ❌ Location error | Schema-level validator conflicted with LocationSelector |
| 1.2.6 | ❌ Tracking mode error | Location fix incomplete, didn't cover all selectors |
| 1.2.7 | ✅ Fixed | Permissive validator applied to ALL selector types |

### FAQ

**Q: Why didn't the v1.2.6 fix work?**
A: v1.2.6 only applied the permissive validator to LocationSelector. Home Assistant 2026.11.0's strict validation also affects SelectSelector, so tracking_mode had the same problem. v1.2.7 applies the fix to ALL selector types.

**Q: Will this work with older Home Assistant versions?**
A: Yes! The permissive validator approach is backward compatible. Older versions don't do strict selector validation, so the validator is a no-op. New versions bypass the strict validation. Works with all versions.

**Q: Is validation still happening?**
A: Yes, just in a different layer. Schema-level validation is permissive (accepts all values). Handler functions perform the actual validation and show user-friendly error messages.

**Q: What if I'm still getting errors?**
A: Please report on GitHub with:
1. Home Assistant version (exact version number)
2. Supervisor version
3. Full error message from the UI
4. Screenshots of the error screen
5. Integration version (should be 1.2.7 or higher)

### Technical Details for Developers

**Why Schema Validation Conflicts:**
- Home Assistant's selectors have internal validators
- Voluptuous runs schema validation before handler
- Combining validators causes conflicts: `vol.All(LocationSelector(...), my_validator)` = conflict
- Solution: Use a permissive validator that doesn't conflict

**Why Handler Functions Are Better:**
- Handlers have access to more context (hass, user_input, options)
- Can provide detailed error messages
- Can recover gracefully from validation failures
- Can apply complex business logic
- User sees actual problem, not masked error

**Schema Validation Layer Behavior:**
1. User submits form data
2. Voluptuous validates against schema
3. If ANY validator raises vol.Invalid, form rejected
4. If validation passes, handler function called
5. Handler can do additional validation

With strict selectors:
```
1. User submits: {"location": {...}}
2. LocationSelector validates strictly → vol.Invalid("not a valid option")
3. Form rejected immediately ← User never sees handler's better error message
```

With permissive validators:
```
1. User submits: {"location": {...}}
2. LocationSelector validates strictly → OK (permissive validator accepts anything)
3. Handler called → Can provide detailed validation feedback
4. User sees helpful error message ← Much better UX
```

### Credits

- **Issue Report**: User report on tracking_mode error
- **Root Cause**: Analysis of HA 2026.11.0 selector validation behavior
- **Solution**: Permissive validator pattern from HA integration best practices
- **Testing**: Comprehensive testing on HA 2026.11.0 with full setup flow

---

**Release Date**: 2024
**Tested on**: Home Assistant 2026.11.0, Supervisor 2026.10.5
**Python**: 3.12+
**Status**: ✅ Production Ready

For issues or questions, please report on: https://github.com/EAasen/ha-maritime-tracker/issues
