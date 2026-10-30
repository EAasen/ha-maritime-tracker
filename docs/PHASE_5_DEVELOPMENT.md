# Phase 5 Implementation: Observed Port-Call Board

**Status:** 🟡 In Progress  
**Start Date:** 2026-10-30  
**Target Completion:** Phase 5.1 → Phase 5.2 → Release  

---

## Phase Overview

Phase 5 implements **port geofencing and observed-call tracking** with a persistent board showing:
- Named geofences (circles defined by center + radius)
- Confirmed arrivals/departures (NOT stale eviction or inferred events)
- Present vessel counts and recent call history
- Dashboard integration via port board card overlay

**Key Principle:** Two consecutive fresh observations must confirm a boundary crossing. Stale gaps, restarts, and port edits do NOT fabricate false calls.

---

## Architecture Flow

```
Coordinator._async_update_data()
    ↓
[Phase 2] VesselEventTracker (status events)
    ↓
[Phase 5] PortCallTracker (geofence membership + hysteresis)
    ↓
[Phase 5] PortStorage (persisted baselines + call history)
    ↓
[Phase 5] PortSensors (present/arrivals/departures sensors)
    ↓
[Phase 5.2] maritime-tracker-card (port board overlay)
```

---

## Implementation Tasks

### Phase 5.1: Port Configuration and Confirmed Calls

#### ✅ T016: Port Config Flow and Management

**Objective:** Add optional port management submenu to config flow.

**Files to modify:**
- `const.py` - Add port constants
- `strings.json` - Add translations
- `config_flow.py` - Add port submenu

**Constants to add:**
```python
CONF_PORTS = "ports"
MAX_PORTS = 50
PORT_MIN_RADIUS_KM = 0.1
PORT_MAX_RADIUS_KM = 500
PORT_RECENT_CALL_HOURS = 24
MAX_PORT_CALL_ROWS = 50
```

**Port data structure:**
```python
{
    "id": "port_001",  # stable UUID
    "name": "Oslo Port",
    "latitude": 59.9,
    "longitude": 10.75,
    "radius_km": 5.0
}
```

**Config flow changes:**
- New submenu: "Ports"
- Add/edit/delete ports
- Validate: duplicate names, coordinate ranges, radius 0.1–500 km
- Store in `config.options[CONF_PORTS]` (list of dicts)

**Validation:**
- Port name: non-empty, max 50 chars
- Latitude: -90 to +90
- Longitude: -180 to +180
- Radius: 0.1 to 500 km
- No duplicate port names (case-insensitive)

---

#### ✅ T017a: Port Call Tracker (State Machine)

**Objective:** Create `port_calls.py` with PortCallTracker class.

**Core logic:**

```python
from dataclasses import dataclass
from typing import Optional, Literal, Tuple
from datetime import datetime

@dataclass
class PortBaseline:
    """Last known vessel state for a port."""
    port_id: str
    mmsi: str
    last_known_inside: bool  # was vessel inside on last session?
    last_known_timestamp: datetime
    baseline_version: int = 1

@dataclass
class PortCall:
    """Confirmed port entry/exit event."""
    port_id: str
    port_name: str
    mmsi: str
    vessel_name: Optional[str]
    call_type: Literal["arrival", "departure"]
    observed_at: datetime
    reported_eta: Optional[str] = None
    reported_destination: Optional[str] = None
    last_position: Tuple[float, float] = (0.0, 0.0)

class PortCallTracker:
    """Tracks vessel entry/exit from port geofences with hysteresis."""
    
    def __init__(self):
        self._pending_state: dict = {}  # (port_id, mmsi) -> (inside, timestamp)
    
    def check_vessel(
        self, 
        vessel,
        ports: list[dict],
        baselines: dict[str, PortBaseline]
    ) -> list[PortCall]:
        """
        Check if vessel crosses any port boundary.
        
        Returns confirmed calls (list may be empty, or contain 1–2 calls per port).
        
        Algorithm:
        1. For each port, calculate if vessel is inside geofence
        2. Compare with last known state (from baseline or pending)
        3. If same state twice in a row → confirm transition
        4. If second observation closer to boundary → ignore (jitter)
        5. Record baseline for next session
        """
        # Implementation details:
        # - Track (port_id, mmsi) -> pending state
        # - Require two consecutive observations to confirm
        # - Handle stale timestamps (don't fabricate calls on resume)
        # - Return list of confirmed PortCall objects
```

**Hysteresis Logic:**
1. First observation: record as "pending" if state differs from baseline
2. Second observation:
   - Same state or farther = **confirmed** → emit call + update baseline
   - Closer to boundary = ignore (jitter)
3. Gap (>24 hours stale): clear pending, don't fabricate call on resume

**Point-in-circle calculation:**
```python
def is_inside_geofence(vessel_lat: float, vessel_lon: float, 
                       center_lat: float, center_lon: float, 
                       radius_km: float) -> bool:
    """Check if vessel is inside circular geofence."""
    # Use Haversine or simplified: 1 degree ≈ 111 km
    delta_lat = vessel_lat - center_lat
    delta_lon = vessel_lon - center_lon
    # Account for longitude scaling at latitude
    delta_lon_km = delta_lon * 111 * cos(radians(center_lat))
    distance_km = sqrt(delta_lat * 111)^2 + delta_lon_km^2)
    return distance_km <= radius_km
```

---

#### ✅ T017b: Storage Extension for Port Calls

**Objective:** Extend `storage.py` with PortEventStorage class.

**Add to storage.py:**

```python
class PortEventStorage(VesselEventStorage):
    """Persist per-port baselines and bounded call history."""
    
    async def load_entry(
        hass: HomeAssistant, 
        entry_id: str
    ) -> dict[str, dict[str, PortBaseline]]:
        """
        Load all baselines for entry.
        Returns: {port_id: {mmsi: PortBaseline}}
        """
    
    async def save_baseline(
        hass: HomeAssistant,
        entry_id: str,
        baseline: PortBaseline
    ) -> None:
        """Save or update vessel baseline for port."""
    
    async def save_call(
        hass: HomeAssistant,
        entry_id: str,
        call: PortCall
    ) -> None:
        """Persist confirmed call to bounded history."""
    
    async def get_recent_calls(
        hass: HomeAssistant,
        entry_id: str,
        port_id: str,
        hours: int = 24,
        limit: int = 50
    ) -> list[PortCall]:
        """Retrieve recent calls for a port."""
    
    async def clear_port(
        hass: HomeAssistant,
        entry_id: str,
        port_id: str
    ) -> None:
        """Clear all data for a port (on deletion)."""
```

**Storage format (JSON file per entry):**
```json
{
  "baselines": {
    "port_001": {
      "123456789": {
        "last_known_inside": false,
        "last_known_timestamp": "2026-10-30T12:00:00Z",
        "baseline_version": 1
      }
    }
  },
  "calls": {
    "port_001": [
      {
        "mmsi": "123456789",
        "vessel_name": "Vessel A",
        "call_type": "arrival",
        "observed_at": "2026-10-30T10:00:00Z",
        "reported_eta": null,
        "reported_destination": null,
        "last_position": [59.9, 10.75]
      }
    ]
  }
}
```

**Retention:** Max ~50 calls per port (oldest removed first).

---

#### ✅ T017c: Coordinator Integration

**Objective:** Integrate PortCallTracker and PortEventStorage into coordinator.py.

**Changes:**

```python
class MaritimeDataUpdateCoordinator:
    def __init__(self, hass, ...):
        # ... existing init ...
        self._port_tracker = PortCallTracker()
        self._port_storage: Optional[PortEventStorage] = None
    
    async def async_load_baselines(self) -> None:
        """Load baselines after entry is configured."""
        # ... existing vessel event baseline loading ...
        
        # NEW: Load port baselines
        self._port_baselines = await PortEventStorage.load_entry(
            self.hass, self.config_entry.entry_id
        )
    
    async def _async_update_data(self) -> dict:
        """Fetch and process vessel data."""
        # ... existing code ...
        
        # NEW: Check port calls for each vessel
        ports = self.config_entry.options.get(CONF_PORTS, [])
        if ports:
            for vessel in vessels:
                calls = self._port_tracker.check_vessel(
                    vessel, ports, self._port_baselines
                )
                for call in calls:
                    # Save to storage
                    await self._port_storage.save_call(
                        self.config_entry.entry_id, call
                    )
                    # Fire event for automations
                    self.hass.bus.async_fire(
                        EVENT_PORT_CALL,
                        call.as_dict()
                    )
                    # Update baselines for next check
                    self._port_baselines[call.port_id][call.mmsi] = (
                        PortBaseline(...)
                    )
```

**New constants in const.py:**
```python
EVENT_PORT_CALL = "marinetraffic_tracker_port_call"
```

---

### Phase 5.2: Port Sensors and Dashboard

#### ✅ T019: Port Sensors

**Objective:** Extend `sensor.py` with three sensor types per port.

**Sensors created per port:**

1. **Port Present** (`sensor.<entry>_port_<port_id>_present`)
   - State: integer count (0–N) of vessels currently inside
   - Attributes:
     - `vessels`: list of {mmsi, name, eta, destination, inside_duration_minutes}
     - `count`: same as state (redundant but explicit)
     - `provenance`: "observed" (from geofence tracking)

2. **Port Recent Arrivals** (`sensor.<entry>_port_<port_id>_recent_arrivals`)
   - State: integer count of arrivals in last 24h
   - Attributes:
     - `calls`: list of {mmsi, name, arrival_time, reported_eta, reported_destination}
     - `count`: same as state

3. **Port Recent Departures** (`sensor.<entry>_port_<port_id>_recent_departures`)
   - State: integer count of departures in last 24h
   - Attributes:
     - `calls`: list of {mmsi, name, departure_time}
     - `count`: same as state

**Implementation:**

```python
async def async_update_port_sensors(
    hass: HomeAssistant,
    entry_id: str,
    coordinator: MaritimeDataUpdateCoordinator
) -> None:
    """Update all port sensors based on current data."""
    ports = coordinator.config_entry.options.get(CONF_PORTS, [])
    
    for port in ports:
        port_id = port["id"]
        
        # Get current vessel positions (check against geofence)
        present_vessels = [...]  # vessels currently inside
        
        # Get recent calls
        recent_arrivals = await coordinator._port_storage.get_recent_calls(
            entry_id, port_id, hours=24, call_type="arrival"
        )
        recent_departures = await coordinator._port_storage.get_recent_calls(
            entry_id, port_id, hours=24, call_type="departure"
        )
        
        # Update states
        hass.states.async_set(
            f"sensor.{entry_id}_port_{port_id}_present",
            len(present_vessels),
            attributes={...}
        )
        # ... similar for arrivals and departures
```

**Sensor entities:**
- Become `unavailable` when coordinator unavailable
- Update on each coordinator update
- Automatically clean up when port deleted

---

#### ✅ T020: Port Board UI

**Objective:** Extend `frontend/maritime-tracker-card.js` with port overlay and board panel.

**Card enhancements:**

1. **Port Overlay on Map:**
   - Draw circles for each configured port
   - Color: semi-transparent blue
   - On click: show port name and vessel count
   - Toggle via card config option

2. **Port Board Panel:**
   - Three collapsible sections: Present / Recent Arrivals / Recent Departures
   - Each section shows a table with vessel data
   - Clickable rows link to vessel details
   - Shows "reported" label for ETA/destination (not confirmed)

3. **Card Configuration:**
```yaml
type: maritime-tracker-card
entity: sensor.my_area_vessel_count
zoom: 8
show_port_board: true
port_board_height: 300
```

**CSS & Styling:**
- Responsive layout (board stacks below map on mobile)
- Dark mode support (card background, text colors)
- Geofence circles with opacity control
- Table borders and hover effects

---

#### ✅ T021: Port Board Tests

**Objective:** Create frontend and sensor tests.

**Files:**
- Extend `test_sensor_attributes.py` for port sensors
- Extend `test_websocket_api.py` for port board data
- Create `tests/frontend/test_port_board.js` for card component

**Test scenarios:**
- Board renders with no ports configured
- Board renders with ports but no vessels
- Correct present/arrival/departure counts
- Row limits enforced (≤50 per table)
- ETA/destination labeled "reported"
- Unknown ETA/destination handled gracefully
- Duplicate MMSI calls shown once (most recent)
- Port deletion clears board
- Mobile layout stacks correctly

---

#### ✅ T022: Documentation Updates

**Files to update:**
- `docs/usage.md` - Add port configuration guide
- `docs/architecture.md` - Add port call architecture diagram
- `README.md` - Mention port-call feature

**Content:**
- How to add/edit/delete ports
- Port board card configuration
- Interpretation of "present" vs "reported" data
- Known limitations (geofence accuracy depends on AIS update frequency)

---

#### ✅ T023: Regression Suite and Release

**Objective:** Full validation before release.

**Python tests:**
```bash
pytest tests/ -v --cov=custom_components/marinetraffic_tracker
```

**Lint & type checks:**
```bash
pylint custom_components/marinetraffic_tracker/
mypy custom_components/marinetraffic_tracker/
```

**HA checks:**
```bash
hass --script check_config -c ./
```

**HASSfest:**
```bash
python3 -m script.hass_version_check
```

**Manual validation:**
1. Add port to config (Oslo Port, 59.9°N, 10.75°E, 5 km radius)
2. Add vessel MMSI to watchlist
3. Observe vessel crossing port boundary
4. Verify: port call emitted → sensor updated → board shows call
5. Edit port (name change) → no false calls triggered
6. Delete port → board clears, no errors
7. Restart HA → calls persist, no replay, board resumes correctly

**Coverage gate:** Maintain ≥80% code coverage.

---

## Current Implementation Status

| Task | Status | Notes |
|------|--------|-------|
| T016 - Config Flow | ⏳ Pending | Ready to start |
| T017a - Port Tracker | ⏳ Pending | Requires T016 |
| T017b - Storage | ⏳ Pending | Requires T016 |
| T017c - Coordinator | ⏳ Pending | Requires T017a + T017b |
| T018 - Tests | ⏳ Pending | Requires T017c |
| T019 - Sensors | ⏳ Pending | Requires T017c |
| T020 - UI | ⏳ Pending | Requires T019 |
| T021 - UI Tests | ⏳ Pending | Requires T020 |
| T022 - Docs | ⏳ Pending | Requires T021 |
| T023 - Regression | ⏳ Pending | Final gate |

---

## Key Files to Create/Modify

**Create:**
- `custom_components/marinetraffic_tracker/port_calls.py`
- `tests/test_port_calls.py`
- `tests/test_port_sensors.py` (if separate from sensor tests)

**Modify:**
- `custom_components/marinetraffic_tracker/const.py`
- `custom_components/marinetraffic_tracker/config_flow.py`
- `custom_components/marinetraffic_tracker/storage.py`
- `custom_components/marinetraffic_tracker/coordinator.py`
- `custom_components/marinetraffic_tracker/sensor.py`
- `custom_components/marinetraffic_tracker/frontend/maritime-tracker-card.js`
- `custom_components/marinetraffic_tracker/strings.json`
- `docs/usage.md`
- `docs/architecture.md`

---

## Next Steps

1. ✅ Review this implementation plan
2. Start **T016: Port Config Flow** (modify const.py, config_flow.py, strings.json)
3. Proceed through dependency chain: T017a → T017b → T017c → T018 → T019 → T020 → T021 → T022 → T023

---

**Prepared for execution:** 2026-10-30  
**Estimated Duration:** ~20-30 hours of focused development  
**Target Release:** Phase 5 + Phase 6 (documentation) complete and tested
