# Norwegian Maritime Tracker for Home Assistant 🚢

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Tests](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/tests.yml)
[![Lint](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/lint.yml/badge.svg)](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/lint.yml)
[![Validate](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/ci.yml)
[![HA Version Compatibility](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/ha-version-matrix.yml/badge.svg)](https://github.com/EAasen/ha-maritime-tracker/actions/workflows/ha-version-matrix.yml)

Official Kystverket AIS maritime tracker for Home Assistant. Real-time vessel tracking in Norwegian waters using the Norwegian Coastal Administration live AIS feed exposed through BarentsWatch.

## Documentation

| Guide | Description |
|---|---|
| [Installation](docs/installation.md) | HACS and manual installation steps |
| [Configuration](docs/configuration.md) | BarentsWatch credentials, config flow walkthrough, all options |
| [Usage](docs/usage.md) | Entities, automations, and Lovelace card examples |
| [Troubleshooting](docs/troubleshooting.md) | Common issues, log instructions, connection testing |
| [Development](docs/development.md) | Setup, testing, linting, and contribution guidelines |
| [Architecture](docs/architecture.md) | Integration structure and data flow for developers |

---

## Quick Start

### 1. Install via HACS

1. Open **HACS** in Home Assistant.
2. Click **⋮ → Custom repositories**, add `https://github.com/EAasen/ha-maritime-tracker`, category **Integration**.
3. Install **Norwegian Maritime Tracker** and **restart Home Assistant**.

> **Manual install:** copy `custom_components/marinetraffic_tracker/` into `/config/custom_components/` and restart.

### 2. Get free BarentsWatch credentials

1. Create an account at <https://www.barentswatch.no/mine-side/>.
2. Register a client application and note the **Client ID** and **Client Secret**.

### 3. Add the integration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Norwegian Maritime Tracker**.
3. Follow the setup wizard — pick a radius or bounding box, enter your credentials, and set the update interval.

---

## Complete Setup Guide

A step-by-step walkthrough from nothing installed to vessels on your map.

### Step 1 — Check prerequisites

| Requirement | Notes |
|---|---|
| Home Assistant **2025.1.0** or newer | Older releases are not supported. Check under **Settings → About**. |
| HACS installed | Optional — a manual copy works too (Step 2b). |
| Internet access from HA | The integration calls `id.barentswatch.no` and `live.ais.barentswatch.no` over HTTPS. |
| A BarentsWatch account | Free. Created in Step 3. |

### Step 2a — Install through HACS (recommended)

1. Open **HACS** from the sidebar.
2. Click the **⋮** menu (top right) → **Custom repositories**.
3. Paste `https://github.com/EAasen/ha-maritime-tracker` into **Repository**, choose **Integration** as the category, and click **Add**.
4. Search HACS for **Norwegian Maritime Tracker** and click **Download**. Accept the offered version (newest).
5. **Restart Home Assistant** — **Settings → System → ⋮ → Restart Home Assistant**. The integration will not appear in the Add Integration list until you do.

### Step 2b — Install manually

1. Download the latest release from the [Releases page](https://github.com/EAasen/ha-maritime-tracker/releases).
2. Copy the folder `custom_components/marinetraffic_tracker/` into your Home Assistant `config/custom_components/` directory, so you end up with `config/custom_components/marinetraffic_tracker/manifest.json`.
3. Restart Home Assistant.

### Step 3 — Create BarentsWatch API credentials

The AIS feed is free but requires a client registration. This takes about two minutes.

1. Go to <https://www.barentswatch.no/minside/> and create an account (or log in).
2. Open **Min side → API-klienter** (My page → API clients).
3. Click to create a new client. Give it any name, e.g. `home-assistant`.
4. **Important:** enable the **`ais`** scope. Without it the integration receives HTTP 403 and no vessels.
5. Copy the **Client ID** and **Client Secret**. The secret is shown only once — store it somewhere safe before leaving the page.

> The Client ID usually looks like `your-email@example.com:home-assistant`. Paste it exactly as shown, including the part before the colon.

### Step 4 — Add and configure the integration

1. **Settings → Devices & Services → + Add Integration**.
2. Search for and select **Norwegian Maritime Tracker**.
3. **Intro screen** — confirms you have credentials ready. Click **Submit**.
4. **Credentials** — paste the Client ID and Client Secret. The integration validates them against BarentsWatch immediately; a wrong value is rejected here rather than failing silently later.
5. **Tracking mode** — choose how to define your area:
   - **Radius** — drop a pin on the map and set a distance in kilometres. Easiest option.
   - **Bounding box** — enter north/east/south/west coordinates. Use when you want a rectangle, e.g. a fjord or a shipping lane.
6. **Area** — place the pin (or type the coordinates) and set the size.
7. **Options** — see the table below. Defaults are sensible; you can change all of these later.

Click **Finish**. Within one poll cycle you should see a **Vessel Count** sensor with a non-zero value.

### Step 5 — Tune the options

Reachable any time via **Settings → Devices & Services → Norwegian Maritime Tracker → Configure**.

| Option | Default | What it does |
|---|---|---|
| **Update interval** | 60 s | How often to poll. Minimum 5 s. Lower means fresher data and more API load. |
| **Stale vessel timeout** | 3600 s | A vessel not heard from for this long is dropped. Raise it in areas with patchy AIS reception. |
| **Allowed vessel types** | all | Restrict tracking to chosen categories, e.g. only Passenger and Cargo. |
| **Exclude anchored / moored** | off | Hides stationary vessels from the live map. They are still counted in statistics. |
| **Show tracked area on map** | on | Draws your area as a zone. See the caveat in [Usage](docs/usage.md). |
| **Write vessel log files** | off | Appends every observation to disk. See [Vessel Log Files](#vessel-log-files). |
| **Vessel log format** | CSV | `CSV` for spreadsheets, `JSON Lines` for scripts. |
| **Vessel log retention** | 7 days | Deletes logs older than this. `0` keeps them forever. |

### Step 6 — Put vessels on your map

Add a **Manual card** to any dashboard:

```yaml
type: map
geo_location_sources:
  - marinetraffic_tracker
```

Every vessel in your area appears as a marker, with no entity to enable first. Markers are added and removed automatically as vessels come and go.

To also show a table of vessels, use the count sensor's `vessels` attribute — see [Usage](docs/usage.md) for a full card example.

### Step 7 — Verify it is working

| Check | Where | Expected |
|---|---|---|
| Vessel count | **Developer Tools → States**, filter `sensor.` | Non-zero during normal traffic hours |
| Map markers | Your map card | Vessel icons inside the area |
| Errors | **Settings → System → Logs** | No entries from `marinetraffic_tracker` |

If something looks wrong, enable debug logging by adding this to `configuration.yaml` and restarting:

```yaml
logger:
  default: warning
  logs:
    custom_components.marinetraffic_tracker: debug
```

Then see [Troubleshooting](docs/troubleshooting.md). Remember to remove the block afterwards — debug logging is verbose.

---

## Vessel Log Files

Enable **Write vessel log files** in the options to keep a permanent record of every observation, with every AIS field, independent of Home Assistant's recorder (which purges old data by default).

**Where:** `config/marinetraffic_tracker/vessels-<id>-YYYY-MM-DD.csv`
A new file is started each day. Files older than the retention setting are deleted automatically.

**What each row contains** — one row per vessel per poll cycle:

| Column | Unit / format | Description |
|---|---|---|
| `logged_at` | ISO 8601 UTC | When this poll cycle was written |
| `mmsi` | 9 digits | Maritime Mobile Service Identity — the unique vessel ID |
| `name` | text | Vessel name as broadcast |
| `vessel_type` | AIS code | Raw numeric AIS ship type |
| `vessel_type_name` | text | Decoded category, e.g. `Cargo`, `Tanker`, `Passenger` |
| `latitude` / `longitude` | decimal degrees | Reported position |
| `heading` | degrees | True heading from the compass; empty when unavailable |
| `course` | degrees | Course over ground, derived from movement |
| `speed` | knots | Speed over ground |
| `status` | text | AIS navigational status, e.g. `Under Way Using Engine`, `At Anchor` |
| `origin` | text | Last port, when broadcast |
| `destination` | text | Destination as typed by the crew — often abbreviated or stale |
| `eta` | text | Estimated time of arrival, as broadcast |
| `imo` | 7 digits | IMO number — permanent, unlike MMSI |
| `flag` | text | Flag state, when available |
| `callsign` | text | Radio callsign |
| `length` | metres | Overall length, derived from antenna offsets |
| `beam` | metres | Width, derived from antenna offsets |
| `draught` | decimetres | Draught as entered by the crew |
| `rate_of_turn` | °/min | Positive is turning to starboard; empty when not reported |
| `msgtime` | ISO 8601 | Timestamp of the AIS message itself |
| `last_seen` | ISO 8601 UTC | When the integration last observed this vessel |
| `source` | text | Which data source supplied the row |

Empty cells mean the vessel did not broadcast that field. `destination`, `eta` and `draught` are manually entered by crews and are frequently blank or inaccurate.

**Sizing.** One row per vessel per poll. A 50 km radius around a busy port with a 60 s interval can produce well over 100,000 rows per day (roughly 20 MB of CSV). Raise the update interval, narrow the area, or lower the retention if disk space matters — Home Assistant OS installations have limited storage.

**Working with the files.** Access them through the **File editor**, **Samba**, or **SSH** add-on. CSV opens directly in Excel, Numbers or LibreOffice. For analysis:

```python
import pandas as pd
df = pd.read_csv("vessels-a1b2c3d4-2026-05-01.csv")
df.groupby("name")["speed"].max().sort_values(ascending=False).head(10)
```

> **Security note:** values that begin with `=`, `+`, `-` or `@` are prefixed with an apostrophe before being written. AIS is an unauthenticated broadcast, so a vessel name is attacker-controlled text and must never be executed as a spreadsheet formula.

---

## Features

- Track vessels inside a **radius** or **bounding box** using the official Kystverket / BarentsWatch AIS feed
- Rich AIS telemetry exposed as Home Assistant entities:

  | Attribute | Description |
  |---|---|
  | `mmsi` | Unique vessel identifier |
  | `vessel_name` | Vessel name |
  | `vessel_type` | AIS vessel category (Cargo, Tanker, Passenger, …) |
  | `speed_knots` | Speed over ground |
  | `course` | Course over ground (degrees) |
  | `heading` | True heading (degrees) |
  | `status` | AIS navigational status |
  | `destination` | Destination port |
  | `eta` | Estimated time of arrival |
  | `imo` | IMO number |
  | `callsign` | Radio callsign |
  | `draught` | Draught in metres |
  | `rate_of_turn` | Rate of turn (°/min) |
  | `msgtime` | Last AIS message timestamp |

- One **vessel count sensor** plus per-vessel **sensors** and **device_tracker** entities
- **Automatic map markers** — every vessel in the area appears on the HA map with no entity setup
- **Vessel log files** — optional CSV / JSON Lines record of every observation with all AIS fields
- **Position history** — last 20 GPS positions per vessel
- **Maritime statistics** sensor — most frequent visitor, speed record, busiest hour, and more
- Optional **vessel-type filter** — track only the categories you care about
- Optional **anchored / moored vessel exclusion** — hide stationary vessels from the live map

---

## Home Assistant Version Compatibility

| Home Assistant Version | Supported |
|------------------------|-----------|
| 2026.x                 | ✅ Tested |
| 2025.x (≥ 2025.1)      | ✅ Tested |
| < 2025.1               | ❌ Not supported |

**Minimum supported version:** Home Assistant **2025.1.0**

Releases older than 2025.1 can no longer be installed or run on Python 3.12, so they cannot be tested and are not claimed as supported.

The integration logs the running HA version at startup and emits a warning if the version is below the minimum requirement. A GitHub Actions matrix job tests the integration against multiple HA versions on every push and weekly schedule.

## What changed for v1.0.0

Version 1.0.0 pivots the integration to a single, official Norwegian data source:

- **Primary source:** Kystverket / BarentsWatch live AIS
- **Default focus:** Norwegian waters
- **Setup flow:** simplified to Norwegian area selection plus BarentsWatch credentials

Earlier scraping-based sources (MarineTraffic, VesselFinder, AISHub) are **deprecated** in the main v1.0.0 flow.  Multi-source support is planned for a future v2.0.0 release.

---

## Notes

- The integration domain remains `marinetraffic_tracker` for compatibility with existing installs.
- The active code path uses the official Norwegian feed instead of scraper-first logic.
- International and multi-source tracking is planned for a later v2.0.0 roadmap release.

## CI / CD

GitHub Actions now provides separate workflows for tests, linting, validation, and tagged releases.

For repository protection, configure the `Tests`, `Lint`, and `Validate` workflows as required status checks on `main`, and require at least one approving code review before merge.
