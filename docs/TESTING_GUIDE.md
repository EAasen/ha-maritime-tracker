# Norwegian Maritime Tracker - Comprehensive Testing Guide

## Overview

This guide provides complete testing instructions for the Norwegian Maritime Tracker integration when installed on Home Assistant OS (HAOS). The integration supports vessel tracking, watchlists, maritime event detection, and real-time WebSocket-based dashboards.

**Version:** 1.2.0  
**Last Updated:** October 2026  
**Minimum HA Version:** 2025.1.0

---

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Manual HAOS Testing](#manual-haos-testing)
5. [Validation Checklist](#validation-checklist)
6. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Prerequisites

#### For Development Testing (Linux/macOS/Windows)

```bash
# Python 3.11+
python --version

# Install dependencies
pip install -r requirements-ci.txt

# Verify installations
pytest --version
pytest-asyncio --version
pytest-cov --version
```

#### For HAOS Installation Testing

1. **HA Instance Requirements:**
   - Home Assistant OS (HAOS) installation
   - Version 2025.1.0 or later
   - Network access to maritime data sources:
     - Kystverket (Norwegian Coastal Administration)
     - MarineTraffic
     - AIS Hub
     - Vessel Finder

2. **Network Configuration:**
   - API access to Norwegian maritime services
   - WebSocket support for real-time updates
   - Geographic area configured (latitude/longitude)

---

## Unit Tests

### Running All Unit Tests

```bash
# Run all tests with coverage
pytest -v --cov=custom_components/marinetraffic_tracker

# Run tests with detailed output
pytest -vv

# Run specific test file
pytest tests/test_coordinator.py -v

# Run specific test
pytest tests/test_coordinator.py::test_coordinator_initialization -v
```

### Test Categories

#### Core Functionality Tests

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_config_flow.py` | Configuration flow validation | User configuration input handling |
| `test_coordinator.py` | Coordinator logic | Central update coordination |
| `test_coordinator_snapshot.py` | Snapshot functionality | Vessel data snapshots |
| `test_client.py` | Main client logic | Core integration functionality |

#### Data Source Tests

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_kystverket_client.py` | Kystverket API | Norwegian coastal data |
| `test_aishub_client.py` | AIS Hub API | Automatic Identification System |
| `test_vesselfinder_client.py` | Vessel Finder API | Vessel identification data |
| `test_barentswatch_auth.py` | Barents Watch auth | Authentication for protected APIs |

#### Feature Tests

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_watchlist.py` | Vessel watchlist | Tracked vessels outside area |
| `test_vessel_events.py` | Vessel events | Status change event emission |
| `test_websocket_api.py` | WebSocket API | Real-time dashboard updates |
| `test_port_calls.py` | Port calls tracking | Port arrival/departure events |
| `test_storage.py` | Data persistence | Persistent state storage |

#### Entity & Attribute Tests

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_entity_properties.py` | Entity metadata | Device/entity configuration |
| `test_entity_registry_defaults.py` | HA registry defaults | Entity registration |
| `test_sensor_attributes.py` | Sensor attributes | Sensor state attributes |
| `test_vessel_device_info.py` | Device information | Device metadata |
| `test_entity_picture.py` | Entity pictures | Vessel/port pictures |

#### Utility & Filter Tests

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_geo_filter.py` | Geographic filtering | Area-based vessel filtering |
| `test_geo_location.py` | Location utilities | Coordinate calculations |
| `test_statistics.py` | Statistics calculation | Aggregate vessel counts |
| `test_anchored_vessels.py` | Anchored vessel detection | Stationary vessel identification |
| `test_vessel_log.py` | Vessel history logging | Historical vessel data |

#### Compatibility Tests

| Test File | Coverage | Purpose |
|-----------|----------|---------|
| `test_ha_version_compatibility.py` | HA version support | Version compatibility checks |
| `test_manifest.py` | Manifest validation | Integration manifest format |
| `test_translations.py` | Translation files | Multi-language support |
| `test_integration.py` | Full integration | End-to-end functionality |
| `test_multi_source.py` | Multi-source operation | Multiple data source handling |
| `test_http_client.py` | HTTP client | Network communication |
| `test_phase_1_extended.py` | Legacy tests | Phase 1 extended coverage |
| `test_min_update_interval.py` | Update intervals | Rate limiting verification |

### Running Specific Test Groups

```bash
# Configuration tests
pytest tests/test_config_flow.py tests/test_manifest.py -v

# Data source tests
pytest tests/test_*_client.py -v

# Feature tests
pytest tests/test_watchlist.py tests/test_vessel_events.py \
        tests/test_websocket_api.py tests/test_port_calls.py -v

# Entity tests
pytest tests/test_entity*.py tests/test_sensor*.py tests/test_vessel_device*.py -v

# All tests
pytest tests/ -v --cov=custom_components/marinetraffic_tracker
```

---

## Integration Tests

### Test Execution Workflow

#### Stage 1: Syntax & Import Validation

```bash
# Verify Python syntax
python -m py_compile custom_components/marinetraffic_tracker/__init__.py
python -m py_compile custom_components/marinetraffic_tracker/coordinator.py
python -m py_compile custom_components/marinetraffic_tracker/config_flow.py
python -m py_compile custom_components/marinetraffic_tracker/storage.py
python -m py_compile custom_components/marinetraffic_tracker/port_calls.py

# Verify test file syntax
python -m py_compile tests/test_coordinator.py
python -m py_compile tests/test_config_flow.py
python -m py_compile tests/test_port_calls.py
```

**Expected Result:** All compilations succeed with exit code 0

#### Stage 2: Linting & Type Checking

```bash
# Run Ruff linter
ruff check custom_components/marinetraffic_tracker tests/

# Run MyPy type checking
mypy custom_components/marinetraffic_tracker --no-error-summary 2>&1 | head -20

# Run Pylint
pylint custom_components/marinetraffic_tracker --disable=all --enable=E,F
```

**Expected Result:** No critical errors in output

#### Stage 3: Unit Test Execution

```bash
# Run all tests
pytest tests/ -v --tb=short

# Run with coverage report
pytest tests/ -v --cov=custom_components/marinetraffic_tracker \
       --cov-report=term-missing --cov-report=html
```

**Expected Result:**
- All tests pass
- Coverage ≥ 80% for core modules
- No test failures or errors

#### Stage 4: Snapshot & Fixture Tests

```bash
# Run coordinator snapshot tests
pytest tests/test_coordinator_snapshot.py -v

# Run fixture-based tests
pytest tests/test_integration.py -v
```

**Expected Result:** All snapshot comparisons match

### Coverage Report

```bash
# Generate coverage report
pytest --cov=custom_components/marinetraffic_tracker \
       --cov-report=html \
       --cov-report=term-missing

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows
```

---

## Manual HAOS Testing

### 1. Installation

#### Add Custom Repository

1. Go to **Settings → Devices & Services → Integrations**
2. Click **Create Automation** (gear icon, top right)
3. Select **Repositories**
4. Add repository: `https://github.com/EAasen/ha-maritime-tracker`
5. Select "Norwegian Maritime Tracker"
6. Click **Install**
7. Restart Home Assistant

#### Direct Installation (Development)

```bash
# Copy integration to HAOS
scp -r custom_components/marinetraffic_tracker/ root@ha-ip:/usr/share/hassio/homeassistant/custom_components/

# SSH into HAOS and restart
ssh root@ha-ip
ha core restart
```

### 2. Configuration Testing

#### Configuration Flow

1. Go to **Settings → Devices & Services → Integrations**
2. Click **Create Integration**
3. Search for "Norwegian Maritime Tracker"
4. **Step 1: Area Configuration**
   - Set **Name**: "Norwegian Coast" (or preferred name)
   - Set **Latitude**: 60.5 (default: Norway)
   - Set **Longitude**: 5.0 (default: Norway)
   - Set **Radius**: 50 km (test with various distances)
   - Select **Data Sources**: Enable all for testing
     - ✓ Kystverket
     - ✓ MarineTraffic
     - ✓ AIS Hub
   - Click **Next**

5. **Step 2: Advanced Options**
   - Set **Update Interval**: 60 seconds (shorter for testing)
   - Set **Max Vessel Display**: 20 (test with various counts)
   - Set **Statistics Window**: 24 hours
   - Click **Next**

6. **Step 3: Watchlist Configuration (Optional)**
   - Add test MMSIs (example: 259637000, 259637100)
   - Click **Create**

#### Expected Outcome
- Integration loads successfully
- No configuration errors appear
- Device created: "marinetraffic_tracker_[name]"

### 3. Entity Verification

#### Device Inspector

1. Go to **Settings → Devices & Services → Devices**
2. Find "marinetraffic_tracker_[name]"
3. Verify entities exist:

| Entity | Domain | Type | Expected |
|--------|--------|------|----------|
| Area Count | sensor | Number | ≥ 0 |
| Anchored Count | sensor | Number | ≥ 0 |
| Watchlist Count | sensor | Number | ≥ 0 |
| Stale Vessels | sensor | Number | ≥ 0 |
| Last Update | sensor | Timestamp | Recent |
| Area Status | sensor | Text | "active" |

### 4. Data Source Testing

#### Verify API Connectivity

1. Go to **Developer Tools → Logs**
2. Look for successful API responses:
   ```
   [marinetraffic_tracker] Connected to Kystverket
   [marinetraffic_tracker] Connected to MarineTraffic
   [marinetraffic_tracker] Connected to AIS Hub
   ```

3. Check for errors in logs (should be none for normal operation)

#### Test Each Data Source

```yaml
# In Developer Tools → Services
service: marinetraffic_tracker.ping_source
data:
  source: kystverket

service: marinetraffic_tracker.ping_source
data:
  source: marinetraffic

service: marinetraffic_tracker.ping_source
data:
  source: aishub
```

### 5. Watchlist Testing

#### Add Vessels to Watchlist

1. Go to **Settings → Devices & Services → Integrations**
2. Select integration name
3. Click **Options**
4. Add MMSIs (example test MMSIs):
   - 259637000 (Norwegian vessel)
   - 259637100 (Test vessel)
5. Save and wait for next update (60 sec default)

#### Verify Watchlist

1. Check **Developer Tools → States**
2. Find `sensor.marinetraffic_tracker_watchlist_count`
3. Verify:
   - State shows correct count
   - Attribute `vessels` contains tracked MMSIs
   - Vessel data includes: name, speed, status, position

### 6. WebSocket Dashboard Testing

#### Install Maritime Tracker Card

1. Go to **Settings → Devices & Services → Integrations**
2. Download the maritime-tracker-card
3. Add to Lovelace dashboard:

```yaml
type: custom:maritime-tracker-card
entity: sensor.marinetraffic_tracker_area_count
title: Maritime Tracker
```

#### Verify Dashboard Features

- [ ] Vessel markers appear on map
- [ ] Real-time updates via WebSocket
- [ ] Vessel trails visible (position history)
- [ ] Heading indicators shown
- [ ] Watchlist vessels highlighted
- [ ] Stale vessels marked distinctly
- [ ] Details pane shows vessel info
- [ ] Map controls functional (fit, reset)
- [ ] Mobile view responsive

### 7. Event Testing

#### Verify Vessel Status Events

1. Go to **Developer Tools → Events**
2. Listen for: `marinetraffic_vessel_status_changed`
3. Trigger by changing vessel status (wait for API update)
4. Check event payload:
   ```json
   {
     "entry_id": "...",
     "vessel_mmsi": "259637000",
     "old_status": "underway_using_engine",
     "new_status": "anchored",
     "timestamp": "2026-10-30T18:57:06Z"
   }
   ```

### 8. Persistence Testing

#### Verify State Persistence

1. Go to **Developer Tools → States**
2. Note current `sensor.marinetraffic_tracker_*` values
3. Restart Home Assistant: **Settings → System → Restart**
4. Wait 2 minutes for integration reload
5. Verify states restored correctly

#### Verify Watchlist Persistence

1. Add MMSIs to watchlist
2. Restart Home Assistant
3. Verify watchlist MMSIs still present after restart

### 9. Performance Testing

#### Monitor Memory & CPU

```bash
# SSH into HAOS
ssh root@ha-ip

# Monitor processes
watch -n 2 'ps aux | grep hass'

# Check disk usage
df -h /

# Monitor memory
free -h
```

#### Expected Performance
- Memory usage stable (< 200 MB increase)
- CPU usage < 5% idle
- API calls every 60 seconds (configurable)
- WebSocket updates < 100ms latency

### 10. Error Recovery Testing

#### Test API Failure Recovery

1. Disable internet access (or use firewall rule)
2. Check logs for error handling
3. Re-enable internet
4. Verify integration recovers within 5 minutes

#### Test State Loss Recovery

1. Delete `@lovelace` state
2. Go to **Settings → Data & Privacy → Download Your Data**
3. Restart integration
4. Verify watchlist and statistics restored

---

## Validation Checklist

### Pre-Release Validation

- [ ] All 33 unit tests pass
- [ ] Code coverage ≥ 80%
- [ ] Ruff linter passes (0 errors)
- [ ] MyPy type checking passes (0 errors)
- [ ] No breaking changes in manifest
- [ ] Version bump in manifest.json
- [ ] CHANGELOG.md updated
- [ ] README.md documentation current

### Installation Validation (HAOS)

- [ ] Integration installs without errors
- [ ] Configuration flow completes
- [ ] All entities created
- [ ] API connectivity verified
- [ ] No errors in Home Assistant logs
- [ ] Stats update within 2 update intervals

### Feature Validation

- [ ] Vessel tracking functional
- [ ] Watchlist configuration works
- [ ] Status events emit correctly
- [ ] WebSocket API responds
- [ ] Dashboard card renders
- [ ] State persistence working
- [ ] API failure recovery functional

### Performance Validation

- [ ] Memory usage < 200 MB
- [ ] Update cycle completes < 30s
- [ ] No thread leaks
- [ ] WebSocket cleanup on disconnect
- [ ] No infinite loops in logs

---

## Troubleshooting

### Common Issues

#### Integration Not Appearing in Config Flow

**Solution:**
```bash
# Clear cache and restart
rm -rf /usr/share/hassio/homeassistant/.cache
ha core restart
```

#### API Connection Errors

**Check:**
```bash
# Verify network connectivity
curl -I https://www.kystverket.no

# Test specific endpoints in HA logs
# Go to Settings → Logs → Enable Debug Logging for marinetraffic_tracker
```

**Solution:**
- Verify API URLs are correct
- Check firewall rules
- Verify API credentials (for Barents Watch)
- Check network interface on HAOS

#### Entities Not Updating

**Check:**
```bash
# Verify coordinator is running
# Developer Tools → Services → marinetraffic_tracker.debug_status

# Check update interval
# Settings → Integrations → Norwegian Maritime Tracker → Options
```

**Solution:**
- Increase update interval if APIs are slow
- Check for API rate limiting in logs
- Restart the integration

#### WebSocket Disconnections

**Check:**
```bash
# Monitor WebSocket connections
# Browser console (F12): Check for connection errors
```

**Solution:**
- Verify CORS settings on HA
- Check firewall for WebSocket port
- Restart the integration

### Debug Mode

Enable detailed logging:

```yaml
# Add to configuration.yaml
logger:
  logs:
    custom_components.marinetraffic_tracker: debug
```

Restart Home Assistant and check logs for detailed output.

---

## Test Automation

### CI/CD Pipeline

Tests run automatically on:
- Pull request creation
- Push to main branch
- Scheduled daily runs

### GitHub Actions Workflow

```bash
# View workflow results
gh run list -R EAasen/ha-maritime-tracker

# View specific run logs
gh run view <run-id> -R EAasen/ha-maritime-tracker
```

---

## Support

For test failures or issues:

1. **Check existing issues:** https://github.com/EAasen/ha-maritime-tracker/issues
2. **Create new issue** with:
   - HA version
   - Integration version
   - Relevant logs (Settings → Logs)
   - Steps to reproduce
3. **Discussion:** https://github.com/EAasen/ha-maritime-tracker/discussions

---

## Related Documentation

- [Installation Guide](./installation.md)
- [Configuration Guide](./configuration.md)
- [Usage Guide](./usage.md)
- [Troubleshooting](./troubleshooting.md)
- [Development Guide](./development.md)
- [Architecture](./architecture.md)
