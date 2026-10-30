# Phase 5 Preparation Guide: Observed Port-Call Board

**Status:** Ready for implementation  
**Dependency:** Phase 4 (✅ complete)  
**Expected Scope:** P5.1 + P5.2  

---

## Quick Reference

Phase 5 implements port geofencing and observed-call tracking — distinct from the legacy event system and stale-eviction. Two vessels confirming a boundary transition create exactly one call; outages, restarts, and port edits do not.

### High-Level Requirements

| REQ | Feature |
|---|---|
| REQ-007 | Named geofences + observed arrivals/departures (not stale eviction or inferred) |
| REQ-008 | Port board shows present vessels + bounded recent calls; ETA/destination labeled as "reported" |
| REQ-009 | Bounded persistence without replay; resumption does not re-emit calls |

### Architecture

```
Coordinator._async_update_data()
    ↓
VesselEventTracker (status events) [Phase 2]
    ↓
PortCallTracker (geofence membership) [Phase 5 new]
    ↓
PortStorage (persisted baselines + call history) [Phase 5 new]
    ↓
PortSensors (present/recent-arrival/recent-departure) [Phase 5 new]
    ↓
maritime-tracker-card (port board overlay) [Phase 5 enhancement]
```

---

## Phase 5.1: Port Configuration and Confirmed Calls

### Tasks

#### T016 — Config flow and port management

**File:** Extend `config_flow.py`

Add an optional submenu for port management:
- Add/edit/delete named circles (stable ID, geometry: center + radius_km)
- Store in `options[CONF_PORTS]` as list of dicts
- Validate MMSI format (nine digits), radius (0.1–500 km)
- Keep watchlist and existing settings intact
- Preserve area unique-ID generation

**Constants** (`const.py`):
```python
CONF_PORTS = "ports"
MAX_PORTS = 50  # per entry
PORT_MIN_RADIUS_KM = 0.1
PORT_MAX_RADIUS_KM = 500
PORT_RECENT_CALL_HOURS = 24  # window for "recent" calls
```

**Strings/translations**:
- "Ports" (menu label)
- "Add port" (button)
- "Port name" (field)
- "Port latitude", "Port longitude" (fields)
- "Port radius (km)" (field)
- Validation messages (duplicate name, invalid coordinates, out-of-range radius)

#### T017 — Port call state machine and storage

**File:** New `port_calls.py`

Geofence membership tracking with confirmation:

```python
class PortCallTracker:
    """Tracks vessel entry/exit from port geofences with hysteresis."""
    
    def check_vessel(self, vessel: VesselData, ports: list[Port]) -> list[PortCall]:
        """
        Check if vessel crosses any port boundary.
        Returns confirmed calls (list may be empty, or contain 1–2 calls per port).
        """
        # Inside → outside = departure (if fresh, not stale eviction)
        # Outside → inside = arrival
        # Jitter at boundary = ignored (hysteresis)
        # Same-message repeat = ignored
        # Coverage gap = gap recorded, resumption does not fabricate calls
```

**Hysteresis Logic:**
- Two consecutive fresh observations needed to confirm boundary crossing
- First observation records "maybe inside/outside"
- Second observation same or farther = confirmed transition
- Second observation closer = boundary jitter, ignored

**Storage** (`storage.py` extensions):
```python
class PortEventStorage(VesselEventStorage):
    """Persist per-port baselines and bounded call history."""
    
    async def get_baseline(entry_id: str, port_id: str, mmsi: str) -> Optional[PortBaseline]:
        """Get last known vessel membership for port (before this session)."""
    
    async def save_call(entry_id: str, call: PortCall) -> None:
        """Persist a confirmed call to bounded history."""
```

**Baseline structure:**
```python
@dataclass
class PortBaseline:
    port_id: str
    mmsi: str
    last_known_inside: bool  # was vessel inside on last session?
    last_known_timestamp: datetime
    baseline_version: int  # for versioning baseline format
```

**Call structure:**
```python
@dataclass
class PortCall:
    port_id: str
    port_name: str
    mmsi: str
    vessel_name: Optional[str]
    call_type: Literal["arrival", "departure"]  # fresh observation
    observed_at: datetime  # when crossing confirmed
    reported_eta: Optional[str]  # from vessel AIS
    reported_destination: Optional[str]  # from vessel AIS
    last_position: Tuple[float, float]  # (lat, lon) at time of call
```

**Integration** (`coordinator.py`):
```python
# In __init__:
self._port_tracker = PortCallTracker()
self._port_storage: Optional[PortEventStorage] = None

# In async_load_baselines():
baselines = await PortEventStorage.load_entry(hass, entry_id)

# In _async_update_data():
ports = config.options.get(CONF_PORTS, [])
for call in self._port_tracker.check_vessel(vessel, ports, baselines):
    await self._port_storage.save_call(entry_id, call)
    hass.bus.async_fire(EVENT_PORT_CALL, call.as_dict())
```

#### T018 — Port call tests

**File:** New `test_port_calls.py`, extend `test_storage.py` and `test_config_flow.py`

Test scenarios:
- Vessel inside geofence, exits (one departure call)
- Vessel outside, enters (one arrival call)
- Vessel crosses boundary twice in one update (two calls: exit + re-enter)
- Jitter at boundary (no call if second observation closer)
- Same message repeated (no duplicate call)
- Coverage gap (no fabricated call on resumption)
- Stale eviction does not create departure call
- Port edited (baseline reset, no false calls)
- Port deleted (stored state removed, no calls emitted)
- Config entry deleted (all port data cleaned up)
- Retention limits (max MAX_PORT_CALL_ROWS per port)
- Unknown/unparseable source time (baseline stores as uncertain)

---

## Phase 5.2: Port Sensors and Dashboard

### Tasks

#### T019 — Port sensors

**File:** Extend `sensor.py`

New sensor types per port:

1. **Port present sensor** (`sensor.<entry>_port_<port_id>_present`)
   - State: count of vessels currently inside (0–N)
   - Attributes: list of (MMSI, name, ETA, destination)

2. **Port recent arrivals** (`sensor.<entry>_port_<port_id>_recent_arrivals`)
   - State: count of arrivals in last PORT_RECENT_CALL_HOURS
   - Attributes: list of recent calls (MMSI, name, timestamp)

3. **Port recent departures** (`sensor.<entry>_port_<port_id>_recent_departures`)
   - State: count of departures in last PORT_RECENT_CALL_HOURS
   - Attributes: list of recent calls (MMSI, name, timestamp)

Each sensor:
- Becomes `unavailable` when entry/coordinator unavailable
- Shows "provenance" (observed/confirmed vs. reported/unverified)
- Clears on port deletion
- Bounded rows (max ~50 per list)
- ISO-8601 timestamps

#### T020 — Port board UI

**File:** Extend `frontend/maritime-tracker-card.js`

Enhancements:
- **Port overlay** on map (geofence circles)
- **Port board panel** (optional, configurable via card config)
- **Present vessels table**: MMSI, name, time inside, speed, destination
- **Recent arrivals table**: MMSI, name, arrival time, reported ETA (marked as "reported")
- **Recent departures table**: MMSI, name, departure time
- Empty states (no ports configured, no calls)
- Clickable rows link to vessel details
- Distinguishes observed calls from reported data

**Card config extension:**
```yaml
type: maritime-tracker-card
entity: sensor.my_area_vessel_count
zoom: 8
show_port_board: true
port_board_height: 300  # pixels
```

#### T021 — Port board tests

**File:** Extend `test_sensor_attributes.py`, `test_websocket_api.py`, `tests/frontend/`

- Board renders with no ports configured
- Board renders with ports but no vessels inside
- Board shows correct present/arrival/departure counts
- Row limits enforced (no more than ~50 rows each)
- ETA/destination labeled "reported" (not scheduled)
- Unknown ETA/destination handled gracefully
- Same-MMSI repeated calls shown once (most recent)
- Port deletion clears board data
- Two entries show separate port boards
- Mobile layout: board stacks below map

---

## Implementation Checklist

- [ ] T016: Port config flow and management UI
- [ ] T017: Port call state machine (port_calls.py)
- [ ] T017: Storage extension (PortEventStorage)
- [ ] T017: Coordinator integration
- [ ] T018: Port call tests
- [ ] T019: Port sensors
- [ ] T020: Port board card component
- [ ] T021: Port board tests
- [ ] T022: Update usage.md, architecture.md (port configuration, port board card)
- [ ] T023: Full regression suite (Python + frontend) before release

---

## Key Differences from Phase 2 (Status Events)

| Aspect | Phase 2 (Status Events) | Phase 5 (Port Calls) |
|---|---|---|
| Trigger | AIS status field change | Geofence boundary crossing |
| Confirmation | One observation (with validation) | Two fresh observations (hysteresis) |
| Persistence | Status baselines only | Full call history (timestamps, positions) |
| Scope | Per vessel, global | Per port, per vessel |
| User entity | Events only (automations) | Sensors (dashboards) + events |
| Stale handling | Stale eviction does not trigger event | Stale gap does not fabricate calls |

---

## Preparation for Implementation

1. **Review existing code:**
   - `vessel_events.py` (status tracking pattern)
   - `storage.py` (persistence pattern)
   - `coordinator.py` (integration points)

2. **Study geofence algorithm:**
   - Point-in-circle: `distance = sqrt((lat - center_lat)^2 + (lon - center_lon)^2) * 111` (km per degree)
   - Hysteresis: track last known state for each (port, mmsi) pair

3. **Leaflet integration for Phase 5.2:**
   - `L.circle()` for port boundaries
   - `L.popup()` for port name on click
   - WebSocket extension for port board data (bounded rows)

4. **Test data preparation:**
   - Synthetic AIS sequences with geofence crossings
   - Jitter scenarios (oscillating on boundary)
   - Coverage gaps (stale timeout between messages)
   - Two-port scenarios (same vessel crosses multiple ports)

---

## Estimated Scope

- **Python:** ~800 lines (port_calls.py + storage extension + sensors + config flow extension + tests)
- **Frontend:** ~600 lines (port overlay + board panel + styling)
- **Tests:** ~500 lines (comprehensive coverage)
- **Documentation:** ~200 lines (usage.md, architecture.md updates)

---

## Release Gate

Before merging Phase 5:

✅ All Python tests pass (80% coverage floor maintained)  
✅ Lint/type checks clean  
✅ HA version matrix passes (minimum 2025.1.0)  
✅ HASSfest passes  
✅ Frontend tests pass (browser validation)  
✅ Manual test: port added, vessel crosses, call emitted, sensor updated, board displayed  
✅ Manual test: port edited/deleted, no false calls, board updates  
✅ Manual test: restart, calls resume, no replay  

---

## Next Phase After 5

**Phase 6: Documentation and Release Readiness (T022-T023)**
- Final documentation sweep
- Full regression suite
- Release packaging and version bump

Then release the complete four-feature set to users.
