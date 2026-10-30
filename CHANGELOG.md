# Changelog

Notable changes to Norwegian Maritime Tracker are recorded here. Work under
`Unreleased` is implemented in the repository but is not yet a published
release; the integration version remains unchanged until release preparation.

## Unreleased

### UX Improvements

**Integration Discovery & Map Display**
- ✨ Added `integration_type: "service"` to manifest for automatic Home Assistant discovery
  - Integration now appears in **Settings → Devices & Services → Create Integration**
  - Users can search for and add the integration via UI without manual YAML configuration
  - Aligns with Home Assistant integration standards (comparable to Flight Radar 24)
- ✨ Added `async_step_import()` to config flow for YAML configuration support
  - Users can choose between UI-based setup or manual YAML configuration
  - Maintains backward compatibility with existing configurations
- 📚 Documented automatic map integration in [docs/configuration.md](docs/configuration.md)
  - New Section 8: "Map Integration" explains vessel display on Home Assistant maps
  - Clarifies how to add Map cards to dashboards
  - Describes area zone visibility and configuration
  - Notes comparison with Flight Radar 24 integration

### Changes

- Manifest: Added `"integration_type": "service"` field
- Config Flow: Added `async_step_import()` method to MarineTrafficConfigFlow class
- Documentation: Extended configuration guide with map integration details

---

## v1.2.0 (October 2026)

**Release Focus:** Production-ready WebSocket dashboard, persistent watchlist, and comprehensive testing.

### Major Features

**Phase 3: Persistent Vessel Watchlist**
- Configurable list of up to 100 vessel MMSIs tracked outside the configured geographic area
- Editable through Home Assistant options flow
- Watched vessels remain observable within feed coverage without altering area counts or statistics
- Separate watchlist registry with unified resolver supporting both area and watched vessel lookups
- Global aggregate `marinetraffic_watchlist_count` sensor exposing current observations
- Watched vessels bypass all display filters (type, anchored, moored)

**Phase 4: Maritime Map and WebSocket API**
- Real-time WebSocket API for bounded dashboard transport
  - Entry-scoped subscriptions with live coordinator updates
  - Paginated snapshots (max 100 vessels per page)
  - Bounded vessel trails with position history (max 50 points)
  - Stale detection and watched-vessel marking
  - Explicit error handling and cleanup on disconnect
- Custom Leaflet-based maritime tracker card for Lovelace
  - Real-time vessel markers updated via WebSocket
  - Heading/course indicators for each vessel
  - Bounded position trails with gap preservation
  - Entity picker to switch between tracked areas
  - Details pane with vessel MMSI, name, status, speed, destination, ETA
  - Watched vessel highlighting and stale state indication
  - Map controls (fit all vessels, reset to default view)
  - Mobile-responsive layout
  - Optional port board panel (prepared for Phase 5)

**Phase 5: Complete Integration**
- Comprehensive test suite (33+ test modules covering all functionality)
- Production-ready documentation and testing guide
- Repository cleanup with phase documentation organized in `/docs`
- Consolidated testing guide for development and HAOS installations

### Testing & Validation

- **33+ test modules** with full coverage of:
  - Client APIs (Kystverket, MarineTraffic, AIS Hub, Vessel Finder)
  - Coordinators and snapshot functionality
  - Configuration flow and entity registration
  - Watchlist management and persistence
  - WebSocket API and dashboard communication
  - Vessel events and status transitions
  - Geographic filtering and statistics
  - Port call tracking and vessel history
  - Multi-source operation and compatibility

- **Comprehensive Testing Guide** ([docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)) including:
  - Environment setup for development and HAOS
  - Unit test execution procedures
  - Integration test workflows
  - Manual HAOS testing procedures (10-step guide)
  - Performance and stress testing
  - Event validation
  - Error recovery testing
  - Troubleshooting common issues

- **Code Quality:**
  - Ruff linter passes (0 errors)
  - MyPy type checking passes
  - Code coverage ≥ 80% for core modules
  - CI/CD pipeline with automated testing on PR/push/schedule
  - HA version compatibility matrix (2025.1+)

### Reliability

- Status observations processed before display filters
- Duplicate and out-of-order messages handled gracefully
- Unknown statuses and implausible timestamps rejected
- First observations and gaps establish baseline without emitting events
- Watched vessels maintained in separate registry without interference
- WebSocket snapshots bounded to prevent large payload accumulation
- Subscriptions fully cleaned up on card close or entry unload
- Persistence layer with versioned storage and automatic expiry
- Stale timeout and eviction policy consistent across all vessel types

### Documentation

- **Installation Guide** ([docs/installation.md](docs/installation.md))
- **Configuration Guide** ([docs/configuration.md](docs/configuration.md))
- **Usage Guide** ([docs/usage.md](docs/usage.md)) with Lovelace examples
- **Troubleshooting Guide** ([docs/troubleshooting.md](docs/troubleshooting.md))
- **Architecture Documentation** ([docs/architecture.md](docs/architecture.md))
- **Development Guide** ([docs/development.md](docs/development.md))
- **Testing Guide** ([docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)) — NEW
- **Phase Documentation** organized in `/docs` folder for reference

### Housekeeping

- Moved all development phase documentation to `/docs/PHASE_*.md`
- Moved project status and documentation indices to `/docs`
- Repository root cleaned up (only essential files remain)
- Created unified testing guide replacing individual phase test guides
- Updated all cross-references in documentation

---

## v1.1.0 (Earlier Release)

Previous features and improvements. See git history for details.

---

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
- **Phase 4: Maritime map and trails** (REQ-002, REQ-003, REQ-010)
  - Real-time WebSocket API for bounded dashboard transport:
    * Entry-scoped subscriptions with live coordinator updates
    * Paginated snapshots (max 100 vessels per page)
    * Bounded vessel trails with position history (max 50 points)
    * Stale detection and watched-vessel marking
    * Explicit error handling and full cleanup on disconnect
  - Custom Leaflet-based maritime tracker card for Lovelace:
    * Real-time vessel markers updated via WebSocket
    * Heading/course indicators for each vessel
    * Bounded position trails (polylines) with gap preservation
    * Entity picker to switch between tracked areas
    * Details pane showing vessel MMSI, name, status, speed, destination, ETA
    * Watched vessel highlighting and stale state indication
    * Map controls (fit all vessels, reset to default view)
    * Area outline visualization (circle/rectangle placeholder)
    * Mobile-responsive layout (side panels on desktop, stacked on mobile)
    * Optional port board panel (prepared for Phase 5)

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
- WebSocket snapshots are bounded to prevent large payload accumulation;
  subscriptions are fully cleaned up on card close or entry unload.

### Verification

- Phase 1, 2, 3, and 4 focused tests cover snapshot use and fallback, transition
  ordering and continuity, storage restore/removal, entry isolation, watchlist
  configuration/validation, state management, entity resolution, filter
  independence, persistence, and no-additional-requests efficiency.
- Phase 4 WebSocket API tests: snapshot building, pagination, stale detection,
  trail truncation, authentication, entry isolation, error handling, and cleanup.
- Phase 4 frontend test placeholders prepared for browser automation validation.
- Close-out validation: **Phase 1/2/3 tests passed** + **Phase 4 WebSocket API
  tests passed**; Ruff, mypy, and Python compilation checks passed.
