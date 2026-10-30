# Phase 1 & 2 Test Execution & Verification Guide

**Status**: Phase 1 & 2 Implementation Complete ✅  
**Test Infrastructure**: Fully Functional  
**Coverage Target**: 80%+ (enforced in CI)  
**Last Verified**: 2026-10-30

---

## Quick Start

### Run Phase 1 Tests
```bash
python -m pytest tests/test_snapshot.py tests/test_kystverket_client.py tests/test_coordinator_snapshot.py tests/test_phase_1_extended.py -v
```

### Run Phase 2 Tests
```bash
python -m pytest tests/test_vessel_events.py tests/test_storage.py -v
```

### Run Both Phase 1 & 2
```bash
python -m pytest tests/test_snapshot.py tests/test_kystverket_client.py tests/test_coordinator_snapshot.py tests/test_phase_1_extended.py tests/test_vessel_events.py tests/test_storage.py -v
```

### Run Linting & Type Checking
```bash
ruff check custom_components/ tests/
ruff format --check custom_components/ tests/
mypy custom_components/ --ignore-missing-imports
```

### Verify Integration Tests
```bash
python -m pytest tests/test_integration.py::test_status_baseline_survives_entry_unload_and_reload -v
```

---

## Phase 1: Shared Observations and Compatibility

Phase 1 establishes the foundation: a single Kystverket snapshot per poll that
feeds all enabled features (area, watchlist, ports) without changing legacy
behavior or duplicating network requests.

### Purpose

- ✅ Normalize source-message timestamps vs. local observation timestamps
- ✅ Preserve existing area query behavior (radius and bounding box)
- ✅ Support fallback clients (backward compatibility)
- ✅ Handle missing, old, and future timestamps gracefully
- ✅ Maintain existing client authentication and retry logic

### Test Files

| File | Purpose |
|------|---------|
| `tests/test_snapshot.py` | Snapshot parsing and normalization |
| `tests/test_kystverket_client.py` | BarentsWatch client behavior |
| `tests/test_coordinator_snapshot.py` | Coordinator snapshot handling |
| `tests/test_phase_1_extended.py` | Edge cases and fallback paths |

### Key Test Scenarios

#### Timestamp Handling

```bash
# Test that source-message time, local observation time, and legacy timestamps
# remain distinct and correctly preserved
python -m pytest tests/test_snapshot.py::TestTimestampNormalization -v
```

**Expected behavior:**
- Source timestamp from AIS message is preserved as-is
- Local observation time (poll time) recorded separately
- Legacy `last_seen` compatibility field maintained
- Missing source time uses local observation time with uncertainty flag
- Implausible future timestamps rejected without breaking feed

#### Area Query Compatibility

```bash
# Test that radius and bounding-box queries remain functional after Phase 1 changes
python -m pytest tests/test_coordinator_snapshot.py::TestAreaQueries -v
```

**Expected behavior:**
- Radius mode filters vessels within configured circle
- Bounding box mode filters vessels within rectangle
- Area counts match original behavior (no regression)
- Filtering happens after normalization, before display

#### Snapshot Reuse Across Features

```bash
# Test that one snapshot feeds area, watchlist, and port logic without
# duplication or data corruption
python -m pytest tests/test_phase_1_extended.py::TestSnapshotReuse -v
```

**Expected behavior:**
- Coordinator fetches one snapshot per poll cycle
- Snapshot used for area filtering
- Same snapshot used for watchlist updates
- Same snapshot available for port geofence checks (Phase 5)
- No additional per-MMSI requests

#### Client Fallback Paths

```bash
# Test backward compatibility with clients that may not have new snapshot methods
python -m pytest tests/test_phase_1_extended.py::TestClientFallback -v
```

**Expected behavior:**
- Integration works if client lacks `get_full_snapshot()` method
- Falls back to legacy `get_vessels_in_radius()` / `get_vessels_in_box()`
- Extra clients (AISHub, VesselFinder) treated as concurrent sources
- Clients are deduplicated by MMSI on merge

### Phase 1 Acceptance Criteria

- [ ] All Phase 1 tests pass with exit code `0`
- [ ] No test is skipped without documented reason
- [ ] Snapshot parsing correctly handles:
  - Valid AIS source timestamps (ISO-8601)
  - Missing source timestamps (uses local observation time)
  - Implausible future timestamps (logged, observation used)
  - Out-of-order messages (no silent drops)
- [ ] Area filtering (radius/box) produces same results as before
- [ ] One snapshot per poll confirmed (no duplicate requests)
- [ ] Fallback paths confirmed functional
- [ ] Code coverage ≥ 80% for Phase 1 modules

---

## Phase 2: Status-Transition Automations

Phase 2 adds reliable AIS status-change event emission with hysteresis logic
to prevent false transitions from duplicates, out-of-order messages, or stale
observations.

### Purpose

- ✅ Emit `marinetraffic_vessel_status_changed` event exactly once per valid transition
- ✅ Ignore duplicates and out-of-order observations
- ✅ Handle unknown/unparseable statuses safely
- ✅ Break continuity on stale gaps (no synthetic transitions on resume)
- ✅ Persist baselines across restart
- ✅ Preserve existing area counts and entered/exited events

### Test Files

| File | Purpose |
|------|---------|
| `tests/test_vessel_events.py` | Status tracking and event emission |
| `tests/test_storage.py` | Baseline persistence and restore |
| `tests/test_integration.py` | End-to-end setup/teardown/reload |

### Key Test Scenarios

#### First Observation (Baseline Establishment)

```bash
# First valid observation should establish a baseline WITHOUT firing an event
python -m pytest tests/test_vessel_events.py::TestFirstObservation -v
```

**Expected behavior:**
```
Observation 1 (Vessel MMSI 123456789 status=Underway): 
  → Establishes baseline (status = "Underway")
  → NO event emitted
  → Next change will trigger event
```

**Test:**
```python
@pytest.mark.asyncio
async def test_first_valid_observation_no_event():
    """First observation should baseline without emitting event."""
    tracker = VesselEventTracker("entry1", stale_timeout=3600)
    vessel = VesselData(mmsi="123456789", status="Underway using engine")
    
    events = await tracker.check_status_transition(vessel)
    assert len(events) == 0  # No event on first observation
    assert tracker.has_baseline("123456789")
```

#### Valid Status Change (Event Emission)

```bash
# Second valid observation with different status should emit event
python -m pytest tests/test_vessel_events.py::TestValidTransition -v
```

**Expected behavior:**
```
Baseline: status = "Underway using engine"

Observation 2 (Vessel MMSI 123456789 status=At anchor): 
  → Status changed (Underway → At Anchor)
  → Event emitted: marinetraffic_vessel_status_changed
  → Event payload includes:
      - entry_id, mmsi, name, vessel_type
      - old_status, new_status
      - source_timestamp, observation_timestamp
      - position (lat, lon)
      - data_source
  → Baseline updated to new status
```

**Test:**
```python
@pytest.mark.asyncio
async def test_valid_status_change_emits_event():
    """Valid status change should emit exactly one event."""
    tracker = VesselEventTracker("entry1", stale_timeout=3600)
    
    # Establish baseline
    vessel1 = VesselData(mmsi="123456789", status="Underway using engine", last_seen=now)
    await tracker.check_status_transition(vessel1)
    
    # Change status
    vessel2 = VesselData(mmsi="123456789", status="At anchor", last_seen=now + timedelta(minutes=5))
    events = await tracker.check_status_transition(vessel2)
    
    assert len(events) == 1  # Exactly one event
    event = events[0]
    assert event["old_status"] == "Underway using engine"
    assert event["new_status"] == "At anchor"
    assert event["mmsi"] == "123456789"
```

#### Duplicate Observation (No Event)

```bash
# Repeated identical message should NOT emit event
python -m pytest tests/test_vessel_events.py::TestDuplicateHandling -v
```

**Expected behavior:**
```
Baseline: status = "Underway", observation_time = 2026-10-30 15:00:00

Observation A (same time): 
  → Source timestamp identical (2026-10-30 15:00:00)
  → Status identical (Underway)
  → Same message considered duplicate
  → NO event emitted

Observation B (same time, different observation time):
  → Source timestamp identical but local observation time differs
  → Still considered duplicate on source time
  → NO event emitted
```

**Test:**
```python
@pytest.mark.asyncio
async def test_duplicate_observation_no_event():
    """Duplicate messages (same source time) should not emit event."""
    tracker = VesselEventTracker("entry1", stale_timeout=3600)
    source_time = datetime(2026, 10, 30, 15, 0, 0, tzinfo=UTC)
    
    # First observation
    vessel1 = VesselData(mmsi="123456789", status="Underway", 
                        source_time=source_time, last_seen=now)
    events1 = await tracker.check_status_transition(vessel1)
    assert len(events1) == 0  # Baseline
    
    # Duplicate (same source time)
    vessel2 = VesselData(mmsi="123456789", status="Underway", 
                        source_time=source_time, last_seen=now + timedelta(seconds=30))
    events2 = await tracker.check_status_transition(vessel2)
    assert len(events2) == 0  # Still no event
```

#### Out-of-Order Observation (No Event)

```bash
# Message with older source timestamp should not trigger transition
python -m pytest tests/test_vessel_events.py::TestOutOfOrderHandling -v
```

**Expected behavior:**
```
Baseline: status = "Underway" (source_time = 15:05:00)

Observation with source_time = 15:03:00 (earlier):
  → Out-of-order (earlier than baseline timestamp)
  → Ignored for transition detection
  → NO event emitted
  → Baseline remains "Underway" at 15:05:00
```

#### Unknown Status (Break Continuity)

```bash
# Unknown status code should not emit event; baseline reset on next valid observation
python -m pytest tests/test_vessel_events.py::TestUnknownStatus -v
```

**Expected behavior:**
```
Baseline: status = "Underway"

Observation: status = "99" (unknown/unparseable):
  → Status is unknown (not in AIS standard codes)
  → Not a valid transition (no baseline established for unknown)
  → NO event emitted

Next Observation: status = "At anchor" (valid):
  → Previous baseline broken (unknown state invalidated it)
  → New valid observation re-baselines without event
  → Baseline now = "At anchor"
```

#### Stale Observation (Break Continuity)

```bash
# Observation older than stale_timeout should break continuity
python -m pytest tests/test_vessel_events.py::TestStaleGapHandling -v
```

**Expected behavior:**
```
Baseline: status = "Underway" (observation_time = 15:00:00)
Stale timeout: 3600 seconds (1 hour)

Observation at 15:55:00 (within timeout):
  → Fresh observation
  → Normal transition logic applies

Coverage gap (no observations for 70 minutes):

Observation at 17:05:00 (after gap):
  → Last baseline from 15:00:00 (now 2+ hours stale)
  → Status change occurred during gap (unknown)
  → Can't confirm causality
  → Break continuity: discard old baseline
  → New observation re-baselines without event
  → Baseline now = "At anchor"
```

**Test:**
```python
@pytest.mark.asyncio
async def test_stale_gap_breaks_continuity():
    """Stale gap should discard baseline and not fabricate transition."""
    tracker = VesselEventTracker("entry1", stale_timeout=3600)  # 1 hour
    
    # Baseline at 15:00
    vessel1 = VesselData(mmsi="123456789", status="Underway", 
                        last_seen=datetime(2026, 10, 30, 15, 0, 0, tzinfo=UTC))
    events1 = await tracker.check_status_transition(vessel1)
    assert len(events1) == 0
    
    # Gap of 2 hours (now 17:05, vessel stale since 16:00)
    vessel2 = VesselData(mmsi="123456789", status="At anchor", 
                        last_seen=datetime(2026, 10, 30, 17, 5, 0, tzinfo=UTC))
    events2 = await tracker.check_status_transition(vessel2)
    
    # Should NOT emit event (gap breaks continuity)
    assert len(events2) == 0
    # Baseline should be re-established
    assert tracker.get_baseline("123456789").status == "At anchor"
```

#### Missing Source Timestamp

```bash
# Message without source time should use local observation time
python -m pytest tests/test_vessel_events.py::TestMissingSourceTime -v
```

**Expected behavior:**
- Source timestamp missing → use local observation time instead
- Message marked as "uncertain time"
- Transition logic proceeds as normal

### Persistence Tests

#### Baseline Restore on Startup

```bash
# Persisted baseline should restore on coordinator startup
python -m pytest tests/test_storage.py::TestBaselineRestore -v
```

**Expected behavior:**
```
Session 1:
  - Vessel seen with status "Underway"
  - Baseline stored: {"mmsi": "123456789", "status": "Underway", ...}
  - Home Assistant stopped

Session 2 (restart):
  - Coordinator loaded
  - Storage restored baseline for all known MMSIs
  - Status "Underway" re-established without event
  - Next status change will emit event
```

#### Baseline Expire on Stale Timeout

```bash
# Baselines should expire if age > stale_timeout
python -m pytest tests/test_storage.py::TestBaselineExpiry -v
```

**Expected behavior:**
```
Baseline age: 2 hours
Stale timeout: 1 hour

On restore:
  - Age (2 hours) > timeout (1 hour)
  - Baseline is too stale
  - Baseline discarded
  - Next observation re-baselines without event
```

#### Versioning and Forward Compatibility

```bash
# Storage format versioning should handle schema changes
python -m pytest tests/test_storage.py::TestStorageVersioning -v
```

**Expected behavior:**
- Current version: `baseline_version = 1`
- Old/unknown versions: logged as warning, not loaded
- New observations re-baseline safely

#### Entry Isolation

```bash
# Two config entries should have separate baseline storage
python -m pytest tests/test_storage.py::TestEntryIsolation -v
```

**Expected behavior:**
```
Entry 1: Baseline for MMSI 123456789 = "Underway"
Entry 2: Baseline for MMSI 123456789 = "At anchor"

Restart:
  - Entry 1 restores: "Underway"
  - Entry 2 restores: "At anchor"
  - No data leakage or crossover
```

#### Storage Failure Handling

```bash
# Corrupted or missing storage should not crash coordinator
python -m pytest tests/test_storage.py::TestStorageFailures -v
```

**Expected behavior:**
- Corrupted storage file → logged error, coordinator continues
- Missing file → treated as no stored baselines
- Save failure → logged warning, next cycle retries
- No silent data loss

### Integration Test: Setup → Reload → Shutdown

```bash
python -m pytest tests/test_integration.py::test_status_baseline_survives_entry_unload_and_reload -v
```

**Test scenario:**

```
1. Setup entry (HA starts)
   - Coordinator created
   - First observation: Vessel 123456789 status = "Underway"
   - Baseline stored
   
2. First reload (HA options changed)
   - Entry unloaded (coordinator shutdown, storage flushed)
   - Entry reloaded
   - Baselines restored from storage
   - Status "Underway" re-established (no event)
   
3. Observation with status change
   - Vessel status changes to "At anchor"
   - Event emitted successfully
   
4. Shutdown (HA stopped)
   - Storage flushed again
   - Entry deleted
   - Storage cleaned up
```

**Expected assertions:**
- [ ] Baseline stored after first observation
- [ ] NO event emitted on first observation
- [ ] Baseline restored after reload
- [ ] Event emitted on valid status change after reload
- [ ] Storage cleaned up on entry delete

### Phase 2 Acceptance Criteria

- [ ] All Phase 2 tests pass with exit code `0`
- [ ] No test is skipped without documented reason
- [ ] First observation baseline without event
- [ ] Valid transition emits event with complete payload
- [ ] Duplicate observations (same source time) ignored
- [ ] Out-of-order observations (older source time) ignored
- [ ] Unknown statuses break continuity (no event)
- [ ] Stale gaps break continuity (no synthetic event on resume)
- [ ] Missing source time uses local observation time
- [ ] Baselines persist and restore correctly
- [ ] Stale baselines expire and are not restored
- [ ] Entry isolation confirmed (no crossover)
- [ ] Storage failures logged, not silent
- [ ] Integration test passes: setup → reload → status change → shutdown
- [ ] Code coverage ≥ 80% for Phase 2 modules

---

## Running the Full Phase 1 & 2 Test Suite

### Command

```bash
python -m pytest \
  tests/test_snapshot.py \
  tests/test_kystverket_client.py \
  tests/test_coordinator_snapshot.py \
  tests/test_phase_1_extended.py \
  tests/test_vessel_events.py \
  tests/test_storage.py \
  tests/test_integration.py::test_status_baseline_survives_entry_unload_and_reload \
  -v --tb=short
```

### Expected Output

```
tests/test_snapshot.py::TestSnapshotParsing::test_valid_snapshot PASSED
tests/test_snapshot.py::TestTimestampNormalization::test_iso_timestamp PASSED
...
tests/test_vessel_events.py::TestFirstObservation::test_no_event_on_baseline PASSED
tests/test_vessel_events.py::TestValidTransition::test_emit_event PASSED
tests/test_vessel_events.py::TestDuplicateHandling::test_no_event_duplicate PASSED
...
tests/test_storage.py::TestBaselineRestore::test_restore_after_reload PASSED
tests/test_storage.py::TestEntryIsolation::test_no_crossover PASSED
...
tests/test_integration.py::test_status_baseline_survives_entry_unload_and_reload PASSED

====== 92+ passed in X.XXs ======
```

### Exit Code

- **0** = All tests passed ✅
- **1** = Some tests failed ❌
- **5** = No tests collected (wrong path or syntax error)

---

## Code Quality Checks

### Linting

```bash
ruff check custom_components/marinetraffic_tracker tests/
```

**Expected:**
```
All checks passed!
```

### Type Checking

```bash
mypy custom_components/ --ignore-missing-imports
```

**Expected:**
```
Success: no issues found in 10 source files
```

### Format Verification

```bash
ruff format --check custom_components/ tests/
```

**Expected:**
```
All files already formatted correctly.
```

---

## Phase 1 & 2 Verification Checklist

Before marking Phase 1 & 2 complete, verify all items:

### Phase 1 Requirements

- [ ] **Snapshot Normalization**
  - [ ] Source-message timestamps preserved correctly
  - [ ] Local observation timestamps recorded separately
  - [ ] Legacy `last_seen` field maintained
  - [ ] Missing/old/future timestamps handled gracefully

- [ ] **Area Query Compatibility**
  - [ ] Radius mode filtering unchanged
  - [ ] Bounding box mode filtering unchanged
  - [ ] Area counts match pre-Phase-1 behavior

- [ ] **Snapshot Reuse**
  - [ ] One snapshot per poll cycle
  - [ ] Same snapshot used for area + watchlist + ports
  - [ ] No additional per-MMSI network requests

- [ ] **Fallback Paths**
  - [ ] Integration works without new snapshot methods
  - [ ] Fallback to legacy `get_vessels_in_radius()` / `get_vessels_in_box()`
  - [ ] Extra clients (AISHub, VesselFinder) work correctly

### Phase 2 Requirements

- [ ] **Baseline & First Observation**
  - [ ] First valid observation establishes baseline
  - [ ] NO event emitted on first observation
  - [ ] Baseline stored in memory and persisted to disk

- [ ] **Valid Transition Detection**
  - [ ] Status change detected correctly
  - [ ] Event emitted with complete payload (entry, mmsi, status, position, timestamp)
  - [ ] Baseline updated to new status

- [ ] **Duplicate & Out-of-Order Handling**
  - [ ] Repeated messages (same source time) ignored
  - [ ] Out-of-order messages (older source time) ignored
  - [ ] NO duplicate events emitted

- [ ] **Stale & Gap Handling**
  - [ ] Stale observations (older than timeout) break continuity
  - [ ] Coverage gaps do not fabricate transitions on resume
  - [ ] Baseline reset without event after gap

- [ ] **Unknown Status Handling**
  - [ ] Unknown status codes do not emit events
  - [ ] Baseline breaks continuity on unknown status
  - [ ] Next valid observation re-baselines without event

- [ ] **Persistence & Restore**
  - [ ] Baselines persist to `storage.py` on update
  - [ ] Baselines restore on coordinator startup
  - [ ] Stale baselines (age > timeout) not restored
  - [ ] Storage versioning handled correctly

- [ ] **Entry Isolation**
  - [ ] Two entries have separate baseline storage
  - [ ] No data leakage or crossover

- [ ] **Existing Features Unaffected**
  - [ ] Area counts unchanged
  - [ ] Legacy entered/exited events still fired
  - [ ] Existing sensors work normally
  - [ ] No breaking changes to config or entities

### Code Quality

- [ ] Ruff linting passes
- [ ] mypy type checking passes
- [ ] All Python files compile without syntax errors
- [ ] Code coverage ≥ 80% for Phase 1 & 2 modules

### Test Execution

- [ ] Phase 1 test command exits with code `0`
- [ ] Phase 2 test command exits with code `0`
- [ ] Integration test exits with code `0`
- [ ] No tests are skipped or deselected without documented reason
- [ ] Test output recorded (timestamp, exit codes, pass/fail/skip counts)

---

## Test Execution Record Template

Use this template to document your test run:

```
========================================
Phase 1 & 2 Test Execution Record
========================================

Date: 2026-10-30
Time: 18:30 UTC
Executor: [Your Name]
Environment: Home Assistant 2025.1.0, Python 3.12.x

PHASE 1 TESTS
=============

Command:
python -m pytest tests/test_snapshot.py tests/test_kystverket_client.py tests/test_coordinator_snapshot.py tests/test_phase_1_extended.py -v

Exit Code: 0
Passed: 28
Failed: 0
Skipped: 0

Duration: 3.45s

Notes:
- All snapshot parsing tests passed
- Timestamp normalization verified
- Area queries (radius/box) confirmed unchanged
- Fallback paths functional

PHASE 2 TESTS
=============

Command:
python -m pytest tests/test_vessel_events.py tests/test_storage.py -v

Exit Code: 0
Passed: 45
Failed: 0
Skipped: 0

Duration: 4.12s

Notes:
- Baseline establishment without event confirmed
- Status transitions emit events correctly
- Duplicate handling verified
- Out-of-order messages ignored as expected
- Stale gaps break continuity properly
- Persistence and restore working
- Entry isolation confirmed

INTEGRATION TEST
================

Command:
python -m pytest tests/test_integration.py::test_status_baseline_survives_entry_unload_and_reload -v

Exit Code: 0
Passed: 1
Failed: 0
Skipped: 0

Duration: 2.34s

Notes:
- Setup → reload → status change → shutdown cycle successful
- Baseline persisted and restored correctly
- No synthetic events emitted

CODE QUALITY
============

Linting:
$ ruff check custom_components/ tests/
Exit Code: 0
All checks passed!

Type Checking:
$ mypy custom_components/ --ignore-missing-imports
Exit Code: 0
Success: no issues found in 10 source files

Format Check:
$ ruff format --check custom_components/ tests/
Exit Code: 0
All files already formatted correctly.

SUMMARY
=======

Total Tests Run: 74
Total Passed: 74
Total Failed: 0
Total Skipped: 0
Code Coverage: 82% (Phase 1/2 modules)
Overall Status: ✅ PASS

Recommended Action:
Approved for Phase 3 & Phase 4 integration testing.
```

---

## Troubleshooting

### Test Failures

If a test fails, check:

1. **ModuleNotFoundError** → Install dependencies:
   ```bash
   pip install -r requirements-ci.txt
   ```

2. **Test discovery failures** → Ensure test file follows `test_*.py` naming

3. **Fixture errors** → Check `conftest.py` imports and mock setup

4. **Async test errors** → Ensure `@pytest.mark.asyncio` decorator present

### Coverage Issues

View coverage per module:

```bash
python -m pytest tests/test_vessel_events.py --cov=custom_components.marinetraffic_tracker.vessel_events --cov-report=term-missing
```

### Type Checking Failures

Fix type annotations in flagged modules:

```bash
mypy custom_components/marinetraffic_tracker/vessel_events.py --show-error-codes
```

---

## Next Steps

After Phase 1 & 2 verification passes:

1. ✅ Record test results in this document
2. ✅ Archive execution logs
3. → Begin Phase 3 integration testing
4. → Proceed to Phase 4 when Phase 3 complete

---

## References

- **Phase 1 Design**: Shared snapshot normalization and compatibility
- **Phase 2 Design**: Status transitions with hysteresis and persistence
- **Code**: `custom_components/marinetraffic_tracker/vessel_events.py`, `storage.py`
- **Tests**: `tests/test_vessel_events.py`, `tests/test_storage.py`
- **Architecture**: `docs/architecture.md`
