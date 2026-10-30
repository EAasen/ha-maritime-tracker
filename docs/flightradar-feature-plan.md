# Implementation Plan: Flightradar-inspired Maritime Features

Date: 2026-10-30  
Status: Proposed implementation plan; no runtime changes implemented  
Local baseline: `36c7cd3e42eef5731b7190dcee930457d37e5c6c`

## Summary and approved scope

Implement four features in small, independently reviewable releases:

1. A maritime dashboard map with vessel trails.
2. A persistent MMSI watchlist that follows vessels outside the local area.
3. An observed port-call board.
4. AIS status-transition events for automations.

The user confirmed all four features, BarentsWatch coverage only, and observed
arrivals/departures with reported AIS ETA rather than promised schedules.
This confirmation is the requirements input for this plan; no separate formal
feature specification or project constitution was supplied.

This is a functional adaptation, not a copy of the Flightradar24 implementation.
Do not introduce a new AIS provider, worldwide tracking, scraped schedules,
airport-style cancellation/delay metrics, or a popularity ranking.
Polling controls and recent-entered/exited sensors are possible later work, not
part of these four approved features.

## Evidence and technical context

Reference: [Flightradar24 README at the reviewed revision](https://github.com/AlexandrErohin/home-assistant-flightradar24/blob/077be7c23a86586b506f3b638226ee87d6f28108/README.md).
It documents map tracks, additional tracking outside the area, airport boards,
and lifecycle events. REA MCP was unavailable; the comparison used public
documentation and local source inspection, not a REA-generated report.

| Surface | Existing behavior and implication |
|---|---|
| [Kystverket client](../custom_components/marinetraffic_tracker/kystverket_client.py) | Fetches `/v1/latest/combined` and applies area filtering locally. Refactor to reuse a single parsed snapshot for area, watchlist, and ports; no per-MMSI HTTP requests. |
| [Coordinator](../custom_components/marinetraffic_tracker/coordinator.py) | Keeps area state, anchor exclusions, 20-point histories, and in-memory statistics. Existing exit events are stale-timeout eviction, not confirmed boundary crossings. |
| [Sensors](../custom_components/marinetraffic_tracker/sensor.py) | Count sensor already has structured vessel summaries; per-vessel history is available only through individual vessel entities. Preserve existing attribute shapes. |
| [Geolocation markers](../custom_components/marinetraffic_tracker/geo_location.py) | Existing map path is functional and must remain available. No custom card or track overlay exists. Absence of a unique ID is not a recorder-exclusion mechanism. |
| [Configuration](../custom_components/marinetraffic_tracker/config_flow.py) | Options currently cover polling, filters, logging, and map-zone visibility. Add opt-in watchlist and port management without changing existing area identity. |
| [Entity base](../custom_components/marinetraffic_tracker/entity.py) | Vessel devices and entity IDs are entry-scoped. Extend data lookup without creating duplicate identities for an area vessel also on the watchlist. |

Use Python 3.12+, Home Assistant config entries and coordinator patterns,
`aiohttp`, `voluptuous`, and existing geometry helpers. Maintain the declared
Home Assistant minimum, currently 2025.1.0; feature-gate optional frontend
registration if an API is unavailable rather than breaking integration setup.

New frontend code should use a small JavaScript custom element and a pinned,
locally packaged map dependency, provisionally Leaflet. Confirm its license,
asset packaging, and compatibility before implementation. Do not depend on
private Home Assistant map internals or load executable code from a CDN.

### Compatibility and guideline check

Apply [contributor conventions](../CONTRIBUTING.md) and the
[development guide](development.md): typed production Python, existing style,
unit tests for new behavior, and existing lint/type/HA validation gates.
No framework migration guideline applies to this additive feature work.

Required invariants:

- Keep the integration domain, existing entry IDs, entity unique IDs, area
  counts, anchor/type filters, event names, and default polling floors.
- New features are opt-in. Existing installations must work unchanged.
- Keep credentials out of events, frontend messages, and diagnostics.
- Surface fetch, storage, registration, and validation errors explicitly.
- Maintain bounded state, clean listener removal, and entry isolation.
- Never infer departure, status change, or arrival solely from missing data.

## Requirements

| ID | Requirement and acceptance condition |
|---|---|
| REQ-001 | One successful source snapshot feeds all enabled views per entry and poll. Existing client wrappers and area behavior remain compatible. |
| REQ-002 | Optional map shows vessel markers, heading/course when known, details, and bounded trails; existing built-in map usage remains functional. |
| REQ-003 | Map draws the actual radius or rectangle without requiring a synthetic HA zone; supports selection, fit/reset, mobile interaction, and unavailable/stale states. |
| REQ-004 | Users can add/remove unique nine-digit MMSIs through options and retain the watchlist across reload/restart; invalid values produce a form error. |
| REQ-005 | Watchlisted vessels remain observable outside the local area within feed coverage, without altering area counts/statistics or duplicating vessel entities. |
| REQ-006 | Emit a structured AIS status-change event exactly once per confirmed valid transition; first observation, duplicates, unknown statuses, and outages must not create fabricated transitions. |
| REQ-007 | Optional named port geofences produce confirmed observed arrivals/departures, distinct from stale eviction and existing legacy events. |
| REQ-008 | Port board shows present vessels and bounded recent port calls, with timestamp provenance and explicitly unverified reported AIS ETA/destination. |
| REQ-009 | Persist bounded port-call records and valid transition baselines across reload/restart; resumption must not replay calls or infer movement during a coverage gap. |
| REQ-010 | Preserve entry isolation, existing contracts, and disabled-by-default entity policy; document limitations and validate every new user journey before release. |

## Proposed behavioral decisions

These are explicit implementation defaults for review, not new claims about AIS.
Do not silently expand them during implementation.

### Shared observation and freshness rules

Separate source-message time from local fetch time. A successful poll may return
the same old AIS message repeatedly; that must not create new history points,
confirm geofence crossings, or keep a watched vessel indefinitely fresh.
Retain local reception time for diagnostics. Normalize source timestamps once.

Only sufficiently fresh valid observations drive the new transition logic.
Use the configured stale timeout as the initial freshness limit. Unknown or
unparseable source time is displayed as uncertain and cannot confirm port calls.
Handle out-of-order messages and implausible future timestamps explicitly.
Do not reinterpret existing `last_seen` or legacy area-event behavior in this
release; expose additional source-time/freshness fields for the new features.

### Watchlist

- Store the configured MMSIs in entry options, not in observation storage.
- Start with a maximum of 100 MMSIs per entry; reject excess entries explicitly.
- Selected MMSIs bypass area/type/anchor display filters only in the watchlist
  view; area views and statistics retain their existing filters.
- An aggregate watchlist sensor reports fresh matches; its bounded attributes
  distinguish fresh, stale, and not-observed selections. No match means
  "not observed in this feed", never "does not exist".
- Reuse existing per-vessel sensor/tracker identity and defaults. A shared
  resolver reads area or watchlist data; do not broaden `coordinator.data`
  because it currently defines the area count.
- A watched vessel's stale state must not expose old coordinates as live.
  Keep last-known position and its timestamp clearly labeled where useful.

### Status events

Add `marinetraffic_vessel_status_changed` with `entry_id`, MMSI, name,
old/new status, source-message timestamp, observation time, source, and position.
Observe the union of relevant area, watchlist, and port vessels before display
exclusions; emit only once per vessel and transition per entry.

First observation establishes a baseline. Duplicate/out-of-order observations
do nothing. An unknown status or a stale/outage interval invalidates continuity:
the next valid observation re-establishes the baseline without inventing a
transition. Persisted state only permits comparison when continuity remains
valid. AIS status is reported by the vessel; it is not proof of berth activity.
Expire baselines after the configured stale timeout and cap them at 2,000
vessels per entry. Evict oldest baselines with an explicit warning if necessary;
an evicted vessel's next observation establishes a baseline, not a transition.

### Port calls

- Manage up to 10 named circular port geofences per entry using location/radius
  selectors and stable generated port IDs. Reject invalid or duplicate IDs,
  and require a port radius greater than the 100 m hysteresis width.
- Ports may be outside the main tracking area but must be within feed coverage.
- Use a 100 m boundary hysteresis band. Confirm a change with two fresh,
  distinct source observations beyond the appropriate boundary. Exact boundary
  and band observations retain the prior state.
- First observation inside establishes "present", not an arrival. Missing,
  stale, or failed polls never mean departure; after a gap, establish a new
  baseline rather than inventing a crossing.
- Emit `marinetraffic_port_arrived` and `marinetraffic_port_departed` with entry,
  port, vessel, last outside/inside times, confirmation time, and source.
  Crossing time is an observation interval, not an exact known time.
- Port membership is geometric and independent of anchored/moored map filters.
  Overlapping ports may each report membership, identified by port ID.
- Board shows "present", "recent observed arrivals", and "recent observed
  departures"; AIS destination and ETA are reported/unverified. Do not label
  an ETA as a scheduled arrival, infer a delay, or map destination free text
  to a port as if it were authoritative.
- Keep at most 100 call records per port and seven days of records, whichever
  is smaller. Retain up to 1,000 per-port vessel baselines; evict inactive ones
  first, then oldest with an explicit warning. Eviction means the next
  observation is a new baseline, never a synthetic call.
- Use versioned Home Assistant storage per entry, debounced writes, orderly
  unload flush, and storage removal on entry deletion. Do not repurpose CSV logs
  or silently claim existing in-memory statistics survive restarts.

### Map data and resource bounds

Do not attach all track histories to the count sensor: that would amplify
recorder writes and large state attributes. Register authenticated Home
Assistant WebSocket commands for on-demand map data, scoped by config entry.

Return compact current marker snapshots and actual area geometry. Subscribe
only while the card is connected; request histories for selected vessels.
Initial limits: 500 markers per response, continuation/pagination for larger
sets, up to 10 selected trails, and 20 points per trail. Report truncation
explicitly. Coalesce live notifications to at most one per second per card.
Frontend display filters never change backend counts.

Use the existing area sensor to select a config entry; resolve its entry server
side. An entry selection must not depend on a hardcoded entity name or expose
credentials. Unknown entry, malformed commands, or unavailable data return
explicit errors/status. Clean subscriptions on disconnect/unload.

The first card supports OSM with attribution, heading-oriented markers, vessel
type styling, selected details, km/nautical miles, and knots. Keep tracks broken
across gaps; never draw a straight line as if missing coverage were observed.
Area and watchlist layers are labeled distinctly; port details follow in the
port-board release. Additional basemaps and complex animation are deferred.

## Implementation steps and inline tasks

Paths below are relative to the repository root. New files are proposed, not
existing implementation evidence. Each task includes its prerequisite IDs.

### Phase 1: Shared observations and compatibility

**P1.1 - Shared feed snapshot and freshness (REQ-001, REQ-010).**
Use the current client, coordinator, data model, and geometry helpers.

- [x] T001 [Plan:1.1] Refactor `custom_components/marinetraffic_tracker/kystverket_client.py` to expose one parsed full-snapshot operation; preserve `get_vessels_in_radius` and `get_vessels_in_box` wrappers. Add normalized observation metadata in `client.py` without changing legacy `last_seen`. Prerequisites: none.
- [x] T002 [Plan:1.1] Update `custom_components/marinetraffic_tracker/coordinator.py` to partition one Kystverket snapshot into area/relevant observations using `geo_filter.py`, retaining current legacy-client paths, failure/auth behavior, filtering, and area results. Prerequisites: T001.
- [x] T003 [Plan:1.1] Extend snapshot/coordinator tests with wrapper behavior, one-fetch-per-poll, old/missing/future source times, fallback, and unchanged area results and legacy behavior. Prerequisites: T002.

Gate: same snapshots produce identical legacy area results; a poll makes one
logical snapshot fetch regardless of enabled consumers, excluding retries. ✅

### Phase 2: Status-transition automations

**P2.1 - Reliable status transitions (REQ-006, REQ-009, REQ-010).**
Consume normalized observations, not filtered map output.

- [x] T004 [Plan:2.1] Add `custom_components/marinetraffic_tracker/vessel_events.py` for bounded status baselines and transition decisions; add the event constant in `const.py`, reusing the existing vessel payload fields where compatible. Prerequisites: T003.
- [x] T005 [Plan:2.1] Add `custom_components/marinetraffic_tracker/storage.py` for versioned per-entry baselines and wire restore, debounced save, unload flush, and entry-delete cleanup through `__init__.py`; invoke transitions once from `coordinator.py`. Prerequisites: T004.
- [x] T006 [Plan:2.1] Add `tests/test_vessel_events.py` and `tests/test_storage.py`; cover duplicate/out-of-order messages, unknown status, stale gaps, restart continuity, storage failures, and two-entry isolation. Prerequisites: T005.

Gate: repeated snapshots generate zero duplicate status events; first sighting
and first sighting after a gap generate no transition. Legacy events remain. ✅

### Phase 3: Persistent vessel watchlist

**P3.1 - Options, separate watchlist state, and entities
(REQ-004, REQ-005, REQ-010).**
Use the full snapshot without extra network calls.

- [ ] T007 [Plan:3.1] Add watchlist options and strict validation in `custom_components/marinetraffic_tracker/config_flow.py`, `const.py`, `strings.json`, and `translations/en.json`; preserve area unique-ID generation and all prior options on save. Prerequisites: T003.
- [ ] T008 [Plan:3.1] Add separate watchlist state and a shared vessel resolver in `custom_components/marinetraffic_tracker/coordinator.py`; bound watched history and retain freshness/unknown distinctions without adding watchlisted vessels to area data/statistics. Prerequisites: T007.
- [ ] T009 [Plan:3.1] Add the aggregate watchlist sensor in `custom_components/marinetraffic_tracker/sensor.py`; update `entity.py` and `device_tracker.py` to resolve watched vessels and deduplicate existing vessel identities while preserving disabled defaults. Prerequisites: T008.
- [ ] T010 [Plan:3.1] Extend `tests/test_config_flow.py`, `tests/test_translations.py`, `tests/test_sensor_attributes.py`, `tests/test_entity_registry_defaults.py`, and `tests/test_vessel_device_info.py`; add `tests/test_watchlist.py` for outside-area continuity, filter independence, removal, persistence, no-match, stale data, and no additional requests. Prerequisites: T009.

Gate: watching an out-of-area MMSI changes the watchlist only, preserves its
entity identity on entering/leaving the area, and does not increase fetch count.
Phases 2 and 3 can be implemented independently after Phase 1, but changes to
shared coordinator/lifecycle files must be integrated serially.

### Phase 4: Maritime map and trails

**P4.1 - Bounded live dashboard transport (REQ-002, REQ-003, REQ-010).**
Keep large history payloads out of recorder-backed state.

- [ ] T011 [Plan:4.1] Add `custom_components/marinetraffic_tracker/websocket_api.py` with authenticated entry resolution, compact paginated snapshots, bounded selected-history requests, live invalidations, and explicit error responses. Register commands once and clean per-entry subscriptions through `__init__.py`. Prerequisites: T005, T010.
- [ ] T012 [Plan:4.1] Add `tests/test_websocket_api.py` for authentication, entry isolation, malformed requests, pagination/truncation, trail limits, stale handling, coalescing, and unsubscribe/unload cleanup. Prerequisites: T011.

**P4.2 - Frontend card and installation (REQ-002, REQ-003, REQ-010).**
Use the reviewed public feature behavior, not upstream source copying.

- [ ] T013 [Plan:4.2] Add `custom_components/marinetraffic_tracker/frontend/__init__.py` and `frontend/maritime-tracker-card.js`; package pinned map assets with required notices, implement one-time HA-compatible static/resource registration, and include all assets in release packaging. Add frontend dependency manifest/lockfile and build tooling only if required by the selected library. Prerequisites: T012.
- [ ] T014 [Plan:4.2] Implement the card's entity picker, area/watchlist layers, heading/course markers, actual area outline, selection/details, selected trails with gaps, fit/reset, unavailable states, units, and mobile/keyboard interaction in `custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js`. Prerequisites: T013.
- [ ] T015 [Plan:4.2] Add frontend tests under `tests/frontend/` and wire a focused frontend job into `.github/workflows/tests.yml`; verify fresh install, two entries, reconnect, reload, missing tiles, packaged assets, and lowest/current supported HA frontend compatibility. Prerequisites: T014.

Gate: existing built-in map YAML is unchanged; custom map draws circle/rectangle
without requiring a synthetic zone; all subscriptions end when the card closes.

### Phase 5: Observed port-call board

**P5.1 - Port configuration and confirmed calls
(REQ-007, REQ-009, REQ-010).**
Use fresh observations, existing radius geometry, and versioned storage.

- [ ] T016 [Plan:5.1] Extend `custom_components/marinetraffic_tracker/config_flow.py`, `const.py`, `strings.json`, and `translations/en.json` with an optional port-management submenu for adding, editing, and deleting stable-ID named circles; keep watchlist and existing settings intact. Prerequisites: T010.
- [ ] T017 [Plan:5.1] Add `custom_components/marinetraffic_tracker/port_calls.py` with the confirmation/hysteresis state machine, gap handling, limits, and event decisions; connect relevant snapshot observations in `coordinator.py` and bounded persistence in `storage.py`. Prerequisites: T006, T016.
- [ ] T018 [Plan:5.1] Add `tests/test_port_calls.py` and extend `tests/test_storage.py` and `tests/test_config_flow.py` for jitter, same-message repeats, exact boundaries, first-inside, coverage loss, overlaps, limits, restart, port edits/removal, retention, and storage version handling. Prerequisites: T017.

Editing a port's geometry must reset its membership baseline; deleting a port
must remove its stored state and entities without emitting vessel departures.

**P5.2 - Board sensors and dashboard
(REQ-008, REQ-009, REQ-010).**
Distinguish observed calls from unverified reported voyage data.

- [ ] T019 [Plan:5.2] Add entry/port-scoped present, recent-arrival, and recent-departure sensors in `custom_components/marinetraffic_tracker/sensor.py`, with bounded rows, stable IDs, provenance, uncertainty, and clear availability; add translation keys and port deletion cleanup. Prerequisites: T018.
- [ ] T020 [Plan:5.2] Add port overlays and an optional port board to `custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js`; extend `websocket_api.py` only for data not suitable for bounded sensor rows. Label AIS ETA/destination as reported, not scheduled. Prerequisites: T015, T019.
- [ ] T021 [Plan:5.2] Extend `tests/test_sensor_attributes.py`, `tests/test_websocket_api.py`, and `tests/frontend/` to verify board schemas, row limits, empty/unavailable states, unknown ETA, same-MMSI repeated calls, port deletion, and no fabricated delays or schedules. Prerequisites: T020.

Gate: two distinct fresh positions confirming a boundary transition create
exactly one call; outage, stale eviction, restart, and port edits do not.

### Phase 6: Documentation and release readiness

**P6.1 - User guidance and final regression gates (REQ-010).**

- [ ] T022 [Plan:6.1] Update `README.md`, `docs/usage.md`, `docs/configuration.md`, `docs/architecture.md`, `docs/troubleshooting.md`, and `docs/development.md` with the new options, event payloads, watchlist coverage, port uncertainty, map setup, storage limits, and frontend checks; correct directly related stale examples, especially undocumented existing area events and recorder assumptions. Prerequisites: T006, T010, T015, T021.
- [ ] T023 [Plan:6.1] Run targeted tests per phase, then the existing complete Python suite, lint/type checks, HA version matrix, HASSfest, frontend checks, and release-asset installation check. Record results with the release PR; increment `custom_components/marinetraffic_tracker/manifest.json` only when preparing the appropriate feature release. Prerequisites: T022.

Recommended release slices: Phase 1 + Phase 2; then Phase 3; then Phase 4;
then Phase 5. Each slice must include its relevant documentation, tests, and
compatibility gates rather than waiting until the final slice.

## Proposed project structure

Existing files are extended unless listed as new:

```text
custom_components/marinetraffic_tracker/
  kystverket_client.py        shared snapshot, compatible filtered wrappers
  coordinator.py             separate area/watchlist/port projections
  client.py                  source observation metadata
  vessel_events.py           new: status transition decisions
  port_calls.py              new: port membership and observed calls
  storage.py                 new: versioned bounded runtime state
  websocket_api.py           new: authenticated bounded dashboard transport
  frontend/
    __init__.py              new: static assets/resource registration
    maritime-tracker-card.js  new: maritime map and optional port board
    vendor/                  new: pinned map assets and license notices
tests/
  test_vessel_events.py       new
  test_storage.py             new
  test_watchlist.py           new
  test_websocket_api.py       new
  test_port_calls.py          new
  frontend/                  new: card and browser checks
```

Do not introduce a generic provider framework, arbitrary polygons, a database
server, or an external backend for these features.

## Validation and release criteria

This is a plan-only change; do not install dependencies, implement features, or
run the integration against live credentials while preparing this document.
Implementation must add tests as required by the repository development guide.

### Automated validation

Use existing Python commands from the contributor guide, with focused selectors
first and full checks at release boundaries:

```powershell
pytest tests -v
ruff check custom_components tests
ruff format --check custom_components tests
mypy custom_components --ignore-missing-imports
```

Retain the existing CI coverage floor of 80%, HASSfest, and supported HA matrix.
Add frontend test/build commands only with the frontend tooling introduced by
T013/T015; document the exact selected commands then. Do not invent a currently
nonexistent npm script or treat missing browser validation as a pass.

Use deterministic synthetic AIS sequences, a frozen clock, and mocked HTTP.
Cover matching area/watchlist MMSIs, two config entries, stale and out-of-order
source messages, anchor exclusions, and stream gaps. No real credentials or
live-provider dependency in automated tests.

### User journeys

1. Existing user upgrades with all new features off: counts, legacy events,
   entities, and built-in map behave as before.
2. User adds an MMSI, sees it outside the area, restarts HA, and removes it:
   selection survives restart, area totals stay unchanged, no duplicate entity.
3. Card displays marker updates and selected trails, changes entry, disconnects,
   and reconnects: no cross-entry data, stale live markers, or orphan listeners.
4. Vessel changes valid AIS status: one event with old/new values; repeat
   snapshots, outages, and first sighting generate none.
5. Vessel crosses a configured port boundary and later departs: two fresh
   observations confirm each call; boundary jitter and missed messages do not.
6. User reloads, edits, or deletes a port: retained history respects bounds,
   baselines are reset where necessary, and no false calls are emitted.

Browser checks require a test HA instance, Node/browser tooling, desktop and
mobile viewports, and a declared test hardware/browser baseline. If unavailable,
record the frontend gate as blocked; Python tests alone do not prove map UX.
Use a local tile stub for deterministic tests; separately verify live tile
attribution and failure handling without sharing vessel data with tile servers.
Map tile requests inherently disclose viewport information; document that.

### Proposed measurable budgets

- Zero additional logical AIS fetches for enabling watchlist, ports, or cards.
- At most 100 watched MMSIs, 10 ports, 100 call records per port, and seven-day
  port history retention; at most 1,000 vessel baselines per port.
- At most 20 history points per vessel; at most 500 markers per map response
  and 10 selected trails per card, with explicit pagination/truncation.
- At most one map notification per second per connected card.
- Synthetic 500-marker fixture: display an incoming update within one second
  and respond to selection within 200 ms on the declared desktop baseline.
  Measure after receipt, excluding upstream polling and tile/network latency.
- Ten repeated card connect/disconnect and entry reload cycles leave no growing
  subscription count. State/storage counts stay within their specified bounds.

Tune budgets only through an explicit plan amendment supported by measurements.

## Risks and mitigation

| Risk | Mitigation / release gate |
|---|---|
| AIS is incomplete or repeated old snapshots look live | Distinguish source time, reception time, stale state, and unknown coverage. |
| Port board is mistaken for a timetable | Use observed-call terminology and unverified AIS ETA labels throughout. |
| Changes break area counts or legacy events | Separate projections and preserve legacy event contracts with regression tests. |
| New statuses fire on restart or after gaps | Continuity-aware bounded baselines, restore rules, and deterministic replay tests. |
| Memory, recorder, or websocket payload growth | Bounded state and selected histories over authenticated on-demand transport. |
| HA frontend APIs vary across supported releases | Validate lowest/current supported versions; explicit optional-card capability errors. |
| External map assets/tiles introduce packaging or privacy issues | Local pinned executable assets, license notices, tile attribution and documented viewport disclosure. |
| Storage failure or incompatible schema | Visible diagnostics and deliberate version handling; no silent successful restore/reset. |
| Position-only crossing inference is overconfident | Hysteresis, fresh distinct observations, observation intervals, and baseline reset after gaps. |

## Requirement mapping

Evidence paths are implementation targets, not claims that features exist.

| REQ ID | Description | Plan items | Planned implementation evidence |
|---|---|---|---|
| REQ-001 | Shared feed snapshot | P1.1 | `kystverket_client.py`, `coordinator.py`; T001-T003 |
| REQ-002 | Markers, details, selected trails | P4.1, P4.2 | `websocket_api.py`, frontend card; T011-T015 |
| REQ-003 | True area outline and usable map states | P4.1, P4.2 | Frontend card, frontend checks; T011-T015 |
| REQ-004 | Persistent validated MMSI options | P3.1 | `config_flow.py`, translations; T007, T010 |
| REQ-005 | Out-of-area watchlist without count/identity changes | P3.1 | Coordinator/resolver, sensor/tracker; T008-T010 |
| REQ-006 | Confirmed status events | P2.1 | `vessel_events.py`, coordinator; T004-T006 |
| REQ-007 | Named geofences and observed calls | P5.1 | `config_flow.py`, `port_calls.py`; T016-T018 |
| REQ-008 | Port board and reported voyage data | P5.2 | Port sensors and card; T019-T021 |
| REQ-009 | Bounded persistence without replay | P2.1, P5.1, P5.2 | `storage.py`, transition/call logic; T005-T006, T017-T021 |
| REQ-010 | Compatibility, isolation, limits, guidance | P1.1, P2.1, P3.1, P4.1, P4.2, P5.1, P5.2, P6.1 | Regression checks and user/developer documentation; T001-T023 |

Coverage: 10 requirements, 8 plan items, 23 tasks. No approved feature is
deferred beyond this plan. No runtime implementation is authorized by the
creation of this document; the next action is review, then Phase 1.
