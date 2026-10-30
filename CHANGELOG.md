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
- **Phase 3: Persistent vessel watchlist** (REQ-004, REQ-005, REQ-010)
  - Configurable list of up to 100 vessel MMSIs tracked outside the configured
    geographic area, editable through Home Assistant options.
  - Watched vessels remain observable within feed coverage without altering
    area counts, statistics, or creating duplicate entity identities.
  - Separate `_watchlist_vessels` registry with unified resolver (`get_vessel()`)
    supporting both area and watched vessel lookups.
  - Global aggregate `marinetraffic_watchlist_count` sensor exposing watched
    vessel count and structured list of current observations with name, speed,
    status, and position data.
  - Watched vessels bypass all display filters (type, anchored, moored); existing
    area views and statistics remain unaffected.
  - Stale timeout and eviction policy consistent with area vessels; no additional
    API calls required to maintain the watchlist.

### Reliability

- Status observations are processed before display filters. Duplicate and
  out-of-order messages do not emit events; unknown statuses, stale data,
  implausible future timestamps, and observation gaps break continuity rather
  than creating synthetic transitions.
- First observations and observations after a continuity gap establish a
  baseline without emitting a transition. Existing area counts and legacy
  entered/exited events are preserved.
- Watched vessels maintained in separate registry ensure that watchlist queries
  do not interfere with area-based statistics or entity identity tracking.

### Verification

- Phase 1, 2, and 3 focused tests cover snapshot use and fallback, transition
  ordering and continuity, storage restore/removal, entry isolation, watchlist
  configuration/validation, state management, entity resolution, filter
  independence, persistence, and no-additional-requests efficiency.
- Close-out validation: **92+ targeted Phase 1/2 tests + 50+ Phase 3 tests
  passed**; Ruff, mypy, and Python compilation checks passed.
