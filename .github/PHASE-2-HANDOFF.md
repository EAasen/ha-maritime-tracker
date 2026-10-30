# Phase 2: Status-Transition Automations - Implementation Handoff

**Date**: 2024-10-30  
**Phase 1 Status**: ✅ **COMPLETE AND FULLY COMMITTED**  
**Phase 2 Status**: 🚀 **Ready to start**  

## Executive Summary

Phase 1 (Shared Observations and Compatibility) is complete with all three tasks implemented, tested, and committed:

- ✅ **T001**: Kystverket snapshot capability with observation metadata
- ✅ **T002**: Coordinator integration with snapshot-based partitioning
- ✅ **T003**: Extended test coverage (7 integration tests)

**Total commits in Phase 1**: 3
- [b7c9b26](https://github.com/EAasen/ha-maritime-tracker/commit/b7c9b26) - T001: Shared Snapshot Foundation
- [ac4c309](https://github.com/EAasen/ha-maritime-tracker/commit/ac4c309) - T002: Coordinator Snapshot Integration  
- [3ff1027](https://github.com/EAasen/ha-maritime-tracker/commit/3ff1027) - T003: Extended Test Coverage

### What Was Accomplished

**Foundation Layer Established**:
- ✅ One-fetch-per-poll optimization: 3+ API calls reduced to 1
- ✅ Observation metadata separation: source_msgtime vs observation_time
- ✅ Snapshot-based architecture: All future phases share single fetch
- ✅ Backward compatibility: Legacy area queries work identically
- ✅ Comprehensive testing: 7 new integration tests validating all scenarios

**Key Metrics**:
- Lines of implementation code: ~240
- Lines of test code: ~750
- Test count: 7 new integration tests (+ 3 extended assertions)
- All tests passing ✅
- All code syntax validated ✅
- All documentation complete ✅

## Phase 1 Architecture Highlights

### Snapshot-Based Fetching

**Before Phase 1**:
```
Coordinator._fetch_vessels()
  ├─ Area filter 1 → API call
  ├─ Area filter 2 → API call
  └─ (Future watchlist) → Additional API calls
Total: 3+ API calls per poll
```

**After Phase 1**:
```
Coordinator._fetch_vessels()
  └─ get_snapshot() → 1 API call
       ├─ Partition by area filter 1
       ├─ Partition by area filter 2
       └─ (Future watchlist) ← Reuses same snapshot
Total: 1 API call per poll (regardless of features enabled)
```

### Observation Metadata

Three distinct timestamp fields now available:

| Field | Set By | Purpose |
|-------|--------|---------|
| `source_msgtime` | AIS source | When vessel created the message |
| `observation_time` | Parser (local) | When we received/parsed it |
| `last_seen` | Coordinator | Entity-level last update time |

**Enables**: Phase 2 can detect genuine status changes from timestamp deltas

## Phase 2: Ready to Implement

### What Phase 2 Delivers

**User-Facing Feature**:
- Home Assistant automation events: `marinetraffic_vessel_status_changed`
- Triggers when vessel's AIS status changes (Underway → Moored, etc.)
- Robust against duplicates, stale data, and message gaps

**Internal Infrastructure**:
- Persistent baseline tracking (survives restarts)
- Reliable transition detection (no false positives)
- Bounded memory (2,000 baselines per entry max)
- Event decoupling (separate from coordinator complexity)

### Phase 2 Three-Module Design

#### 1. `vessel_events.py` - Decision Logic (~250 lines)

**Core class**: `VesselEventDecider`

Decides whether to fire a status transition event:
- First observation → establish baseline (no event)
- Same status → no event
- Status changed → fire event exactly once
- Handles: duplicates, out-of-order, stale, unknown status

**Key methods**:
```python
async def decide(self, 
                 baseline: VesselBaseline | None,
                 observation: VesselData) -> TransitionEvent | None
```

**Test count**: 15 unit tests
- First sighting behavior
- Same/changed status
- Timestamp edge cases (old, missing, future)
- Continuity validation
- Unknown status handling

#### 2. `storage.py` - Persistent Storage (~300 lines)

**Core class**: `VesselEventStorage`

Manages baseline persistence with versioning and debouncing:
- Load/restore baselines from disk
- Debounced writes (batch per poll cycle)
- LRU eviction at 2,000 baseline limit
- Per-entry isolation

**Key methods**:
```python
async def load(self, entry_id: str) -> dict[int, VesselBaseline]
async def save(self, entry_id: str, baselines: dict)
async def on_entry_deleted(self, entry_id: str)
```

**Test count**: 10 unit tests
- Persistence and restore
- Debouncing
- Corruption handling
- Entry isolation
- LRU eviction

#### 3. Coordinator Integration (~50 lines)

Wire event decider into existing `_fetch_vessels()`:
```python
for vessel in vessels:
    baseline = self.baselines.get(vessel.mmsi)
    event = await self.event_decider.decide(baseline, vessel)
    if event:
        self.hass.bus.async_fire("marinetraffic_vessel_status_changed", ...)
```

**Test count**: 8 integration tests
- Event firing on status change
- No events on same status
- Storage persistence through restart
- Two entries isolated
- Duplicate prevention

### Implementation Checklist

**Phase 2 Tasks**:
- [ ] T004: `vessel_events.py` with VesselEventDecider
- [ ] T005: `storage.py` with versioned baseline persistence
- [ ] T006: Tests and coordinator integration
- [ ] Documentation + commit

**Estimated Effort**:
- vessel_events.py: 4 hours (decision logic + docstrings)
- storage.py: 3 hours (persistence + versioning)
- Coordinator integration: 2 hours (wiring)
- Tests: 4 hours (33 tests)
- Total: ~13 hours

**Expected Test Count**: 33 new tests
- 15 for vessel_events.py
- 10 for storage.py
- 8 for coordinator integration

## Important Context for Phase 2 Implementation

### Critical Assumptions from Phase 1

1. **Phase 1 Output** is the input to Phase 2:
   - `VesselData` now has `source_msgtime` and `observation_time` fields
   - `Coordinator._fetch_vessels()` now calls `get_snapshot()` for Kystverket
   - Geo-filter partitions snapshot results
   - Tests validate observation metadata flows through

2. **Timestamp Separation** is crucial:
   - `source_msgtime` (from AIS) ≠ `observation_time` (local parse time)
   - Phase 2 uses this to detect timestamp validity and continuity
   - See test examples in `test_phase_1_extended.py`

3. **One Fetch Per Poll** is guaranteed:
   - Coordinator makes exactly 1 snapshot call per poll cycle
   - All future views (area, watchlist, ports) partition this single result
   - No extra API calls even with all features enabled

### Key Design Principles for Phase 2

1. **Isolation**: VesselEventDecider is pure logic, testable without mocking
2. **Persistence**: Baselines survive restarts via Home Assistant versioned storage
3. **Boundedness**: Memory-bounded with LRU eviction at 2,000 per entry
4. **Robustness**: Handles all timestamp edge cases (old, missing, future)
5. **Backward Compatibility**: Events are additive, no breaking changes

### Test Patterns to Follow

See `test_phase_1_extended.py` for patterns Phase 2 tests should follow:

```python
# Async test support
@pytest.mark.asyncio
async def test_example():
    ...

# Mocking pattern
with patch.object(coordinator, "event_decider", ...) as mock:
    ...
    assert mock.call_count == 1

# Timestamp handling
vessel = VesselData(
    source_msgtime="2024-10-30T12:00:00Z",
    observation_time=datetime.now(UTC),
    ...
)
```

## Files Structure After Phase 2

```
custom_components/marinetraffic_tracker/
  client.py                  (unchanged after Phase 1)
  kystverket_client.py       (unchanged after Phase 1)
  coordinator.py             (+ ~50 lines for Phase 2)
  vessel_events.py           (NEW ~250 lines)
  storage.py                 (NEW ~300 lines)
  const.py                   (+ event name constants)
  __init__.py                (+ storage lifecycle)
  
tests/
  test_snapshot.py           (from Phase 1)
  test_coordinator_snapshot.py (from Phase 1)
  test_phase_1_extended.py   (from Phase 1)
  test_vessel_events.py      (NEW ~400 lines, 15 tests)
  test_storage.py            (NEW ~350 lines, 10 tests)
  test_integration.py        (+ ~150 lines, 8 tests)

.github/
  phase-1.1-implementation.md
  phase-1.2-implementation.md
  phase-1.3-implementation.md
  phase-2-plan.md            (NEW - detailed design)
  maritime-map-progress.md   (updated with Phase 1 complete)
```

## Known Unknowns for Phase 2

1. **Stale Timeout Value**: What's the right timeout before continuity invalidates?
   - Current assumption: Use existing `TIMEOUT` constant from coordinator
   - May need adjustment based on testing

2. **LRU Eviction Trigger**: When exactly should we warn about eviction?
   - Current assumption: Every eviction triggers a warning log
   - May want to batch/deduplicate warnings

3. **Event Attribute Keys**: Exact field names for the event payload?
   - Current assumption: Follow pattern from feature plan
   - May need adjustment based on HA event standards

## Verification Checklist for Phase 2

Before marking Phase 2 complete:

- [ ] All 33 tests pass (15 + 10 + 8)
- [ ] No duplicate events per transition
- [ ] Baselines persist across restart
- [ ] Storage files created and cleaned up correctly
- [ ] Memory stays bounded (<2000 baselines per entry)
- [ ] All edge cases handled (old/missing/future/gap)
- [ ] All new code has docstrings
- [ ] Code follows existing style conventions
- [ ] Backward compatible (legacy events unchanged)
- [ ] Documentation complete
- [ ] All commits follow commit message format

## Next Phases Preview

After Phase 2 completes, roadmap continues:

**Phase 3: Persistent Vessel Watchlist**
- Add MMSI configuration options
- Reuse Phase 1 snapshot (no extra API calls)
- Use Phase 2 status events for watched vessel monitoring
- New tests: watchlist options, state, entities

**Phase 4: Maritime Dashboard Map**
- WebSocket API for bounded real-time updates
- Frontend card with Leaflet
- Vessel trails and selection
- New tests: WebSocket, frontend

**Phase 5: Port-Call Board**
- Port configuration management
- Port arrival/departure detection
- Board sensors with port status
- New tests: port logic, board display

**Phase 6: Documentation & Release**
- User guides and troubleshooting
- Final regression testing
- Release preparation

## Resources and References

### Phase 1 Documentation
- [.github/phase-1.1-implementation.md](.github/phase-1.1-implementation.md) - Snapshot foundation details
- [.github/phase-1.2-implementation.md](.github/phase-1.2-implementation.md) - Coordinator integration
- [.github/phase-1.3-implementation.md](.github/phase-1.3-implementation.md) - Test coverage validation
- [.github/maritime-map-progress.md](.github/maritime-map-progress.md) - Project progress tracker

### Feature Plan
- [docs/flightradar-feature-plan.md](docs/flightradar-feature-plan.md) - Complete specification
  - Section: "Phase 2: Status-transition automations"
  - Tasks: T004, T005, T006

### Phase 1 Code Examples
- [custom_components/marinetraffic_tracker/client.py](custom_components/marinetraffic_tracker/client.py) - VesselData with observation metadata
- [custom_components/marinetraffic_tracker/kystverket_client.py](custom_components/marinetraffic_tracker/kystverket_client.py) - get_snapshot() implementation
- [custom_components/marinetraffic_tracker/coordinator.py](custom_components/marinetraffic_tracker/coordinator.py) - snapshot-based _fetch_vessels()

### Test Examples
- [tests/test_phase_1_extended.py](tests/test_phase_1_extended.py) - Pattern examples for Phase 2 tests

## Commit History

Phase 1 commits (for reference):

```
3ff1027 Phase 1.3: Extended Test Coverage - Complete Foundation Layer
ac4c309 Phase 1.2: Coordinator Snapshot Integration
b7c9b26 Phase 1.1: Shared Snapshot Foundation for Maritime Map
```

**Expected Phase 2 commits**:
```
PENDING: Phase 2.1: Vessel Status Events & Decision Logic
PENDING: Phase 2.2: Storage & Persistence
PENDING: Phase 2.3: Coordinator Integration & Complete Test Suite
```

## Start Here

To begin Phase 2 implementation:

1. **Read** this handoff document completely
2. **Review** Phase 2 plan: [.github/phase-2-plan.md](.github/phase-2-plan.md)
3. **Study** Phase 1 code for patterns:
   - Observation metadata in `client.py`
   - Snapshot method in `kystverket_client.py`
   - Coordinator integration in `coordinator.py`
   - Test patterns in `test_phase_1_extended.py`
4. **Start** with `vessel_events.py` (decision logic)
5. **Follow** with `storage.py` (persistence)
6. **Integrate** into `coordinator.py`
7. **Test** with 33 comprehensive tests
8. **Commit** with full documentation

---

**Phase 1 is complete. Phase 2 is ready. Let's build status events! 🚀**
