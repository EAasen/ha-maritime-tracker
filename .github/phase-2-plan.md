# Phase 2: Status-Transition Automations - Implementation Plan

**Status**: 🚀 Ready to Start  
**Prerequisite**: Phase 1 ✅ COMPLETE  
**Target Completion**: Next session  

## Overview

Phase 2 implements reliable vessel status-transition detection with persistent baseline tracking. It's the foundation for detecting when vessels change operational state (underway, moored, anchored, etc.) without generating false positives from message gaps, stale data, or outages.

### What Phase 2 Enables

**For the User**:
- Home Assistant automation events when vessel AIS status changes
- Distinction between genuine transitions and temporary connectivity gaps
- Robust handling of message ordering and delivery issues

**For Future Phases**:
- Phase 3 (Watchlist) leverages status events for watched vessel monitoring
- Phase 4 (Maritime Map) uses status transitions for vessel lifecycle tracking
- Phase 5 (Port Calls) distinguishes arrivals/departures from status transitions

## Architecture Design

### Core Concept: Baseline-Transition Pattern

```
Timeline: [First Observation] → [Status-A period] → [Status-B] → [Transition Event]
          └─ No event       └──── No events      └─ Baseline  └─ Fired once
             (baseline)         (baseline matches)   changes
```

**Key Invariants**:
1. First observation = establish baseline (no event fired)
2. Same status = no event
3. Duplicate/out-of-order message = no event
4. Unknown status = baseline invalidated (next valid = new baseline)
5. Stale/gap interval = baseline invalidated (next valid = new baseline)
6. Status changed = fire event exactly once

### Data Model

**VesselBaseline** (stored in persistent storage):
```python
@dataclass
class VesselBaseline:
    mmsi: int
    status: str                     # Current AIS status (e.g., "Underway")
    source_msgtime: str | None      # When AIS message created
    observation_time: datetime      # When we received/parsed it
    entry_id: str                   # Config entry this baseline belongs to
    continuity_valid: bool          # False if gap/stale invalidated
    eviction_warning: bool          # True if space limit forced eviction
```

**Event Payload** (fired to Home Assistant):
```python
{
    "entry_id": "xyz",
    "mmsi": 123456789,
    "name": "VESSEL NAME",
    "old_status": "Underway",
    "new_status": "Moored",
    "source_msgtime": "2024-10-30T12:00:00Z",
    "observation_time": "2024-10-30T12:00:05Z",
    "source": "kystverket",
    "position": {"latitude": 59.0, "longitude": 10.0}
}
```

## Three Core Modules

### 1. `vessel_events.py` - Decision Logic

**Responsibility**: Determine whether to fire a transition event

**Key Class**: `VesselEventDecider`
```python
class VesselEventDecider:
    async def decide(self, 
                     baseline: VesselBaseline | None,
                     observation: VesselData) -> TransitionEvent | None:
        """
        Returns:
        - None: No event (first sighting, same status, or continuity broken)
        - TransitionEvent: Status changed, fire this event
        """
```

**Decision Tree**:
```
if no baseline exists:
    → Create baseline, return None
if observation status == baseline status:
    → Return None (no change)
if observation is stale/old/future (timestamp check):
    → Invalidate continuity, return None
if message out-of-order (check source_msgtime):
    → Return None
if continuity invalid from prior gap:
    → Re-baseline, return None
if status changed:
    → Fire event, update baseline, return TransitionEvent
else:
    → Return None
```

**Key Methods**:
- `_is_observation_valid()` - Timestamp sanity checks
- `_check_continuity()` - Detect gaps/stale intervals
- `_should_fire_transition()` - Compare old/new status
- `_update_baseline_and_fire_event()` - Atomic transition

**Test Coverage**:
- [ ] First observation → baseline, no event
- [ ] Same status → no event
- [ ] Status changed → event fired
- [ ] Duplicate message → no event
- [ ] Out-of-order message → no event
- [ ] Unknown status → baseline invalid
- [ ] Stale message (>timeout) → continuity invalid, no event
- [ ] Future timestamp (clock skew) → handled gracefully
- [ ] Gap period (no messages) → continuity invalid
- [ ] After gap, next message → baseline re-established

### 2. `storage.py` - Persistent Baseline Storage

**Responsibility**: Read/write baselines with versioning and debouncing

**Key Class**: `VesselEventStorage`
```python
class VesselEventStorage:
    async def load(self, entry_id: str) -> dict[int, VesselBaseline]:
        """Load persisted baselines for entry"""
    
    async def save(self, entry_id: str, baselines: dict[int, VesselBaseline]):
        """Debounced write of baselines"""
    
    async def on_entry_deleted(self, entry_id: str):
        """Clean up storage for deleted entry"""
```

**Storage Format** (Home Assistant versioned storage):
```json
{
  "version": 1,
  "data": {
    "123456789": {
      "mmsi": 123456789,
      "status": "Underway",
      "source_msgtime": "2024-10-30T12:00:00Z",
      "observation_time": "2024-10-30T12:00:05Z",
      "entry_id": "xyz",
      "continuity_valid": true
    }
  }
}
```

**Features**:
- Versioned format for future upgrades
- Per-entry isolation (no cross-entry data leakage)
- Debounced writes (batch changes, write once per poll cycle)
- Graceful load failure (corrupted data doesn't crash)
- Automatic cleanup on entry deletion

**Key Methods**:
- `_schedule_save()` - Debounce timer
- `_load_from_disk()` - Read with version check
- `_migrate_if_needed()` - Handle format changes
- `_evict_oldest_if_full()` - LRU when at 2,000 vessel limit

**Test Coverage**:
- [ ] Load and restore baselines
- [ ] Save and persist
- [ ] Debounce multiple writes
- [ ] Corrupt data gracefully handled
- [ ] Entry deleted → storage file removed
- [ ] Full storage → oldest evicted with warning
- [ ] Restart → baselines restored
- [ ] Two entries isolated

### 3. `coordinator.py` Integration - Hook Point

**Responsibility**: Call event decider after each snapshot fetch

**Integration Point** in `_fetch_vessels()`:
```python
async def _fetch_vessels(self, ...):
    # Existing snapshot fetch...
    vessels = await self._get_snapshot()
    
    # NEW: Process status transitions
    for vessel in vessels:
        baseline = self.baselines.get(vessel.mmsi)
        event = await self.event_decider.decide(baseline, vessel)
        if event:
            self.hass.bus.async_fire(
                "marinetraffic_vessel_status_changed",
                event.as_dict()
            )
            # Storage will save in background
```

**Coordinator Changes**:
- Add `self.event_decider: VesselEventDecider` instance
- Add `self.baselines: dict[int, VesselBaseline]` cache
- Add `self.storage: VesselEventStorage` instance
- Call event decider for each fetched vessel
- On unload: flush storage, cancel debounce timer
- On entry delete: cleanup storage files

## Implementation Sequence

### Step 1: vessel_events.py (4 hours)
- [x] Define VesselBaseline dataclass
- [x] Define TransitionEvent dataclass
- [x] Implement VesselEventDecider class
- [x] All decision logic and timestamp handling
- [x] Unit tests (10 tests)

### Step 2: storage.py (3 hours)
- [x] Define storage file path pattern
- [x] Implement VesselEventStorage class
- [x] Versioned read/write
- [x] Debounce timer logic
- [x] LRU eviction with warnings
- [x] Integration tests (8 tests)

### Step 3: coordinator.py Integration (2 hours)
- [x] Import new modules
- [x] Initialize event_decider and storage
- [x] Wire into _fetch_vessels()
- [x] Fire events to Home Assistant bus
- [x] Lifecycle: load on startup, save on unload
- [x] Entry deletion cleanup
- [x] Integration tests (5 tests)

### Step 4: const.py and __init__.py (1 hour)
- [x] Add EVENT_NAME constant
- [x] Add event attribute keys
- [x] Wire storage startup/shutdown in __init__.py

### Step 5: Tests (4 hours)
- [x] test_vessel_events.py (15 tests)
- [x] test_storage.py (10 tests)
- [x] Extend test_integration.py (8 tests)
- [x] Total: 33 new tests

## Test Coverage Matrix

| Scenario | Test | Status |
|----------|------|--------|
| First observation | test_first_observation_creates_baseline | ⏳ |
| Same status | test_same_status_no_event | ⏳ |
| Status changed | test_status_changed_fires_event | ⏳ |
| Duplicate message | test_duplicate_message_ignored | ⏳ |
| Out-of-order | test_out_of_order_message_ignored | ⏳ |
| Unknown status | test_unknown_status_invalidates | ⏳ |
| Stale message | test_stale_message_invalidates | ⏳ |
| Clock skew | test_future_timestamp_handled | ⏳ |
| Gap period | test_gap_invalidates_continuity | ⏳ |
| Restart | test_baselines_restored_from_storage | ⏳ |
| Storage full | test_lru_eviction_with_warning | ⏳ |
| Entry isolation | test_two_entries_isolated | ⏳ |
| Duplicate events | test_no_duplicate_events_per_transition | ⏳ |

**Total Test Count**: 33 new tests across 3 files

## Key Design Decisions

### 1. Why Persist Baselines?
- **Problem**: Without persistence, restart causes all vessels to re-baseline
- **Solution**: Store in Home Assistant's versioned storage
- **Benefit**: Ensures events don't fire on every restart

### 2. Why Debounce Storage Writes?
- **Problem**: Writing to disk after every vessel observation is too frequent
- **Solution**: Batch all changes from one poll cycle, write once
- **Benefit**: Reduces disk I/O from ~500 writes/poll to 1 write/poll

### 3. Why 2,000 Baseline Limit?
- **Problem**: Unbounded baselines could grow forever
- **Solution**: Cap at 2,000 per entry, LRU eviction
- **Benefit**: Memory bounded, predictable
- **Trade-off**: Rarely-seen vessel gets evicted, next sighting re-baselines

### 4. Why Separate Event Decider?
- **Problem**: Coordinator is already complex
- **Solution**: Isolated VesselEventDecider class with pure logic
- **Benefit**: Testable without mocking coordinator

## Backward Compatibility

✅ **All changes backward compatible**:
- No changes to existing entity IDs or names
- No changes to existing sensor attributes
- Events are additive (new bus event doesn't break existing automations)
- Storage is per-entry, isolated
- Fallback paths (non-Kystverket clients) unaffected

## Phase 2 Completion Gate

**All tests pass**:
- ✅ Zero duplicate events per transition
- ✅ First sighting generates no event
- ✅ Gap + first message after gap generates no event
- ✅ Out-of-order messages ignored
- ✅ Storage persists and restores correctly
- ✅ Entry isolation verified
- ✅ Legacy events unchanged

**Quality Metrics**:
- Target: 33 new tests (15 decider + 10 storage + 8 integration)
- Coverage: All decision paths
- Performance: Events fired within 1 poll cycle (<5s)
- Memory: Bounded at 2,000 baselines per entry

## Next Phase Preview

Once Phase 2 is complete:

**Phase 3** will:
- Add MMSI watchlist configuration
- Reuse Phase 1 snapshot (no extra API calls)
- Use Phase 2 status events for changed/watching detection

**Phase 4** will:
- Use Phase 2 status for lifecycle tracking
- Show status changes on map with transitions

**Phase 5** will:
- Use Phase 2 for false transition rejection
- Port arrivals/departures distinct from status changes

## Files to Create/Modify

### New Files
- `custom_components/marinetraffic_tracker/vessel_events.py` (~250 lines)
- `custom_components/marinetraffic_tracker/storage.py` (~300 lines)
- `tests/test_vessel_events.py` (~400 lines)
- `tests/test_storage.py` (~350 lines)

### Modified Files
- `custom_components/marinetraffic_tracker/coordinator.py` (~50 lines)
- `custom_components/marinetraffic_tracker/const.py` (~20 lines)
- `custom_components/marinetraffic_tracker/__init__.py` (~30 lines)
- `tests/test_integration.py` (+~150 lines)

### Total New Code
- ~1,700 lines of implementation
- ~900 lines of tests (33 tests)
- Total: ~2,600 lines

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Storage file corruption | Try/except on load, graceful degradation to empty baselines |
| Memory leak (unbounded baselines) | LRU eviction at 2,000 per entry with warning |
| Event loop dead code | Comprehensive tests for all paths |
| Timestamp-based bugs | Extensive edge case tests (old, missing, future times) |
| Restart data loss | Versioned storage with explicit unload flush |
| Cross-entry data leakage | Per-entry storage files, explicit entry_id isolation |

## Success Criteria

✅ Phase 2 is complete when:
- [ ] All 33 tests pass
- [ ] No duplicate events per transition
- [ ] Baselines persist across restart
- [ ] Storage files created and cleaned up correctly
- [ ] Zero memory leaks (bounded storage)
- [ ] All edge cases handled (out-of-order, stale, unknown)
- [ ] All new code has docstrings
- [ ] Code follows existing style conventions
- [ ] Backward compatible (legacy events unchanged)

---

## Implementation Begin

Ready to start. The foundation from Phase 1 (observation metadata, snapshot architecture, timestamp separation) is solid. Phase 2 leverages all of it to add reliability.

Next: Create `vessel_events.py` → `storage.py` → Coordinator integration → Tests → Commit
