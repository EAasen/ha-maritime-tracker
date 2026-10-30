# Maritime Dashboard Map Implementation Progress

**Status**: Phase 1 Complete ✅ | Phase 2 Complete ✅
**Date Started**: 2024-10-30  
**Last Updated**: 2026-10-30 (Phase 1/2 verified)

## Overview

This document tracks the implementation of four features for the Norwegian Maritime Tracker integration, following the feature plan in `docs/flightradar-feature-plan.md`.

### Four Approved Features
1. ⏳ Maritime dashboard map with vessel trails (Phase 4)
2. ⏳ Persistent MMSI watchlist (Phase 3)
3. ⏳ Observed port-call board (Phase 5)
4. ✅ AIS status-transition events (Phase 2)

## Phase 1: Shared Observations and Compatibility ✅ COMPLETE

### T001: Refactor Kystverket Client ✅ COMPLETE

**Objective**: Expose one parsed full-snapshot operation while preserving existing `get_vessels_in_radius` and `get_vessels_in_box` wrappers.

**Completed**:

1. **Enhanced VesselData model** (`client.py`):
   - Added `source_msgtime: str | None` - ISO-8601 string of when the AIS message was created at source
   - Added `observation_time: datetime` - Local reception time when the message was parsed
   - These fields separate concerns from `msgtime` (legacy) and `last_seen` (coordinator timestamp)

2. **New Snapshot Methods** (`kystverket_client.py`):
   - Added `async get_snapshot()` - Public method to fetch all available vessels unfiltered
   - Added `async _fetch_payload_full()` - Internal fetch without geographic bounds
   - Both methods include full retry logic and error handling matching `_fetch_payload`

3. **Updated Parsing** (`kystverket_client.py`):
   - Modified `_parse_row()` to populate `source_msgtime` (from source timestamp) and `observation_time` (current UTC)
   - Preserves all existing fields and backward compatibility

**Tests Created**:
- `tests/test_snapshot.py` - New test suite covering:
  - VesselData observation metadata isolation
  - VesselData default factory behavior
  - KystverketClient.get_snapshot() method existence
  - Snapshot return type validation
  - Source/observation/last-seen time separation

**Backward Compatibility**: ✅
- All existing `get_vessels_in_radius` and `get_vessels_in_box` calls unchanged
- New fields use sensible defaults
- Legacy `msgtime` field preserved
- No breaking changes to coordinator or entity contracts

### T002: Update Coordinator for Snapshot Partitioning ✅ COMPLETE

**Objective**: Integrate snapshot method into coordinator with geo-filtering, fallback strategy, and zero user-facing changes.

**Completed**:

1. **Enhanced _fetch_vessels()** (`coordinator.py`):
   - Detects Kystverket client via `isinstance` check
   - Calls `get_snapshot()` if available
   - Partitions results using `geo_filter.partition()`
   - Falls back to existing area queries if snapshot fails
   - Debug logging for call tracking

2. **Geo-filter Integration**:
   - Seamlessly partitions unfiltered snapshot into area bounds
   - No changes to existing area filter logic
   - Maintains exact same vessel counts as legacy area queries

3. **Backward Compatibility**: ✅
   - Other clients (AISHub, VesselFinder) bypass snapshot entirely
   - Fallback catches ALL exceptions and retries with area queries
   - No breaking changes to entity resolvers or downstream code

**Tests Created**:
- `tests/test_coordinator_snapshot.py` - Integration tests covering:
  - Snapshot used when available
  - Fallback to area queries on snapshot failure
  - Correct vessel counts with/without area filters
  - No extra API calls made

### T003: Extend Tests for Snapshot Integration ✅ COMPLETE

**Objective**: Comprehensive validation of one-fetch-per-poll optimization, edge cases, and backward compatibility.

**Completed**:

1. **7 New Integration Tests** (`test_phase_1_extended.py`):
   - **test_coordinator_one_fetch_per_poll_with_snapshot**: Validates 3 polls = 3 snapshot calls (optimization goal)
   - **test_coordinator_handles_old_source_timestamps**: 1-hour-old timestamps handled gracefully
   - **test_coordinator_handles_missing_source_timestamps**: None source_msgtime doesn't break system
   - **test_coordinator_handles_future_timestamps**: Clock skew/malformed data robustness
   - **test_coordinator_area_counts_unchanged**: Snapshot filtering matches legacy area query counts
   - **test_vessel_observation_time_set_correctly**: Observation metadata flows through coordinator
   - Plus 2 Phase 1.2 tests (fallback, no area filter)

2. **Test Coverage Matrix**:
   - ✅ One-fetch-per-poll verified
   - ✅ Timestamp handling (old/missing/future)
   - ✅ Backward compatibility (area counts)
   - ✅ Metadata flow (observation times)
   - ✅ Edge cases (fallback, no filter)

3. **Quality Metrics**:
   - All tests isolated with proper mocking
   - Fast execution (<1 second total)
   - Clear docstrings and failure messages
   - No external dependencies
   - CI/CD ready

**Documentation Created**:
- `.github/phase-1.1-implementation.md` - Technical details of snapshot foundation
- `.github/phase-1.2-implementation.md` - Coordinator integration and optimization
- `.github/phase-1.3-implementation.md` - Test coverage and validation

---

## Phase 1 Summary

**Foundation Status**: ✅ COMPLETE AND FULLY TESTED

**What Phase 1 Achieved**:
- ✅ One-fetch-per-poll optimization: 3+ API calls reduced to 1 per poll cycle
- ✅ Observation metadata separation: source_msgtime (AIS created) vs observation_time (parsed locally)
- ✅ Snapshot-based architecture: All future phases share single fetch with different filters
- ✅ Backward compatibility: Area queries work identically, other clients unchanged
- ✅ Comprehensive testing: Edge cases, timestamps, fallback all validated

**Phase 1 Benefits**:
- Phase 2 (Status Events): Uses timestamp separation to detect genuine transitions
- Phase 3 (Watchlist): Reuses same snapshot, applies different filter/view
- Phase 4 (Maritime Map): Efficient real-time updates via WebSocket
- Phase 5 (Port Calls): Hysteresis confirmation and entry/exit detection

**Phase 1 handoff**: Complete; Phase 2 status-transition work is now implemented.

---

## Phase 2: Status-Transition Automations

### T004-T006: Vessel Events and Storage
**Status**: ✅ COMPLETE
**Prerequisites**: Phase 1 complete

**Implemented**:
- `vessel_events.py` tracks per-entry status baselines, rejects duplicate and
  out-of-order source messages, and re-baselines after unknown status, stale
  observations, gaps, or implausible future timestamps.
- Status-transition detection runs on merged feed observations before vessel
  type and anchored/moored display filters, without changing area counts or
  existing entered/exited events.
- `storage.py` uses versioned Home Assistant storage with per-entry keys,
  debounced saves, startup restore, unload flush, and config-entry deletion
  cleanup.
- Baselines expire after the configured stale timeout and are capped at 2,000
  per entry; eviction is logged explicitly.
- Event `marinetraffic_vessel_status_changed` includes entry, vessel, old/new
  status, source/observation timestamps, source, and position.

**Tests and validation**:
- `tests/test_vessel_events.py`: status transitions, duplicates, ordering,
  missing/unknown/stale/future timestamps, gaps, restart continuity, bounds,
  and coordinator event behavior.
- `tests/test_storage.py`: versioned restore, malformed state, debounced
  writes, flush, entry isolation/removal, and surfaced storage failures.
- Targeted Phase 1/2 tests, including coordinator, integration, snapshot,
  event, and storage coverage: **92 passed**.

---

## Phase 3: Persistent Vessel Watchlist

### T007-T010: Watchlist Configuration and State
**Status**: ⏳ Pending  
**Prerequisites**: T001-T003 (Complete)

Tasks:
- [ ] T007: Add watchlist options in `config_flow.py` with MMSI validation
- [ ] T008: Add separate watchlist state and resolver in `coordinator.py`
- [ ] T009: Add aggregate watchlist sensor with freshness tracking
- [ ] T010: Extend tests for outside-area continuity and filter independence

---

## Phase 4: Maritime Map and Trails

### T011-T015: WebSocket API and Frontend Card
**Status**: ⏳ Pending  
**Prerequisites**: T005 (Complete), T010 (Pending)

**Map Data and Frontending**:

Tasks:
- [ ] T011: Add `websocket_api.py` with authenticated entry resolution, paginated snapshots, live invalidations
- [ ] T012: Add WebSocket API tests for authentication, entry isolation, pagination
- [ ] T013: Add frontend card registration and asset packaging (Leaflet)
- [ ] T014: Implement card UI (markers, trails, heading, details, fit/reset, mobile)
- [ ] T015: Add frontend integration tests

**Design Notes**:
- Map library: Leaflet (provisionally, pending license/asset confirmation)
- Custom element for vessel display
- Pinned, locally packaged assets (no CDN)
- Max 500 markers per response with pagination
- Up to 10 selected trails at 20 points each
- Coalesced live updates (≤ 1 per second)
- Existing built-in map YAML unchanged

---

## Phase 5: Observed Port-Call Board

### T016-T021: Port Configuration and Board Sensors
**Status**: ⏳ Pending  
**Prerequisites**: T006 (Complete), T010 (Pending)

Tasks:
- [ ] T016: Add port configuration in `config_flow.py` (up to 10 ports)
- [ ] T017: Add `port_calls.py` with hysteresis confirmation logic
- [ ] T018: Add comprehensive port-call tests
- [ ] T019: Add port-scoped board sensors (present, arrivals, departures)
- [ ] T020: Add port overlays and board UI to card
- [ ] T021: Add board display tests

**Port Call Logic**:
- Circular geofences with 100 m hysteresis
- Confirm with two fresh distinct observations beyond boundary
- Emit events only on confirmed crossings
- Track recent calls (7 days, ≤100 per port)
- Retain vessel baselines (≤1000 per port)

---

## Phase 6: Documentation and Release

### T022: Documentation Updates
**Status**: ⏳ Pending  
**Prerequisites**: T021 (Pending)

Updates needed:
- [ ] README.md - Feature overview
- [ ] docs/usage.md - User guide
- [ ] docs/configuration.md - Map, watchlist, port setup
- [ ] docs/architecture.md - Design details
- [ ] docs/troubleshooting.md - Common issues
- [ ] docs/development.md - Dev setup for map work

---

## Key Design Principles

### Observation Metadata
- **source_msgtime**: When AIS message was created (ISO-8601 string, may be None/unparseable)
- **observation_time**: Local reception time (datetime, always set at parse time)
- **last_seen**: Coordinator timestamp (preserved, updated on merge)
- **msgtime**: Legacy field, same as source_msgtime for compatibility

### One Snapshot Per Poll
- Kystverket client fetches full snapshot once
- Coordinator partitions for area, watchlist, ports
- All views derive from same fetch (no extra HTTP calls)

### Opt-In Features
- Existing installations work unchanged
- Watchlist, map card, port board are all optional
- Feature gates prevent breakage if frontend APIs unavailable

### State Isolation
- Entry-scoped WebSocket commands
- Separate watchlist and port storage per entry
- No cross-entry data leakage
- Clean unload/reload handling

### Bounded State
- Max 100 MMSIs in watchlist
- Max 10 named ports
- Max 500 markers per map response (paginated)
- Max 100 port-call records per port
- Max 2000 status baselines per entry

---

## Testing Strategy

### Unit Tests
- VesselData model validation
- Snapshot parsing with old/missing/future timestamps
- WebSocket command authentication and entry isolation
- Port hysteresis state machine
- Status baseline persistence and deduplication

### Integration Tests
- One fetch per poll cycle
- Watchlist vessel appearing/disappearing without area change
- Port arrivals with boundary hysteresis
- Status event emission (no duplicates on restart)
- Entry deletion cleanup
- Frontend card reconnect/reload

### Frontend Tests
- Fresh install with asset packaging
- Two-entry setup
- Card reconnect after close
- Mobile/keyboard interaction
- Missing tiles graceful handling
- HA frontend compatibility (lowest + current supported)

---

## Dependency Notes

### Python
- Python 3.12+
- Existing: aiohttp, voluptuous
- No new Python dependencies required

### Frontend
- Leaflet (open-source, OSM)
- Custom element (no framework)
- Local packaging (no CDN)
- License review: ✅ Required before T013

### Home Assistant
- Minimum version: 2025.1.0 (unchanged)
- WebSocket API available (required for map)
- Config entries and coordinator (existing patterns)
- Storage system (versioned, per-entry)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Leaflet license/asset packaging | Confirm before T013; fall back if needed |
| Map card frontend breakage | Feature-gate optional registration; test HA versions |
| Watchlist entity duplication | Shared resolver, preserve identity across area transitions |
| Port call false positives | Hysteresis band, dual-observation confirmation, gap handling |
| State explosion | Bounded maps (100 MMSIs, 2000 baselines, 100 calls/port) |
| Outage recovery | Gap detection, baseline reset, no fabricated transitions |

---

## Definition of Done

- [ ] All code changes are syntax-valid and type-checked
- [ ] Existing tests pass (no regressions)
- [ ] New tests cover happy path, edge cases, error handling
- [ ] Code follows project conventions (Python style, type hints)
- [ ] Documentation updated with examples and limitations
- [ ] Feature works end-to-end from clean install
- [ ] Frontend assets packaged and verified
- [ ] No credentials in events, logs, or diagnostics
- [ ] Bounded state validated (no infinite growth)
- [ ] Entry isolation verified (multi-entry scenario)

---

## File Manifest

### New Files
- `custom_components/marinetraffic_tracker/vessel_events.py` (Phase 2)
- `custom_components/marinetraffic_tracker/storage.py` (Phase 2)
- `custom_components/marinetraffic_tracker/port_calls.py` (Phase 5)
- `custom_components/marinetraffic_tracker/websocket_api.py` (Phase 4)
- `custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js` (Phase 4)
- `custom_components/marinetraffic_tracker/frontend/__init__.py` (Phase 4)
- `tests/test_snapshot.py` (Phase 1) ✅
- `tests/test_vessel_events.py` (Phase 2)
- `tests/test_storage.py` (Phase 2)
- `tests/test_port_calls.py` (Phase 5)
- `tests/test_websocket_api.py` (Phase 4)
- `tests/frontend/...` (Phase 4)

### Modified Files
- `custom_components/marinetraffic_tracker/client.py` ✅
- `custom_components/marinetraffic_tracker/kystverket_client.py` ✅
- `custom_components/marinetraffic_tracker/coordinator.py` (Phase 1.2)
- `custom_components/marinetraffic_tracker/config_flow.py` (Phase 3, 5)
- `custom_components/marinetraffic_tracker/const.py` (Throughout)
- `custom_components/marinetraffic_tracker/strings.json` (Phase 3, 5)
- `tests/test_kystverket_client.py` (Phase 1.3)
- `tests/test_coordinator.py` (Phase 1.3)

### Documentation
- `docs/architecture.md` (Phase 6)
- `docs/usage.md` (Phase 6)
- `docs/configuration.md` (Phase 6)
- `docs/troubleshooting.md` (Phase 6)

---

## Commit History

### Commit 1: Phase 1.1 - Shared Snapshot Foundation ✅
**Date**: 2024-10-30

- Add observation metadata to VesselData model (source_msgtime, observation_time)
- Add KystverketClient.get_snapshot() method for full unfiltered fetch
- Add _fetch_payload_full() with retry logic
- Update _parse_row() to populate observation metadata
- Add test_snapshot.py with coverage for new functionality
- Maintain full backward compatibility

**Tested Components**:
- VesselData model validation
- Snapshot method presence and interface
- Parsing with metadata population

**Next**: Phase 1.2 (Coordinator refactoring)
