# Phase 2: Status-Transition Automations

**Status**: ✅ Implemented
**Prerequisite**: Phase 1 snapshot foundation

## Behavior

- The first valid observation establishes a status baseline without firing an event.
- A new status fires `marinetraffic_vessel_status_changed` once for that MMSI and entry.
- Duplicate or out-of-order observations do not change the baseline or emit events.
- Missing/unknown status, stale source time, implausible future time, and gaps
  invalidate continuity; the next valid observation establishes a new baseline.
- Status observations are evaluated before vessel-type and anchored/moored
  display filters, without changing area counts or legacy entered/exited events.
- Source timestamps are compared when available; local observation timestamps
  provide ordering and freshness when the source timestamp is absent.
- AIS status is a reported navigational status, not proof of berth activity.

## Event payload

`marinetraffic_vessel_status_changed` includes `entry_id`, `mmsi`, `name`,
`old_status`, `new_status`, `source_msgtime`, `observation_time`, `source`,
and `position` (`latitude`, `longitude`).

## Persistence and bounds

- `VesselEventStorage` uses Home Assistant's versioned `Store` API with a
  separate key per config entry.
- Baselines are restored before the initial poll, saved with a two-second
  debounce, flushed on unload, and removed when the entry is deleted.
- Baselines expire after the configured stale timeout and are capped at 2,000
  per entry. Expiration and eviction never create transitions; eviction emits
  an explicit warning.
- Invalid persisted data and storage I/O errors are surfaced rather than
  silently reset.

## Implementation and tests

- Decision logic: `custom_components/marinetraffic_tracker/vessel_events.py`
- Persistence: `custom_components/marinetraffic_tracker/storage.py`
- Coordinator and config-entry lifecycle wiring:
  `custom_components/marinetraffic_tracker/coordinator.py` and
  `custom_components/marinetraffic_tracker/__init__.py`
- Tests: `tests/test_vessel_events.py`, `tests/test_storage.py`, and the
  restart-continuity case in `tests/test_integration.py`
- Progress and validation details: `.github/maritime-map-progress.md`
