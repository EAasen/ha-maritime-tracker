# Norwegian Maritime Tracker - Feature Backlog

**Last Updated:** 2026-10-30  
**Status:** Phase 5.1 Complete, Phase 5.2 Ready for Sprint Planning

---

## 📋 Backlog Organization

This document tracks:
1. **Current Phase (Phase 5.2)** — Next sprint items
2. **Upcoming Phases (5.2, 6, 7+)** — Planned features by phase
3. **Future Enhancements** — Nice-to-have features for future consideration
4. **Community Suggestions** — Potential user-requested features

---

## 🔄 Phase 5.2: Port Sensors & Board UI

**Status:** ⏳ **Ready for Implementation**  
**Priority:** P0 (High - Completes Phase 5 core deliverable)  
**Estimated Effort:** 10–15 hours  
**Dependencies:** Phase 5.1 (✅ Complete)

Phase 5.2 transforms port call data into actionable sensors and user-facing UI components.

---

### T019: Port Call Sensors

**Status:** ⏳ Pending  
**Priority:** P0  
**Effort:** 4–5 hours  
**Owner:** TBD

#### Description
Extend the sensor platform to expose port call data as Home Assistant sensor entities. Create three sensor types per configured port for monitoring vessel activity.

#### Requirements

##### R-5.2.1: Port Present Sensor
- **Entity ID Pattern:** `sensor.<entry>_port_<port_id>_present`
- **State:** Integer count of vessels currently inside the port's geofence
- **Attributes:**
  - `vessel_list`: List of vessels inside (format: `MMSI: Name`)
  - `vessel_details`: Structured array with extended info per vessel:
    - `mmsi`: Vessel MMSI
    - `name`: Vessel name
    - `inside_duration_minutes`: Minutes since vessel entered
    - `speed_knots`: Current speed
    - `heading`: Current heading (degrees)
    - `destination`: Reported destination (if available)
  - `last_update`: Timestamp of last change
  - `port_name`: Name of the port
  - `port_radius_km`: Geofence radius

- **Availability:** Unavailable when coordinator is unavailable
- **Icon:** `mdi:ferry`
- **Unit of Measurement:** `vessels`

##### R-5.2.2: Recent Arrivals Sensor
- **Entity ID Pattern:** `sensor.<entry>_port_<port_id>_arrivals`
- **State:** Integer count of vessels that arrived in last 24 hours
- **Attributes:**
  - `arrivals`: List of recent arrivals (format: `MMSI: Name (HH:MM)`)
  - `arrival_details`: Structured array with:
    - `mmsi`: Vessel MMSI
    - `name`: Vessel name
    - `arrival_time`: ISO timestamp
    - `arrival_local_time`: Human-readable local time
    - `reported_eta`: Reported ETA (if available)
    - `reported_destination`: Reported destination (if available)
    - `speed_at_arrival`: Speed when entering geofence
  - `last_update`: Timestamp of last arrival
  - `port_name`: Name of the port
  - `bounded_retention`: Indication if limited to last 24h

- **Availability:** Unavailable when coordinator is unavailable
- **Icon:** `mdi:ferry-arriving`
- **Unit of Measurement:** `vessels`

##### R-5.2.3: Recent Departures Sensor
- **Entity ID Pattern:** `sensor.<entry>_port_<port_id>_departures`
- **State:** Integer count of vessels that departed in last 24 hours
- **Attributes:**
  - `departures`: List of recent departures (format: `MMSI: Name (HH:MM)`)
  - `departure_details`: Structured array with:
    - `mmsi`: Vessel MMSI
    - `name`: Vessel name
    - `departure_time`: ISO timestamp
    - `departure_local_time`: Human-readable local time
    - `inside_duration_minutes`: Total time inside geofence
    - `final_speed`: Speed when exiting geofence
    - `reported_destination`: Reported destination at departure
  - `last_update`: Timestamp of last departure
  - `port_name`: Name of the port
  - `bounded_retention`: Indication if limited to last 24h

- **Availability:** Unavailable when coordinator is unavailable
- **Icon:** `mdi:ferry-departing`
- **Unit of Measurement:** `vessels`

#### Implementation Details

**File:** `custom_components/marinetraffic_tracker/sensor.py` (extend existing)

**Key Classes:**
```python
class PortPresentEntity(MarineTrafficEntity, SensorEntity):
    """Port present sensor - count and list of vessels inside."""
    
class PortArrivalsEntity(MarineTrafficEntity, SensorEntity):
    """Port arrivals sensor - count and list of recent arrivals."""
    
class PortDeparturesEntity(MarineTrafficEntity, SensorEntity):
    """Port departures sensor - count and list of recent departures."""
```

**Lifecycle:**
- Sensors created when port configuration is loaded (coordinator init)
- Sensors updated on each coordinator cycle (post port-check)
- Sensors auto-removed when port is deleted from config
- State persisted in Home Assistant entity registry

**Data Sources:**
- `coordinator._port_storage.async_get_recent_calls(port_id, hours=24)`
- `coordinator._port_baselines[port_id]` for present vessels
- Coordinator's main `_observations` dict for vessel details

**Attribute Limits (Bounded Retention):**
- `vessel_list`: Max 50 vessels (oldest removed first)
- `arrival_details`: Max 50 entries (oldest removed first)
- `departure_details`: Max 50 entries (oldest removed first)
- Time window: 24 hours (configurable per port in Phase 6)

#### Acceptance Criteria
- [ ] Three sensor entities created per configured port
- [ ] States reflect accurate vessel counts
- [ ] Attributes provide structured vessel details
- [ ] Sensors unavailable when coordinator unavailable
- [ ] Sensors created/destroyed with port config changes
- [ ] Bounded retention enforced (max 50 per sensor)
- [ ] Test coverage ≥85% for sensor logic

#### Testing Strategy
Extend `tests/test_sensor_attributes.py`:
- Mock port configurations and baselines
- Mock recent calls from storage
- Assert sensor states and attributes match expected values
- Test sensor lifecycle (create/update/delete)
- Test availability when coordinator unavailable

---

### T020: Port Board Frontend Component

**Status:** ⏳ Pending  
**Priority:** P0  
**Effort:** 6–8 hours  
**Owner:** TBD

#### Description
Extend the maritime-tracker-card.js frontend component with a collapsible port board panel showing real-time vessel activity at configured ports.

#### Requirements

##### R-5.2.4: Port Board Panel UI
- **Display Mode:** Collapsible panel below main map (or side panel on desktop)
- **Expand/Collapse:** Toggles via card configuration (`show_port_board: true/false`)
- **Header:** Shows total active ports and summary counts

##### R-5.2.5: Port Board Layout
Three-section table layout per port:

**Section 1: Currently Present**
- Table columns: MMSI | Name | Status | Speed | Duration | Heading | Destination
- Data source: Port present sensor state + attributes
- Empty state: "No vessels currently inside"
- Sorted by: Inside duration (longest first)

**Section 2: Recent Arrivals (24h)**
- Table columns: MMSI | Name | Arrival Time | Reported ETA | Duration Inside | Speed at Arrival
- Data source: Port arrivals sensor attributes
- Empty state: "No arrivals in last 24 hours"
- Sorted by: Arrival time (newest first)
- Label: "(Reported)" next to ETA and destination fields

**Section 3: Recent Departures (24h)**
- Table columns: MMSI | Name | Departure Time | Duration Inside | Final Speed | Reported Destination
- Data source: Port departures sensor attributes
- Empty state: "No departures in last 24 hours"
- Sorted by: Departure time (newest first)
- Label: "(Reported)" next to destination fields

##### R-5.2.6: Port Board Map Integration
- **Geofence Circles:** Render configured port geofences on Leaflet map
  - Circle color: Light blue (#4444FF, 30% opacity)
  - Border: Darker blue (#0000CC, 60% opacity)
  - Label: Port name at circle center
  - Radius: Drawn to scale matching GIS coordinates
  - Interactive: Highlight on hover, zoom to port on click

- **Vessel Markers:** Highlight vessels currently inside any port
  - Border color: Golden/orange (#FFA500, vs. default gray)
  - Z-index: Slightly above non-port vessels
  - Tooltip: Add "In Port: [Port Name]" line

##### R-5.2.7: Port Board Interactivity
- **Clickable Rows:** Each vessel row links to existing vessel detail view
  - Click MMSI → Opens vessel detail panel
  - Click Name → Same behavior as MMSI
  
- **Port Selection Dropdown:** Filter board to show one port at a time (optional)
  - Default: Show all ports
  - Dropdown: "All Ports" + per-port entries
  - Updates URL hash for deep-linking

- **Refresh Control:** Manual refresh button
  - Triggers coordinator update cycle
  - Shows last-refresh timestamp

##### R-5.2.8: Responsive Design
- **Desktop (1024px+):** 
  - Map takes ~70% of width, board panel on right side (30%)
  - Board panel: Scrollable, fixed height
  
- **Tablet (768px–1024px):**
  - Map full width, board panel below (collapsed by default)
  - Swipe to collapse/expand
  
- **Mobile (<768px):**
  - Map full width, board minimized (icon only)
  - Board icon in top toolbar
  - Tap to open modal dialog with board content

##### R-5.2.9: Configuration Extension
Extend card schema in `maritime-tracker-card.yaml`:
```yaml
show_port_board:
  type: boolean
  default: false
  description: "Show port board panel with vessel activity"

port_board_height:
  type: number
  default: 300
  description: "Height of port board panel in pixels (desktop)"

port_board_max_rows:
  type: number
  default: 50
  description: "Maximum rows per section (arrivals, departures)"
```

#### Implementation Details

**File:** `www/community/maritime-tracker-card/maritime-tracker-card.js` (extend existing)

**Key Components:**
```javascript
class PortBoardPanel extends LitElement {
  /**
   * Render port board sections (present, arrivals, departures)
   */
}

class PortGeofenceLayer extends L.Layer {
  /**
   * Render geofence circles on Leaflet map
   */
}

class VesselMarkerHighlight {
  /**
   * Highlight markers for vessels inside ports
   */
}
```

**Data Flow:**
1. Card queries port-board entities (`sensor.*.port_*_{present,arrivals,departures}`)
2. Subscribe to WebSocket updates (existing maritime-tracker-card channel)
3. Render geofences on map load
4. Update sections on entity state changes
5. Handle responsive resizing

**Styling:**
- Use existing maritime-tracker-card theming system
- Light theme: White background, dark text
- Dark theme: Dark gray background, light text
- Port circles: Consistent color scheme
- Empty states: Centered, italicized text

#### Acceptance Criteria
- [ ] Port board panel renders with three sections
- [ ] Geofence circles displayed on map
- [ ] Section data flows from port sensors
- [ ] Clickable vessel rows link to details
- [ ] Responsive layout on mobile/tablet/desktop
- [ ] Card configuration updates extend schema
- [ ] No performance degradation (WebSocket updates <500ms)
- [ ] Empty states display correctly
- [ ] Map circles scale correctly for different port sizes

#### Testing Strategy
- Playwright browser tests for card rendering
- Mock sensor entities with port data
- Test responsive layouts (viewport resizing)
- Test data binding and updates
- Test geofence circle rendering and scale
- Performance profiling (WebSocket update latency)

---

### T021: Port Board Test Suite

**Status:** ⏳ Pending  
**Priority:** P0  
**Effort:** 2–3 hours  
**Owner:** TBD

#### Description
Comprehensive test coverage for port sensors and frontend port board component.

#### Scope

**Backend Tests** (Python/pytest)
- Extend `tests/test_sensor_attributes.py`:
  - Port sensor state calculation
  - Port sensor attribute generation
  - Sensor lifecycle (create/update/delete)
  - Availability when coordinator unavailable
  
- Extend `tests/test_storage.py`:
  - Bounded retention enforcement (max 50 per port)
  - Time window queries (24h window)

**Frontend Tests** (JavaScript/Playwright or Jest)
- Card rendering with port board enabled/disabled
- Geofence circle rendering and scaling
- Section data binding and updates
- Responsive layout tests
- Vessel row clickability
- Empty state display

**Integration Tests**
- Sensor data flows correctly to card
- WebSocket updates propagate to board
- No lag between port call and sensor update

#### Acceptance Criteria
- [ ] Test coverage ≥85% for port sensor logic
- [ ] All sensor lifecycle tests pass
- [ ] Frontend tests cover all sections and layouts
- [ ] Integration tests verify end-to-end data flow
- [ ] Bounded retention tests verify limits enforced
- [ ] Test execution <30 seconds

---

## 🔮 Phase 6: Documentation & Release

**Status:** ⏳ **Planned**  
**Priority:** P1 (High - Enables v1.0 release)  
**Estimated Effort:** 8–12 hours

### T022: Documentation Updates

- **Usage Guide** (`docs/usage.md`)
  - Port configuration walkthrough
  - Port board card setup
  - Automation examples (send notification on vessel arrival, etc.)
  - Screenshots and video walk-through

- **Architecture Documentation** (`docs/architecture.md`)
  - Phase 5 port architecture diagram
  - Port call flow (config → observation → call emission)
  - Storage persistence model
  - Sensor data sources and update cycle

- **API Reference** (New `docs/api.md`)
  - `EVENT_PORT_CALL` event schema
  - Sensor entity naming conventions
  - WebSocket API extensions for port board

- **README.md Updates**
  - Feature overview with Phase 5 port tracking
  - Screenshots of port board
  - Quick-start section
  - Known limitations and planned features

### T023: Regression Test Suite

- Run full `pytest` suite with coverage ≥80%
- Lint checks (`flake8`, `pylint`, `mypy`)
- HASSfest validation
- Manual integration tests with real Home Assistant instance
- Code review checklist

### T024: Release Preparation

- Version bump (v0.9.0 → v1.0.0)
- CHANGELOG updates
- Merge staging branch to main
- GitHub release creation
- HACS registry submission

---

## 🎯 Phase 7: Enhanced Port Features (Future)

**Status:** 💭 **Conceptual**  
**Priority:** P2 (Medium - Post-release features)

### T025: Per-Port Configuration Options

Allow users to customize behavior per port:

- **Time Windows:** Configure arrival/departure retention window per port
  - Default: 24 hours
  - Range: 1 hour – 30 days
  
- **Notification Triggers:** Per-port automation triggers
  - "Notify when specific MMSI enters port"
  - "Alert if vessel stays >X hours"
  - "Warn if vessel departs without expected ETA"

- **Port-Specific Filters:**
  - Only track vessels of certain types (cargo, tanker, etc.)
  - Ignore recreational/small vessels
  - Track only by flag state (Norwegian, international, etc.)

### T026: Port Schedule and Expected Arrivals

- **Scheduled Calls:** Users define expected vessel arrivals
  - Date/time or frequency (daily, weekly, etc.)
  - Expected duration
  - ETA deviation alerts if vessel arrives late/early
  
- **Port Statistics:**
  - Average daily traffic
  - Busiest hours/days
  - Dwell time statistics
  - Type distribution pie chart

### T027: Port Board Historical View

- **Calendar View:** Select date to view historical port activity
  - Shows arrivals/departures for selected date
  - Heatmap of port occupancy
  
- **Activity Timeline:** Scrollable timeline of all vessel events
  - Hover for details
  - Click to filter by vessel

### T028: Multi-Port Comparisons

- **Comparative Dashboard:** View activity across multiple ports side-by-side
  - Charts: Daily traffic, vessel types, dwell times
  - Trends over time (7-day, 30-day, 90-day views)
  
- **Geofence Heatmap:** Show vessel density across all ports

---

## 🚀 Phase 8+: Advanced Maritime Features (Future)

**Status:** 💭 **Conceptual**  
**Priority:** P3 (Low - Long-term vision)

### T029: Route Planning Integration

- **Vessel Route Prediction:**
  - Predict next port based on reported destination
  - Show expected arrival time
  - Alert if vessel deviates from predicted route

- **Corridor Geofences:**
  - Define shipping lanes/corridors
  - Track vessels passing through corridors
  - Corridor-based events (separate from port events)

### T030: Vessel Classification & Smart Routing

- **Vessel Risk Scoring:**
  - Flag vessels with unusual activity patterns
  - Alert on rapid direction changes
  - Detect potential collision courses

- **Shipping Type Analytics:**
  - Group vessels by cargo type
  - Show trade flows (port A → port B patterns)
  - Seasonal traffic patterns

### T031: Weather & Sea State Integration

- **Weather Overlay:**
  - Display wind/wave conditions on map
  - Alert when storms approach ports
  - Link weather events to vessel behavior changes

- **Sea State Correlation:**
  - Correlate vessel speed with sea state
  - Identify vessels seeking shelter

### T032: Multi-Entry Fleet Management

- **Fleet Aggregation:**
  - View all vessels across multiple Home Assistant entries
  - Centralized fleet dashboard
  - Cross-entry alerting rules

- **Custom Entity Grouping:**
  - Define "shipping companies" or "vessel fleets"
  - Aggregate sensors by group
  - Group-level automations

### T033: AIS Data Validation & Quality

- **Data Quality Metrics:**
  - Flag implausible speed/heading changes
  - Detect duplicate/spoofed MMSI
  - Position accuracy confidence scores

- **Source Prioritization:**
  - Weight Kystverket data differently by source quality
  - Handle conflicting reports gracefully

### T034: Historical Data Analytics

- **Data Export:**
  - Export port call history to CSV
  - Export vessel tracks to GeoJSON
  - Bulk data download for offline analysis

- **Statistical Reports:**
  - Generate weekly/monthly traffic reports
  - Vessel count trends
  - Most active vessels/ports

---

## 💡 Community Feature Suggestions

### From User Requests (Future Collection Point)

*This section will be populated as the community provides feedback.*

**Voting Mechanism:**
- Users upvote features in GitHub discussions
- Top 3 monthly features added to next sprint consideration
- Labels: `feature-request`, `high-demand`, `community-voted`

**Example Suggestions (Placeholder):**
- [ ] "SMS/Email alerts on vessel arrivals" (0 votes)
- [ ] "Telegram bot integration" (0 votes)
- [ ] "InfluxDB export for historical analysis" (0 votes)

---

## 📊 Backlog Metrics

| Phase | Status | Tasks | LOC | Tests | Priority |
|-------|--------|-------|-----|-------|----------|
| 1–2   | ✅ Complete | 6 | 2.5K | 100+ | — |
| 3     | ⏳ In Progress | 4 | 1.2K | 30+ | P0 |
| 4     | ✅ Complete | 5 | 4.8K | 40+ | — |
| 5.1   | ✅ Complete | 5 | 11.6K | 21 | — |
| **5.2** | ⏳ **Ready** | **3** | **~8K** | **~25** | **P0** |
| 6     | 📋 Planned | 3 | ~2K | 10+ | P1 |
| 7     | 💭 Conceptual | 10 | ~10K | 30+ | P2 |
| 8+    | 💭 Conceptual | 10+ | ~15K+ | 50+ | P3 |

---

## 🎯 Prioritization Rationale

### Phase 5.2 (P0 - High)
- **Why:** Completes core Phase 5 deliverable (port tracking)
- **Impact:** Enables users to act on port call data
- **Dependency:** Phase 5.1 already complete
- **Estimated Timeline:** 10–15 hours, next sprint

### Phase 6 (P1 - High)
- **Why:** Required for v1.0 release and production readiness
- **Impact:** Documentation, stability, maintainability
- **Dependency:** All Phase 5 complete
- **Estimated Timeline:** 8–12 hours, following Phase 5.2

### Phase 7 (P2 - Medium)
- **Why:** Enhances Phase 5 with advanced configuration
- **Impact:** Customization, improved UX
- **Dependency:** Phase 6 complete
- **Estimated Timeline:** Post-v1.0 release (2–3 months)

### Phase 8+ (P3 - Low)
- **Why:** Long-term vision, nice-to-have features
- **Impact:** Differentiation, advanced analytics
- **Dependency:** Mature v1.0+ ecosystem
- **Estimated Timeline:** 3–6 months+ (vision items)

---

## 📈 Velocity & Sprint Planning

### Current Velocity
- **Phase 5.1 (1 session):** 5 tasks in ~8 hours = **5 tasks/session**
- **Average Task Effort:** ~1.6 hours

### Phase 5.2 Sprint Estimate
- **Total Effort:** 10–15 hours
- **Sprint Duration:** 2–3 days (with parallel work)
- **Team Size:** 1–2 developers
- **Recommended Breakdown:**
  - Session 1: T019 (Port Sensors) — 4–5 hours
  - Session 2: T020 (Frontend) — 6–8 hours
  - Session 3: T021 (Tests) — 2–3 hours

### Phase 6 Release Sprint Estimate
- **Total Effort:** 8–12 hours
- **Recommended Breakdown:**
  - T022 (Docs): 4–5 hours
  - T023 (Regression): 2–3 hours
  - T024 (Release): 2–4 hours

---

## 🔗 Dependencies & Blockers

| Item | Blocker | Status | Note |
|------|---------|--------|------|
| T019 | Phase 5.1 | ✅ Complete | Ready to start |
| T020 | T019 | ⏳ Blocked | Needs sensor entities |
| T021 | T019, T020 | ⏳ Blocked | Needs both for testing |
| T022 | T019–T021 | ⏳ Blocked | Needs Phase 5.2 complete |
| T023 | T019–T022 | ⏳ Blocked | Needs all changes complete |
| T024 | T023 | ⏳ Blocked | Needs regression sign-off |
| T025 | T024 | ⏳ Blocked | Post-release enhancement |

---

## 📝 How to Update This Backlog

1. **Completing a Task:** Move to ✅ Complete, update status
2. **Adding a Feature:** Create T### section under appropriate phase
3. **Community Requests:** Add to "Community Suggestions" with voting
4. **Blockers:** Update dependencies table and status
5. **Timeline Changes:** Document in meeting notes with reason

---

## 📚 Related Documentation

- [PROJECT_STATUS.md](PROJECT_STATUS.md) — Overall project status
- [PHASE_5_COMPREHENSIVE_SUMMARY.md](PHASE_5_COMPREHENSIVE_SUMMARY.md) — Phase 5.1 details
- [PHASE_5_QUICKSTART.md](PHASE_5_QUICKSTART.md) — Quick reference
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines
- [docs/](docs/) — User and developer documentation

---

## 🎓 Future Work Suggestions

### Short Term (Next Sprint)
1. ✅ **Complete Phase 5.2** (sensors + UI) — 10–15 hours
2. ✅ **Release v1.0** (Phase 6) — 8–12 hours
3. ✅ **Community Feedback Collection** — Solicit input on Phase 7

### Medium Term (Q4 2026–Q1 2027)
1. **Per-Port Configuration** (T025) — 4–6 hours
2. **Port Schedule/Expectations** (T026) — 6–8 hours
3. **Historical View** (T027) — 4–5 hours
4. **Multi-Port Dashboard** (T028) — 3–4 hours

### Long Term (2027+)
1. **Route Planning Integration** (T029) — 8–10 hours
2. **Advanced Analytics** (T030–T034) — 20–30 hours
3. **Multi-Entry Management** (T032) — 6–8 hours
4. **Community-Driven Features** (Based on voting)

---

## 📞 Contact & Feedback

- **GitHub Issues:** Feature requests and bug reports
- **GitHub Discussions:** Feature ideas and brainstorming
- **Pull Requests:** Community contributions
- **Email:** (To be configured)

---

**Last Review:** 2026-10-30  
**Next Review:** After Phase 5.2 completion  
**Maintainer:** EAasen
