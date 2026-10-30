# Changelog

Notable changes to Norwegian Maritime Tracker are recorded here. Work under
`Unreleased` is implemented in the repository but is not yet a published
release; the integration version remains unchanged until release preparation.

## Unreleased

### Added

- Shared Kystverket snapshot fetching with normalized source-message and local
  observation timestamps, while preserving the existing area query behavior.
- `marinetraffic_vessel_status_changed` Home Assistant event for valid AIS
  status transitions. Its payload includes entry and vessel identity, old and
  new statuses, source and observation timestamps, data source, and position.
- Per-entry, versioned persistence for transition baselines, with debounced
  writes, startup restore, unload flush, stale expiry, a 2,000-vessel bound,
  explicit eviction warnings, and cleanup when an integration entry is removed.

### Reliability

- Status observations are processed before display filters. Duplicate and
  out-of-order messages do not emit events; unknown statuses, stale data,
  implausible future timestamps, and observation gaps break continuity rather
  than creating synthetic transitions.
- First observations and observations after a continuity gap establish a
  baseline without emitting a transition. Existing area counts and legacy
  entered/exited events are preserved.

### Verification

- Phase 1 and Phase 2 focused tests cover snapshot use and fallback, transition
  ordering and continuity, storage restore/removal, and entry isolation.
- Close-out validation: **92 targeted Phase 1/2 tests passed**; Ruff, mypy,
  and Python compilation checks passed.
