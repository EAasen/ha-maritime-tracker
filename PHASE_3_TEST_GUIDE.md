# Phase 3 Test Execution & Verification Guide

**Status**: Phase 3 Implementation Complete ✅  
**Test Infrastructure Ready**: Setup Complete  
**Coverage Target**: 80%+ (enforced in CI)

---

## Quick Start

### Run All Tests
```bash
python verify_phase3.py --coverage
```

### Run Watchlist Tests Only
```bash
python verify_phase3.py --watchlist-only
```

### Run Linting & Type Checking
```bash
python verify_phase3.py --lint
python verify_phase3.py --type-check
```

### Verify Files Exist
```bash
python verify_phase3.py --files-only
```

---

## Test Infrastructure

### Pytest Configuration
- **File**: `pytest.ini`
- **Test Directory**: `tests/`
- **Async Mode**: Auto (asyncio_mode=auto)
- **Coverage Target**: 80% minimum (enforced by CI)

### CI/CD Workflow
- **File**: `.github/workflows/tests.yml`
- **Python Version**: 3.12+
- **Trigger**: Push, Pull Request, Manual
- **Artifacts**: Coverage reports (XML + HTML)

### Dependencies
- **Requirements File**: `requirements-ci.txt`
- **Key Packages**:
  - pytest 8.3.4
  - pytest-cov 6.0.0
  - pytest-homeassistant-custom-component 0.13.205
  - mypy 2.3.1
  - ruff (linting)

---

## Phase 3 Test Coverage

### Test Files Created/Modified

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_watchlist.py` | 20+ new | Watchlist core functionality |
| `tests/test_config_flow.py` | +18 | MMSI validation & config |
| `tests/test_sensor_attributes.py` | +14 | Watchlist sensor attributes |
| `tests/test_entity_registry_defaults.py` | +1 | Entity registry defaults |
| `tests/test_vessel_device_info.py` | +5 | Device info resolution |

**Total**: 58+ new/extended tests for Phase 3

### Test Categories

#### Configuration & Validation (18 tests)
- MMSI validation (length, characters, deduplication)
- Schema integration
- Options flow acceptance/rejection
- Field optionality

#### State Management (20+ tests)
- Watchlist initialization
- Watched vessel isolation
- Registry separation
- Persistence across config updates
- Stale eviction

#### Entity Resolution (8 tests)
- Unified resolver (`get_vessel()`)
- Area/watchlist precedence
- Device info lookup
- Tracker integration

#### Filter Independence (2 tests)
- Type filter bypass
- Anchored/moored exclusion bypass

#### Sensor Attributes (14 tests)
- Count sensor state
- Attribute presence/values
- Vessels list validation
- Sorting and filtering

#### Performance (1 test)
- No additional API calls

#### Debug Logging (1 test)
- Watched vessel count in logs

---

## Running Tests Locally

### Prerequisites
```bash
pip install -r requirements-ci.txt
```

### Full Test Suite
```bash
pytest tests/ -v --cov=custom_components.marinetraffic_tracker --cov-report=term-missing
```

### Watchlist Tests Only
```bash
pytest tests/test_watchlist.py -v
```

### Extended Tests (Config, Sensor, Entity Registry, Device Info)
```bash
pytest tests/test_config_flow.py::*watchlist* -v
pytest tests/test_sensor_attributes.py::TestWatchlistSensorAttributes -v
pytest tests/test_entity_registry_defaults.py::test_watchlist_sensor_enabled_by_default -v
pytest tests/test_vessel_device_info.py::TestWatchlistVesselResolver -v
```

### Run with Coverage Report
```bash
pytest tests/ -v \
  --cov=custom_components.marinetraffic_tracker \
  --cov-report=html \
  --cov-report=term-missing
```

Coverage report will be in `htmlcov/index.html`

### Check Code Quality
```bash
# Linting
ruff check custom_components tests

# Type checking
mypy custom_components/marinetraffic_tracker

# All checks via verify script
python verify_phase3.py
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/tests.yml`

**Steps**:
1. Checkout code
2. Set up Python 3.12
3. Install dependencies from `requirements-ci.txt`
4. Run pytest with coverage (80% minimum)
5. Upload coverage report as artifact

**Trigger Conditions**:
- On every push to any branch
- On pull requests
- Manual workflow dispatch

**Coverage Artifacts**:
- `coverage.xml` - Machine-readable XML format
- Available as GitHub Actions artifact for download

### Running CI Locally
```bash
# Simulates CI environment
python -m pytest tests/ -v \
  --cov=custom_components.marinetraffic_tracker \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=80
```

---

## Test Verification Checklist

### ✅ Phase 3 Implementation
- [x] T007: Watchlist options and validation
- [x] T008: Watchlist state and resolver
- [x] T009: Watchlist sensor and entity resolution
- [x] T010: Comprehensive test coverage

### ✅ Test Execution Requirements

- [ ] **Run Full Test Suite**
  ```bash
  python verify_phase3.py --coverage
  ```
  Expected: All tests pass, coverage > 80%

- [ ] **Coverage Report**
  - Verify watchlist code paths exercised
  - Check coordinator, sensor, entity coverage
  - Check config_flow validation coverage

- [ ] **Integration Testing**
  - Verify Home Assistant entity lifecycle
  - Test configuration persistence
  - Test entity resolution (area → watchlist transitions)

- [ ] **Production Readiness**
  - All linting checks pass
  - All type checks pass
  - No unhandled exceptions
  - Proper error messages for invalid configs

---

## Expected Test Results

### Test Counts
- **Phase 1/2 Tests**: 92+ (pre-existing)
- **Phase 3 Tests**: 58+ (new/extended)
- **Total**: 150+

### Coverage Targets
- **Overall**: ≥80% (enforced)
- **Watchlist Module**: ≥95%
- **Config Flow**: ≥90%
- **Coordinator**: ≥85%
- **Sensors**: ≥90%

### Quality Gates
- ✅ All tests pass
- ✅ No code style violations (ruff)
- ✅ All type hints correct (mypy)
- ✅ Coverage ≥80%
- ✅ No security warnings

---

## Debugging Test Failures

### Common Issues

#### 1. Import Errors
```bash
# Ensure dependencies installed
pip install -r requirements-ci.txt
```

#### 2. Async Test Issues
- Already configured in `pytest.ini`
- Uses `asyncio_mode=auto`

#### 3. Fixture/Mock Issues
Check `tests/conftest.py` for shared fixtures

#### 4. Coverage Below 80%
Run with term-missing to see uncovered lines:
```bash
pytest --cov=custom_components.marinetraffic_tracker --cov-report=term-missing
```

---

## Continuous Integration Details

### Build Matrix
- **Python**: 3.12 (minimum required)
- **OS**: Ubuntu latest
- **Caching**: pip cache for faster builds

### Failure Conditions
- Any test fails
- Coverage drops below 80%
- Linting errors detected (checked separately in lint.yml)
- Type checking errors (checked separately in validate.yml)

### Artifact Retention
- Coverage reports: Available for download from Actions
- Logs: Available for debugging in Actions UI

---

## Release Readiness Checklist

Before releasing Phase 3:

- [ ] All tests pass (automated in CI)
- [ ] Coverage ≥80% (automated in CI)
- [ ] Code review completed
- [ ] Documentation updated:
  - [x] CHANGELOG.md updated
  - [x] Feature plan updated
  - [x] Phase 3 complete summary created
- [ ] No breaking changes to existing features
- [ ] Backward compatible configuration
- [ ] User-facing documentation prepared

---

## Next Steps

### Immediate (Required for Release)
1. Run full test suite: `python verify_phase3.py --coverage`
2. Review coverage report
3. Address any uncovered code paths

### Before Phase 4
1. Create release notes highlighting Phase 3 features
2. Prepare user documentation
3. Test with real Home Assistant installation

### Future Enhancements
- Add integration tests with Home Assistant
- Add frontend tests for watchlist UI
- Add performance/load tests for large watchlists

---

## Contact & Support

For issues with tests:
1. Check test output with `-v` flag
2. Review test file docstrings
3. Check GitHub Issues for known problems
4. See CONTRIBUTING.md for development guidelines

---

## Appendix: Quick Commands

```bash
# Verify Phase 3 complete
python verify_phase3.py --files-only

# Run all tests with coverage
python verify_phase3.py --coverage

# Run only watchlist tests
python verify_phase3.py --watchlist-only

# Run linting
python verify_phase3.py --lint

# Run type checking
python verify_phase3.py --type-check

# Run full verification (all checks)
python verify_phase3.py

# Full pytest with HTML coverage report
pytest tests/ -v \
  --cov=custom_components.marinetraffic_tracker \
  --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

**Last Updated**: 2026-10-30  
**Phase 3 Status**: Complete and Ready for Testing ✅
