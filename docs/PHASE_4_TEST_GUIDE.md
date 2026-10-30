# Phase 4 Test Execution & Verification Guide

**Status**: Phase 4 Implementation Complete ✅  
**Components Ready**: WebSocket API + Custom Lovelace Card  
**Test Infrastructure Ready**: Python tests complete, browser tests pending  
**Coverage Target**: 80%+ Python (enforced in CI), browser coverage via manual/Playwright

---

## Quick Start

### Run WebSocket API Tests
```bash
python -m pytest tests/test_websocket_api.py -v
```

### Run All Phase 4 Tests (Python)
```bash
python -m pytest tests/test_websocket_api.py tests/frontend/ -v --tb=short
```

### Run Python Linting & Type Checking
```bash
python -m mypy custom_components/marinetraffic_tracker/websocket_api.py --strict
ruff check custom_components/marinetraffic_tracker/websocket_api.py custom_components/marinetraffic_tracker/frontend/
```

### Verify Files Exist
```bash
python -c "
import os
required = [
    'custom_components/marinetraffic_tracker/websocket_api.py',
    'custom_components/marinetraffic_tracker/frontend/__init__.py',
    'custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js',
    'tests/test_websocket_api.py',
    'tests/frontend/__init__.py',
]
for f in required:
    assert os.path.exists(f), f'Missing: {f}'
    print(f'✓ {f}')
"
```

---

## Phase 1, 2, & 3 Completion Verification

Before starting Phase 4 tests, verify all prior phases are passing:

### Phase 1: Snapshot & Compatibility

```bash
python -m pytest tests/test_snapshot.py tests/test_kystverket_client.py tests/test_coordinator_snapshot.py tests/test_phase_1_extended.py -v
```

### Phase 2: Status Transitions & Persistence

```bash
python -m pytest tests/test_vessel_events.py tests/test_storage.py -v
```

### Phase 3: Watchlist & Configuration

```bash
python -m pytest tests/test_watchlist.py tests/test_config_flow.py tests/test_sensor_attributes.py -v
```

**Completion gate:** If any prior phase fails, Phase 4 tests cannot be validated. Complete all Phase 1/2/3 tests first.

---

## Phase 4 Test Coverage

### Test Files Created/Modified

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_websocket_api.py` | 20+ new | WebSocket API bounded responses, pagination, stale detection, trail truncation |
| `tests/frontend/__init__.py` | 15+ placeholders | Frontend card lifecycle, map interactions, vessel selection, trail rendering |
| `tests/test_integration.py` | +2 | WebSocket registration, card asset loading |
| `custom_components/marinetraffic_tracker/__init__.py` | +1 func | WebSocket API registration |

**Total**: 35+ new/extended tests for Phase 4

### Test Categories

#### T011: WebSocket API Implementation

**Core Functionality Tests:**
- `test_bounded_snapshot_empty` — Empty coordinator returns no vessels
- `test_bounded_snapshot_single` — Single vessel included with full metadata
- `test_bounded_snapshot_multiple` — Multiple vessels paginated (max 100 per page)
- `test_bounded_snapshot_respects_max_per_page` — Pagination respects configured limit
- `test_snapshot_marks_stale_vessels` — Stale vessels marked with `is_stale=True`
- `test_snapshot_marks_watched_vessels` — Watched vessels marked with `is_watched=True`
- `test_stale_detection_by_timeout` — Stale timeout correctly applied to each vessel
- `test_snapshot_sorting_by_distance` — Vessels sorted by distance from reference point
- `test_snapshot_includes_pagination_info` — Pagination metadata present and correct

**Pagination Tests:**
- `test_snapshot_pagination_skip_and_limit` — Skip/limit parameters work correctly
- `test_snapshot_pagination_beyond_bounds` — Skip beyond vessel count returns empty
- `test_snapshot_pagination_respects_stale_filter` — Stale vessels excluded from pagination

**Trail Tests:**
- `test_bounded_trail_empty` — No position history returns empty trail
- `test_bounded_trail_single_point` — Single point included correctly
- `test_bounded_trail_multiple_points_truncated` — Multiple points truncated to max (50)
- `test_trail_respects_max_points` — Trail respects configured point limit
- `test_trail_timestamp_ordering` — Trail points in chronological order
- `test_trail_coordinate_validation` — Invalid coordinates filtered out

**WebSocket Handler Tests:**
- `test_handle_subscribe_valid` — Subscribe handler registers callback correctly
- `test_handle_subscribe_persists_connection` — Subscription persists across messages
- `test_handle_unsubscribe_removes_callback` — Unsubscribe removes listener
- `test_handle_get_snapshot_returns_bounded` — get_snapshot returns bounded response
- `test_handle_get_trail_returns_bounded` — get_trail returns bounded trail
- `test_handle_invalid_entry_id` — Invalid entry_id rejected safely
- `test_handle_subscription_on_coordinator_update` — Subscription fires on coordinator change
- `test_handle_cleanup_on_disconnect` — All subscriptions cleaned up on disconnect

#### T012: WebSocket Tests

All tests listed above are in `tests/test_websocket_api.py` and use mocked `MagicMock` objects for:
- `hass` connection (no real Home Assistant needed)
- `coordinator` with mock vessel data
- No live network calls
- No authentication required

#### T013/T014: Frontend Card Implementation

**Frontend Card Lifecycle Tests** (in `tests/frontend/__init__.py`):

1. **Card Registration & Config**
   - [ ] Card element registers as custom element
   - [ ] Card accepts `setConfig()` with valid configuration object
   - [ ] Card exposes `getCardSize()` returning integer
   - [ ] Card exposes `getLayoutOptions()` with supported layout types

2. **Map Initialization**
   - [ ] Map container created when card inserted into DOM
   - [ ] Leaflet map instance created with correct center/zoom
   - [ ] Map tiles load from configured provider
   - [ ] Map resize handles on window resize
   - [ ] Map invalidate called on responsive layout change

3. **WebSocket Connection**
   - [ ] Card opens WebSocket connection to Home Assistant on setup
   - [ ] Card sends `subscribe` command on connection
   - [ ] Card reconnects on connection loss
   - [ ] Card cleans up on card removal from DOM

4. **Vessel Markers**
   - [ ] Vessel markers added to map for each vessel in snapshot
   - [ ] Marker color reflects status: blue (in area), orange (nearby), gray (stale)
   - [ ] Marker icon shows heading indicator
   - [ ] Marker popup shows vessel name and MMSI
   - [ ] Marker click selects vessel and shows details pane
   - [ ] Stale vessels marked with "unavailable" badge

5. **Heading Indicators**
   - [ ] Heading line drawn from marker in correct direction
   - [ ] Heading line length configurable
   - [ ] Heading line color matches marker
   - [ ] Heading line removed when vessel stale

6. **Position Trails**
   - [ ] Trail polyline drawn for selected vessel
   - [ ] Trail contains all points from trail response
   - [ ] Trail color distinct from markers
   - [ ] Trail updated on new WebSocket message
   - [ ] Trail removed when vessel deselected
   - [ ] Trail gaps (stale periods) rendered as disconnected segments

7. **Details Pane**
   - [ ] Details pane shows when vessel selected
   - [ ] Pane displays: MMSI, Name, Status, Position, Heading, Speed, Last Seen
   - [ ] Stale vessels show "Last seen X minutes ago"
   - [ ] Pane close button deselects vessel
   - [ ] Pane scrollable on small screens

8. **Watched Vessel Highlighting**
   - [ ] Watched vessels have distinct marker color/border
   - [ ] Watched vessel label shown in details pane
   - [ ] Star/heart icon next to name in pane
   - [ ] Clicking watch button on details pane updates watchlist

9. **Map Controls**
   - [ ] "Fit All" button centers and zooms to show all vessels
   - [ ] "Reset View" button returns to configured center/zoom
   - [ ] "Layer Toggle" button switches between map tile providers
   - [ ] "Search" input filters vessels by MMSI or name
   - [ ] Search results highlight matching vessels

10. **Area Outline**
    - [ ] Circle drawn for radius-based area query
    - [ ] Rectangle drawn for bounding-box area query
    - [ ] Area outline color configurable
    - [ ] Area outline transparent/semi-transparent

11. **Live Updates**
    - [ ] New WebSocket message updates marker positions
    - [ ] Position updates animate smoothly (optional)
    - [ ] New vessels added to map
    - [ ] Disappeared vessels removed from map
    - [ ] Status changes update marker color immediately
    - [ ] Trail extends with new points
    - [ ] Details pane updates without losing selection

12. **Mobile Responsiveness**
    - [ ] Card renders on small screens (< 768px)
    - [ ] Details pane switches to modal/overlay on mobile
    - [ ] Map controls stack vertically on mobile
    - [ ] Touch interactions work (tap to select, pan, pinch-zoom)
    - [ ] Card readable at mobile default zoom levels

13. **Error Handling**
    - [ ] WebSocket connection error shows alert/banner
    - [ ] Missing vessel data handled gracefully
    - [ ] Invalid coordinates filtered out
    - [ ] Missing tiles don't block map interaction
    - [ ] Recovery after temporary connection loss

#### T015: Frontend Test Infrastructure

**Test Framework Setup:**
- [ ] `tests/frontend/__init__.py` contains test classes with descriptive names
- [ ] Test docstrings explain what each test validates
- [ ] Mock setup provides representative Home Assistant state
- [ ] Card HTML fixture renders without errors
- [ ] WebSocket mock sends realistic message payloads

---

## Integration Tests

### WebSocket API Registration

Test that WebSocket API is properly registered on integration startup:

```bash
python -m pytest tests/test_integration.py::test_websocket_api_registration -v
```

**Expected behavior:**
- `async_register_websocket_api()` called once per integration entry
- All four commands (subscribe, unsubscribe, get_snapshot, get_trail) registered
- Commands callable from Home Assistant frontend
- No errors logged during registration

### Frontend Asset Loading

Test that frontend assets are discovered by Home Assistant:

```bash
python -m pytest tests/test_integration.py::test_frontend_assets_registered -v
```

**Expected behavior:**
- `maritime-tracker-card.js` found in frontend directory
- Card asset registration succeeds
- No 404 errors when loading card

### Full Integration: WebSocket → Card Flow

**Manual test (requires Home Assistant instance):**

1. Add integration to Home Assistant with Kystverket credentials
2. Add maritime tracker card to dashboard via UI
3. Observe:
   - [ ] Map loads with no errors in browser console
   - [ ] Vessels appear as markers on map
   - [ ] Markers update position in real-time (every WebSocket update)
   - [ ] Clicking vessel shows details pane
   - [ ] Selecting vessel draws trail
   - [ ] Watched vessels highlighted differently
   - [ ] Stale vessels shown as gray/unavailable
   - [ ] Card controls work (fit all, reset view, layer toggle)
   - [ ] No WebSocket connection errors in browser console
   - [ ] No JavaScript errors in browser console

---

## Quality Gates

### Python Code Quality

```bash
# Syntax validation
python -m py_compile custom_components/marinetraffic_tracker/websocket_api.py

# Type checking (strict mode)
python -m mypy custom_components/marinetraffic_tracker/websocket_api.py --strict

# Linting
ruff check custom_components/marinetraffic_tracker/websocket_api.py

# Format checking
ruff format --check custom_components/marinetraffic_tracker/websocket_api.py
```

**Expected results:**
- [ ] No syntax errors
- [ ] No type mismatches
- [ ] Linting passes with 0 violations
- [ ] All code formatted correctly

### JavaScript Code Quality

```bash
# Syntax validation via Node.js (if available)
node -c custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js

# Or manual inspection of:
# - ES6+ syntax correctness
# - No undefined variable references
# - No console errors when card loads
# - No XSS vulnerabilities (all user input sanitized)
```

**Expected results:**
- [ ] No syntax errors
- [ ] No undefined variables
- [ ] Card loads without errors
- [ ] No security issues

### Test Coverage

```bash
python -m pytest tests/test_websocket_api.py --cov=custom_components/marinetraffic_tracker/websocket_api --cov-report=term-missing
```

**Expected results:**
- [ ] WebSocket API coverage ≥ 85%
- [ ] All critical paths covered
- [ ] No uncovered branches in bounded snapshot/trail logic

---

## Phase 4 Acceptance Checklist

### Python Tests
- [ ] `test_websocket_api.py` pytest command exits with code `0`
- [ ] All 20+ WebSocket API tests pass
- [ ] No skipped or deselected tests without documented reason
- [ ] Type checking passes (mypy strict mode)
- [ ] Linting passes (ruff)

### Frontend Tests
- [ ] Frontend test placeholders in place
- [ ] All 13 card lifecycle test categories have clear steps
- [ ] Test environment setup documented
- [ ] Manual test checklist includes all critical flows

### Documentation
- [ ] `PHASE_4_IMPLEMENTATION_SUMMARY.md` up-to-date with all deliverables
- [ ] `docs/architecture.md` includes Phase 4 components and data flow
- [ ] `docs/usage.md` includes maritime tracker card configuration
- [ ] `CHANGELOG.md` documents Phase 4 features and fixes

### Code Quality
- [ ] WebSocket API passes syntax, type, and lint checks
- [ ] Frontend card JavaScript has no syntax errors
- [ ] All imports and dependencies available
- [ ] No breaking changes to existing entities or sensors
- [ ] Entry isolation verified (two entries don't cross-contaminate)

### Integration
- [ ] WebSocket API registration succeeds in `async_setup_entry()`
- [ ] Frontend assets discoverable by Home Assistant
- [ ] Card can be added to dashboard via UI
- [ ] No errors in Home Assistant logs during card interaction

### Version & Git
- [ ] All Phase 4 commits present in git history
- [ ] CHANGELOG.md reflects Phase 4 in "Unreleased" section
- [ ] No uncommitted changes to Phase 4 files

---

## Execution Record Template

Use this template to document Phase 4 test execution:

```markdown
## Phase 4 Test Execution Record

**Date**: YYYY-MM-DD  
**Tester**: [Name/Email]  
**Environment**: 
- OS: [Windows/macOS/Linux]
- Python: [version]
- Home Assistant: [version, if tested]
- Node.js: [version, if available]

### Python Test Execution

**WebSocket API Tests**
```
Command: python -m pytest tests/test_websocket_api.py -v
Exit Code: 0
Output:
[Paste full pytest output here]
Pass/Skip/Fail Counts: X passed, Y skipped, Z failed
```

**Type Checking**
```
Command: python -m mypy custom_components/marinetraffic_tracker/websocket_api.py --strict
Exit Code: 0
Output:
[Paste mypy output, or "Success: no issues found"]
```

**Linting**
```
Command: ruff check custom_components/marinetraffic_tracker/websocket_api.py
Exit Code: 0
Output:
[Paste ruff output, or describe: 0 violations found]
```

### Frontend Test Execution

**Browser Environment Setup**
- [ ] Home Assistant instance running
- [ ] Integration added with valid Kystverket credentials
- [ ] Maritime tracker card added to dashboard
- [ ] Browser DevTools open with console visible

**Manual Test Results**

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | Map loads without errors | PASS/FAIL | ... |
| 2 | Vessels appear as markers | PASS/FAIL | ... |
| 3 | Markers update in real-time | PASS/FAIL | ... |
| 4 | Clicking vessel shows details pane | PASS/FAIL | ... |
| 5 | Selecting vessel draws trail | PASS/FAIL | ... |
| 6 | Watched vessels highlighted | PASS/FAIL | ... |
| 7 | Stale vessels shown as gray | PASS/FAIL | ... |
| 8 | Card controls work (fit all, etc.) | PASS/FAIL | ... |
| 9 | No console errors | PASS/FAIL | ... |
| 10 | No WebSocket errors | PASS/FAIL | ... |

### Summary

**Overall Result**: PASS / FAIL  
**Phase 4 Status**: ✅ VERIFIED / ❌ BLOCKED  

**Blockers (if any)**:
- [Issue description and mitigation]

**Sign-off**: [Tester Name], [Timestamp]
```

---

## Troubleshooting

### WebSocket API Tests Fail

**Symptom**: `pytest tests/test_websocket_api.py` exits with code 1

**Diagnostics**:
1. Check Python 3.12+ installed: `python --version`
2. Check pytest installed: `python -m pytest --version`
3. Check imports: `python -c "from tests.test_websocket_api import *"`
4. Run with verbose traceback: `python -m pytest tests/test_websocket_api.py -vv --tb=long`

**Common issues**:
- Missing `pytest-homeassistant-custom-component`: Install with `pip install pytest-homeassistant-custom-component==0.13.205`
- Import errors in test file: Check syntax with `python -m py_compile tests/test_websocket_api.py`
- Mock setup incorrect: Verify `MagicMock` objects have required attributes (see test file docstrings)

### Type Checking Fails

**Symptom**: `mypy` reports type errors in `websocket_api.py`

**Diagnostics**:
1. Check mypy installed: `python -m mypy --version`
2. Run with show-error-context: `mypy --show-error-context --pretty websocket_api.py`
3. Review error lines and fix annotations

**Common issues**:
- Dict/List type hints incomplete: Use `dict[str, Any]` not `dict`
- Callback signatures: Callbacks must match registered type hints
- Optional types: Use `T | None` or `Optional[T]`, not bare `T`

### Frontend Card Not Loading in Home Assistant

**Symptom**: Card doesn't appear in card selector or shows blank/error

**Diagnostics**:
1. Check browser console for errors (F12 → Console tab)
2. Check Home Assistant logs: Settings → Logs
3. Verify card file exists: `ls custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js`
4. Check integration version matches asset registration

**Common issues**:
- Missing Leaflet library: Check CDN is accessible and HTTPS enabled
- Asset path wrong: Check frontend `__init__.py` registration paths
- JavaScript syntax error: Validate with `node -c maritime-tracker-card.js`
- Lovelace cache: Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

### WebSocket Connection Fails in Browser

**Symptom**: Card shows "Connection error" or no data updates

**Diagnostics**:
1. Check Home Assistant WebSocket URL: `wss://[host]/api/websocket`
2. Check integration registered command: Home Assistant → Developer Tools → States → Look for websocket API logs
3. Check browser console for WebSocket errors
4. Check entity_id is set correctly in card config

**Common issues**:
- HTTPS required: WebSocket must use `wss://`, not `ws://`
- Port mismatch: Ensure port number correct for HA instance
- Auth token expired: Try logging out/in to Home Assistant
- Command not registered: Check `async_register_websocket_api()` called in `__init__.py`

### Stale Detection Not Working

**Symptom**: Vessels marked as stale but shouldn't be, or vice versa

**Diagnostics**:
1. Check vessel `last_seen` timestamp in coordinator
2. Check `stale_timeout` configuration in integration options
3. Verify system time synchronized on Home Assistant host
4. Run test: `python -m pytest tests/test_websocket_api.py::TestBoundedSnapshot::test_stale_detection_by_timeout -vv`

**Common issues**:
- Timezone mismatch: Ensure all timestamps UTC or consistently localized
- Stale timeout too short: Default 300s (5 min), may need adjustment for live API
- Coordinator not updating: Verify vessel feed polling active

### Trail Points Not Appearing

**Symptom**: Vessel selected but no trail polyline drawn

**Diagnostics**:
1. Check vessel has position history: `test_bounded_trail_multiple_points_truncated`
2. Verify trail response has coordinate points
3. Check Leaflet `L.polyline()` not throwing errors in browser console
4. Verify map instance has correct CRS (coordinate reference system)

**Common issues**:
- Trail max points set to 0: Check `stale_timeout` not accidentally 0
- Position history not collected: Coordinator needs multiple observations
- Coordinate format wrong: Should be `[lat, lon]` not `[lon, lat]`
- Missing polyline CSS: Check browser DevTools → Elements tab for style

---

## Next Steps

### Immediate (after Phase 4 verification)
1. Record Phase 4 test execution in this guide's Execution Record Template
2. If all tests pass, mark Phase 4 as ✅ VERIFIED in `PROJECT_STATUS.md`
3. Archive test evidence (screenshots, logs, execution records)

### Before Phase 5
1. Set up Home Assistant test environment with Playwright/browser automation
2. Migrate frontend test placeholders to automated Playwright tests
3. Add Phase 4 integration tests to CI/CD pipeline (currently Python-only)

### Future Improvements
- Screenshot comparison tests for frontend card
- E2E tests with real Kystverket API mock
- Performance profiling for large vessel datasets (100+)
- Accessibility testing (a11y) for card UI

---

## References

- **Feature Plan**: `flightradar-feature-plan.md` (Phase 4 requirements)
- **Implementation Summary**: `PHASE_4_IMPLEMENTATION_SUMMARY.md` (tasks T011-T015)
- **Architecture**: `docs/architecture.md` (Phase 4 components and data flow)
- **Usage**: `docs/usage.md` (card configuration and user guide)
- **Project Status**: `PROJECT_STATUS.md` (overall integration status)

---

**Phase 4 Completion Gate:** Phase 4 is verified only when all Python tests pass (exit code 0), code quality checks pass (mypy, ruff), and manual integration test completes successfully. Browser automation tests are recommended but not blocking for release.
