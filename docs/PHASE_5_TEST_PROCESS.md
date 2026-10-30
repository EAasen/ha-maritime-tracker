# Phase 5 Test Process & Validation Guide

**Created:** 2026-10-30  
**Status:** Ready for Implementation  
**Phase:** 5.1 Validation & Integration Testing

---

## 🎯 Purpose

This document outlines the comprehensive test process to validate that Phase 5.1 (Port Geofencing and Confirmed Calls) is correctly implemented, integrated, and production-ready for Phase 5.2 development.

---

## 📋 Test Execution Overview

```
Phase 5.1 Test Flow
═══════════════════════════════════════════════════════════════════════════

┌─ STAGE 1: PRE-TEST SETUP ─────────────────────────────────────────────┐
│ • Environment validation                                               │
│ • Dependency verification                                              │
│ • File integrity checks                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─ STAGE 2: SYNTAX & LINT VALIDATION ───────────────────────────────────┐
│ • Python syntax check (py_compile)                                     │
│ • Import validation                                                    │
│ • Linting checks (flake8, pylint)                                      │
│ • Type hints (mypy)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─ STAGE 3: UNIT TESTS ─────────────────────────────────────────────────┐
│ • Port call tracker logic                                              │
│ • Geofence calculations                                                │
│ • Hysteresis state machine                                             │
│ • Storage operations                                                   │
│ • Config validation                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─ STAGE 4: INTEGRATION TESTS ──────────────────────────────────────────┐
│ • Coordinator integration                                              │
│ • Event firing                                                         │
│ • Baseline persistence                                                 │
│ • Call persistence                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─ STAGE 5: CODE QUALITY GATES ─────────────────────────────────────────┐
│ • Coverage thresholds (≥80%)                                           │
│ • No breaking changes                                                  │
│ • No new vulnerabilities                                               │
│ • Code style compliance                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
              ✅ ALL TESTS PASS - READY FOR PHASE 5.2
```

---

## 🔧 STAGE 1: Pre-Test Setup

### 1.1 Environment Validation

**Objective:** Verify development environment is ready

**Steps:**

```bash
# Check Python version
python --version
# Expected: Python 3.11.x or higher

# Check pytest installation
pytest --version
# Expected: pytest 7.x or higher

# List installed packages
pip list | grep -E "pytest|pytest-asyncio|pytest-cov"
```

**Expected Output:**
```
Python 3.11.9
pytest 7.4.3
pytest-asyncio (installed)
pytest-cov (installed)
```

**Pass Criteria:**
- [ ] Python ≥3.11
- [ ] pytest installed
- [ ] pytest-asyncio installed
- [ ] pytest-cov installed

### 1.2 File Integrity Checks

**Objective:** Verify all Phase 5.1 files exist

**New Files:**
```bash
ls -l custom_components/marinetraffic_tracker/port_calls.py
ls -l tests/test_port_calls.py
```

**Modified Files:**
```bash
ls -l custom_components/marinetraffic_tracker/{const,config_flow,storage,coordinator}.py
ls -l custom_components/marinetraffic_tracker/strings.json
```

**Pass Criteria:**
- [ ] port_calls.py exists and >10 KB
- [ ] test_port_calls.py exists and >15 KB
- [ ] All modified files exist
- [ ] No files corrupted or truncated

### 1.3 Dependency Verification

**Objective:** Check no new external dependencies added

**Command:**
```bash
grep -r "^import\|^from" custom_components/marinetraffic_tracker/port_calls.py | head -20
```

**Expected imports (only stdlib + HA):**
```
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, UTC, timedelta
from typing import Any
from homeassistant.core import HomeAssistant
```

**Pass Criteria:**
- [ ] Only stdlib imports
- [ ] Only existing HA imports
- [ ] No external packages added (numpy, scipy, etc.)

---

## 📝 STAGE 2: Syntax & Lint Validation

### 2.1 Python Syntax Check

**Objective:** Verify all Python files have valid syntax

**Command:**
```bash
python -m py_compile custom_components/marinetraffic_tracker/port_calls.py
python -m py_compile tests/test_port_calls.py
python -m py_compile custom_components/marinetraffic_tracker/storage.py
python -m py_compile custom_components/marinetraffic_tracker/coordinator.py
python -m py_compile custom_components/marinetraffic_tracker/config_flow.py
python -m py_compile custom_components/marinetraffic_tracker/const.py
```

**Expected Output:** No output (success), or errors are shown

**Pass Criteria:**
- [ ] port_calls.py: No syntax errors
- [ ] test_port_calls.py: No syntax errors
- [ ] storage.py: No syntax errors
- [ ] coordinator.py: No syntax errors
- [ ] config_flow.py: No syntax errors
- [ ] const.py: No syntax errors

### 2.2 Import Resolution

**Objective:** Verify all imports resolve correctly

**Command:**
```bash
python -c "from custom_components.marinetraffic_tracker.port_calls import PortCallTracker, PortBaseline, PortCall; print('✓ Imports OK')"
python -c "from custom_components.marinetraffic_tracker.storage import PortEventStorage; print('✓ Imports OK')"
python -c "from tests.test_port_calls import *; print('✓ Test imports OK')"
```

**Expected Output:**
```
✓ Imports OK
✓ Imports OK
✓ Test imports OK
```

**Pass Criteria:**
- [ ] port_calls imports resolve
- [ ] storage imports resolve
- [ ] test imports resolve
- [ ] No circular dependencies

### 2.3 Flake8 Linting

**Objective:** Verify code style compliance

**Command:**
```bash
flake8 custom_components/marinetraffic_tracker/port_calls.py --max-line-length=100
flake8 tests/test_port_calls.py --max-line-length=100
```

**Expected Output:** No output or only warnings

**Pass Criteria:**
- [ ] No E9xx errors (syntax/import)
- [ ] No F8xx errors (undefined names)
- [ ] E501 (line length) acceptable if documented
- [ ] No unused imports

### 2.4 Type Hints Check (mypy)

**Objective:** Verify type safety

**Command:**
```bash
mypy custom_components/marinetraffic_tracker/port_calls.py --strict --ignore-missing-imports
mypy custom_components/marinetraffic_tracker/storage.py --strict --ignore-missing-imports
```

**Expected Output:** Clean or only minor warnings

**Pass Criteria:**
- [ ] No type errors
- [ ] All functions have return type hints
- [ ] All parameters have type hints

---

## 🧪 STAGE 3: Unit Tests Execution

### 3.1 Run Port Calls Test Suite

**Objective:** Execute all port-call-specific unit tests

**Command:**
```bash
pytest tests/test_port_calls.py -v --tb=short -s
```

**Expected Output:**
```
tests/test_port_calls.py::TestGeofenceDetection::test_vessel_inside_geofence PASSED
tests/test_port_calls.py::TestGeofenceDetection::test_vessel_outside_geofence PASSED
tests/test_port_calls.py::TestGeofenceDetection::test_vessel_at_boundary PASSED
tests/test_port_calls.py::TestGeofenceDetection::test_longitude_scaling PASSED
tests/test_port_calls.py::TestHysteresisConfirmation::test_single_observation_pending PASSED
tests/test_port_calls.py::TestHysteresisConfirmation::test_arrival_confirmation PASSED
tests/test_port_calls.py::TestHysteresisConfirmation::test_departure_confirmation PASSED
tests/test_port_calls.py::TestHysteresisConfirmation::test_jitter_filtering PASSED
tests/test_port_calls.py::TestHysteresisConfirmation::test_multiple_transitions PASSED
tests/test_port_calls.py::TestStaleGapHandling::test_large_gap_clears_pending PASSED
tests/test_port_calls.py::TestStaleGapHandling::test_normal_gap_maintains_pending PASSED
tests/test_port_calls.py::TestBaselineResumption::test_resuming_outside_no_call PASSED
tests/test_port_calls.py::TestBaselineResumption::test_resuming_inside_no_call PASSED
tests/test_port_calls.py::TestCallAttributes::test_call_has_all_fields PASSED
tests/test_port_calls.py::TestCallAttributes::test_call_as_dict PASSED
tests/test_port_calls.py::TestCallAttributes::test_call_attributes_serializable PASSED
tests/test_port_calls.py::TestDuplicateMessageHandling::test_duplicate_messages_single_call PASSED
tests/test_port_calls.py::TestClearPending::test_clear_by_port PASSED
tests/test_port_calls.py::TestClearPending::test_clear_by_vessel PASSED
tests/test_port_calls.py::TestClearPending::test_clear_all_pending PASSED
tests/test_port_calls.py::TestClearPending::test_clear_nonexistent_pending PASSED

======================== 21 passed in X.XXs ========================
```

**Pass Criteria:**
- [ ] All 21 tests pass
- [ ] No test failures
- [ ] No test skips
- [ ] Execution time <10 seconds

### 3.2 Test Coverage Analysis

**Objective:** Verify test coverage meets threshold

**Command:**
```bash
pytest tests/test_port_calls.py --cov=custom_components/marinetraffic_tracker/port_calls --cov-report=term-missing
```

**Expected Output:**
```
Name                                                          Stmts   Miss  Cover   Missing
---------------------------------------
port_calls.py                                                   XXX     X   XX%
TOTAL                                                           XXX     X   XX%
```

**Pass Criteria:**
- [ ] Coverage ≥80% for port_calls.py
- [ ] Coverage ≥85% for critical paths (hysteresis, geofence)
- [ ] Missing lines documented if acceptable

### 3.3 Storage Test Execution

**Objective:** Verify port storage implementation

**Command:**
```bash
pytest tests/test_storage.py -v -k "Port" --tb=short
```

**Expected Tests:**
- PortEventStorage.async_load()
- PortEventStorage.async_save_baseline()
- PortEventStorage.async_save_call()
- PortEventStorage.async_get_recent_calls()
- PortEventStorage.async_clear_port()
- PortEventStorage.async_flush()

**Pass Criteria:**
- [ ] All port storage tests pass
- [ ] Coverage ≥85% for PortEventStorage
- [ ] No data loss in persistence

### 3.4 Config Flow Validation

**Objective:** Verify port configuration logic

**Command:**
```bash
pytest tests/test_config_flow.py -v -k "port" --tb=short -s
```

**Expected Tests:**
- Port validation functions
- Duplicate name detection
- Coordinate range validation
- Radius bounds checking (0.1–500 km)
- Config flow menu routing

**Pass Criteria:**
- [ ] All port config tests pass
- [ ] Port validation works correctly
- [ ] Invalid ports rejected

---

## 🔗 STAGE 4: Integration Tests

### 4.1 Coordinator Integration

**Objective:** Verify port tracking is integrated into coordinator

**Command:**
```bash
pytest tests/test_coordinator.py -v -k "port" --tb=short -s
```

**Test Scenarios:**
```
1. Port Initialization
   - Load port configuration on startup
   - Load baselines from storage
   - Initialize _port_tracker
   - Initialize _port_storage
   
2. Port Checking in Update Loop
   - Receive vessel observation
   - Check against all configured ports
   - Call PortCallTracker.check_vessel()
   - Receive PortCall if confirmed
   
3. Event Firing
   - Confirmed call emitted
   - EVENT_PORT_CALL event fired
   - Event payload includes call details
   - Event accessible to automations
   
4. Baseline Persistence
   - Baseline updated after call
   - Baseline persisted to storage
   - Baseline restored on restart
   
5. Shutdown Handling
   - Port data flushed on shutdown
   - State persisted
   - No data loss
```

**Pass Criteria:**
- [ ] Port tracker initialized correctly
- [ ] Port checking runs in update loop
- [ ] Events fired when calls confirmed
- [ ] Baselines persisted correctly
- [ ] Shutdown flushes state

### 4.2 Event Firing Integration

**Objective:** Verify EVENT_PORT_CALL event structure and delivery

**Create Test File** (if not existing):
```bash
pytest tests/test_port_events.py -v --tb=short
```

**Test Scenarios:**
```
1. Event Payload Structure
   - entry_id present
   - port_id present
   - port_name present
   - mmsi present
   - vessel_name present
   - call_type ("arrival" or "departure")
   - observed_at (ISO timestamp)
   - position (lat/lon)
   - eta (if available)
   - destination (if available)
   
2. Event Delivery
   - Event delivered to Home Assistant
   - Accessible in automations
   - Payload serializable to JSON
   
3. Multiple Ports
   - Events fire independently per port
   - No event crosstalk
   - Multiple events can fire same observation
```

**Pass Criteria:**
- [ ] Event structure correct
- [ ] All required fields present
- [ ] Event fires at correct time
- [ ] Multiple ports don't interfere

### 4.3 Baseline Persistence Integration

**Objective:** Verify baseline survival across restart/reload

**Test Scenarios:**
```
1. Baseline Saved After Call
   - Observation confirms call
   - Baseline updated in memory
   - Baseline persisted to storage
   
2. Baseline Restored on Startup
   - Coordinator initializes
   - Baselines loaded from storage
   - Memory cache populated
   - No calls fabricated on resume
   
3. Long Outage Handling
   - Baseline saved with timestamp
   - Gap >24h detected
   - Pending state cleared without call
   - Resume without false positives
```

**Pass Criteria:**
- [ ] Baselines saved after calls
- [ ] Baselines restored on restart
- [ ] No false calls on resume
- [ ] Long gaps handled safely

### 4.4 Call History Persistence

**Objective:** Verify call history bounded retention

**Test Scenarios:**
```
1. Call Saved After Confirmation
   - Call confirmed by hysteresis
   - Call saved to storage
   - Call queryable by time window
   
2. Bounded Retention (Max 50 per Port)
   - Save 50 calls: All retained
   - Save 51st call: Oldest removed
   - Retention FIFO by timestamp
   - No data loss until limit reached
   
3. Time Window Queries
   - Query last 24 hours
   - Query last 7 days
   - Query all history
   - Timestamps correct
```

**Pass Criteria:**
- [ ] Calls persisted correctly
- [ ] Retention limit enforced
- [ ] Time queries return correct data
- [ ] No unbounded growth

---

## 🎯 STAGE 5: Code Quality Gates

### 5.1 Coverage Threshold

**Objective:** Verify test coverage meets project standards

**Command:**
```bash
pytest tests/test_port_calls.py tests/test_storage.py tests/test_coordinator.py \
  --cov=custom_components/marinetraffic_tracker/port_calls \
  --cov=custom_components/marinetraffic_tracker/storage \
  --cov=custom_components/marinetraffic_tracker/coordinator \
  --cov-report=term-missing --cov-report=html
```

**Pass Criteria:**
- [ ] Overall coverage ≥80%
- [ ] port_calls.py ≥85%
- [ ] PortEventStorage ≥85%
- [ ] Coordinator port sections ≥80%
- [ ] No uncovered critical paths

### 5.2 No Breaking Changes

**Objective:** Verify Phase 5.1 doesn't break existing functionality

**Test Existing Features:**
```bash
pytest tests/ -v --tb=short -x
```

**Test Coverage:**
- Phase 1 (shared observations)
- Phase 2 (status events)
- Phase 3 (watchlist)
- Phase 4 (maritime map)
- Existing sensors and entities

**Pass Criteria:**
- [ ] All existing tests still pass
- [ ] No test failures introduced
- [ ] No regressions in Phase 1–4 features
- [ ] Backward compatible (ports optional)

### 5.3 No New Vulnerabilities

**Objective:** Check for security issues

**Command:**
```bash
# Check for common issues
grep -r "pickle\|eval\|exec" custom_components/marinetraffic_tracker/port_calls.py
grep -r "SELECT\|INSERT\|UPDATE" custom_components/marinetraffic_tracker/port_calls.py
# Should return no results

# Check for credential leaks
grep -r "password\|api_key\|secret" custom_components/marinetraffic_tracker/port_calls.py
# Should return no results
```

**Pass Criteria:**
- [ ] No pickle/eval/exec usage
- [ ] No SQL injection vectors
- [ ] No hardcoded credentials
- [ ] No unvalidated input to dangerous functions

### 5.4 Code Style Compliance

**Objective:** Verify code follows project standards

**Command:**
```bash
# Check naming conventions
grep -E "^[a-z_]+\s*=|^def [a-z_]+|^class [A-Z]" custom_components/marinetraffic_tracker/port_calls.py

# Check docstring presence
grep -c "\"\"\"" custom_components/marinetraffic_tracker/port_calls.py
# Should be >20 (classes + methods have docstrings)
```

**Pass Criteria:**
- [ ] Classes: PascalCase
- [ ] Functions/variables: snake_case
- [ ] Constants: UPPER_SNAKE_CASE
- [ ] Docstrings on public classes/methods
- [ ] Line length <120 characters
- [ ] Proper type hints

---

## 🏃 Quick Test Execution Script

**File:** `run_phase5_tests.sh`

```bash
#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  PHASE 5.1 TEST EXECUTION"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# STAGE 1: Pre-Test Setup
echo "STAGE 1: Pre-Test Setup"
echo "─────────────────────────────────────────────────────────────"
python --version
pytest --version
echo ""

# STAGE 2: Syntax & Lint
echo "STAGE 2: Syntax & Lint Validation"
echo "─────────────────────────────────────────────────────────────"
python -m py_compile custom_components/marinetraffic_tracker/port_calls.py
python -m py_compile tests/test_port_calls.py
echo "✓ Syntax checks passed"
echo ""

# STAGE 3: Unit Tests
echo "STAGE 3: Unit Tests"
echo "─────────────────────────────────────────────────────────────"
pytest tests/test_port_calls.py -v --tb=short
echo ""

# STAGE 4: Coverage
echo "STAGE 4: Coverage Analysis"
echo "─────────────────────────────────────────────────────────────"
pytest tests/test_port_calls.py --cov=custom_components/marinetraffic_tracker/port_calls --cov-report=term-missing
echo ""

# STAGE 5: Integration Tests
echo "STAGE 5: Integration Tests"
echo "─────────────────────────────────────────────────────────────"
pytest tests/test_coordinator.py -v -k "port" --tb=short
echo ""

# STAGE 6: Regression
echo "STAGE 6: Regression Tests (All Tests)"
echo "─────────────────────────────────────────────────────────────"
pytest tests/ -x --tb=short
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ ALL TESTS PASSED - PHASE 5.1 READY"
echo "═══════════════════════════════════════════════════════════════"
```

**Run:**
```bash
chmod +x run_phase5_tests.sh
./run_phase5_tests.sh
```

---

## ✅ Test Sign-Off Checklist

After running all tests, verify:

### Environment
- [ ] Python 3.11+ installed
- [ ] pytest and dependencies available
- [ ] No system warnings or errors

### Syntax & Linting
- [ ] port_calls.py: No syntax errors
- [ ] test_port_calls.py: No syntax errors
- [ ] All modified files: No syntax errors
- [ ] All imports resolve
- [ ] Flake8: No critical errors
- [ ] mypy: No type errors

### Unit Tests
- [ ] test_port_calls.py: 21/21 tests pass
- [ ] Coverage ≥80%
- [ ] No skipped tests
- [ ] All fixtures initialize correctly

### Integration Tests
- [ ] Port tracker initialized in coordinator
- [ ] Port checking in update loop
- [ ] Events fire correctly
- [ ] Baselines persist and restore
- [ ] Call history bounded correctly

### Code Quality
- [ ] No breaking changes
- [ ] No security vulnerabilities
- [ ] Code style compliant
- [ ] All docstrings present
- [ ] Type hints complete

### Regression Testing
- [ ] All Phase 1–4 tests pass
- [ ] Backward compatibility maintained
- [ ] No test failures introduced

---

## 📊 Test Results Template

**Date:** _______________  
**Tester:** _______________  
**Environment:** Python _______, pytest ________

| Test Category | Status | Notes |
|---------------|--------|-------|
| Syntax Validation | ⬜ | |
| Unit Tests (port_calls.py) | ⬜ | |
| Unit Tests (storage) | ⬜ | |
| Unit Tests (config_flow) | ⬜ | |
| Integration Tests | ⬜ | |
| Coverage (≥80%) | ⬜ | |
| No Breaking Changes | ⬜ | |
| Security Check | ⬜ | |
| Code Quality | ⬜ | |
| Regression Suite | ⬜ | |

**Overall Status:** ⬜ PASS / ⬜ FAIL

**Sign-Off:** _________________________  (Tester)

---

## 🚀 Next Steps After Passing Tests

1. ✅ Phase 5.1 validation complete
2. 📋 Review test results and sign-off
3. 🔀 Create PR for Phase 5.1 code
4. 👥 Request code review
5. 🚀 Merge to main branch
6. 📌 Tag v0.9.0-rc.1 (release candidate)
7. ▶️ Proceed with Phase 5.2 implementation

---

## 📞 Troubleshooting

### Tests Fail with Import Error
```
ModuleNotFoundError: No module named 'custom_components'
```
**Solution:** Run pytest from repository root, or adjust PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Tests Timeout
```
TimeoutError: ...
```
**Solution:** Increase pytest timeout or remove timeout for development:
```bash
pytest --timeout=60 tests/test_port_calls.py
```

### Coverage Below 80%
```
FAIL: Coverage XX% < 80%
```
**Solution:** Identify uncovered lines in `htmlcov/index.html` and add tests.

### Coordinator Tests Fail
```
FAIL: Port not in coordinator
```
**Solution:** Ensure `async_load_port_baselines()` is called before first poll in test setup.

---

**Last Updated:** 2026-10-30  
**Next Review:** After Phase 5.1 merge
