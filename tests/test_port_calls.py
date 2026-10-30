"""Tests for port call tracking and geofence membership."""

from __future__ import annotations

from datetime import datetime, UTC, timedelta
from typing import Any

import pytest

from custom_components.marinetraffic_tracker.port_calls import (
    PortCallTracker,
    PortBaseline,
    PortCall,
)


@pytest.fixture
def port_tracker() -> PortCallTracker:
    """Create a port call tracker instance."""
    return PortCallTracker()


@pytest.fixture
def test_port() -> dict[str, Any]:
    """Create a test port configuration."""
    return {
        "id": "oslo_port",
        "name": "Oslo Port",
        "latitude": 59.9,
        "longitude": 10.75,
        "radius_km": 5.0,
    }


@pytest.fixture
def test_vessel() -> dict[str, Any]:
    """Create a test vessel data dictionary."""
    return {
        "mmsi": "123456789",
        "vessel_name": "Test Ship",
        "latitude": 59.9,
        "longitude": 10.75,
        "msgtime": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        "eta": "2024-01-02T10:00:00Z",
        "destination": "Oslo",
    }


class TestGeofenceDetection:
    """Test point-in-geofence calculations."""

    def test_vessel_inside_geofence(self, port_tracker: PortCallTracker) -> None:
        """Test that a vessel inside the geofence is detected correctly."""
        # Vessel at port center
        assert port_tracker._is_inside_geofence(
            59.9, 10.75,  # vessel position
            59.9, 10.75,  # port center
            5.0,  # radius in km
        )

    def test_vessel_outside_geofence(self, port_tracker: PortCallTracker) -> None:
        """Test that a vessel outside the geofence is detected correctly."""
        # Vessel ~10 km away
        assert not port_tracker._is_inside_geofence(
            60.0, 10.75,  # vessel position (about 11 km north)
            59.9, 10.75,  # port center
            5.0,  # radius in km
        )

    def test_vessel_at_boundary(self, port_tracker: PortCallTracker) -> None:
        """Test that a vessel at the geofence boundary edge cases work."""
        # Exactly at radius edge should be inside
        assert port_tracker._is_inside_geofence(
            59.9 + (5.0 / 111.0),  # approximately 5 km north
            10.75,
            59.9,
            10.75,
            5.0,
        )

    def test_longitude_scaling(self, port_tracker: PortCallTracker) -> None:
        """Test that longitude scaling is applied at high latitudes."""
        # Test at 70 degrees north where longitude scaling is significant
        assert port_tracker._is_inside_geofence(
            70.0, 20.0,
            70.0, 20.0,
            1.0,
        )

        # Should be outside when far enough east (accounting for scaling)
        assert not port_tracker._is_inside_geofence(
            70.0, 21.0,
            70.0, 20.0,
            1.0,
        )


class TestHysteresisConfirmation:
    """Test hysteresis logic (two-observation confirmation)."""

    def test_single_entry_no_call(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that a single observation does not trigger a call."""
        # Vessel is now inside
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        # No baseline, vessel moves to inside → pending, not confirmed
        assert len(calls) == 0
        
        # Verify pending state was recorded
        assert ("oslo_port", "123456789") in port_tracker._pending_transitions

    def test_confirmation_arrival(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that two observations confirm an arrival."""
        # First observation: vessel enters
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0
        
        # Second observation: vessel still inside (confirms arrival)
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        assert len(calls) == 1
        assert calls[0].call_type == "arrival"
        assert calls[0].mmsi == "123456789"
        assert calls[0].port_name == "Oslo Port"

    def test_confirmation_departure(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that two observations confirm a departure."""
        # Establish baseline: vessel inside
        baseline = {
            "oslo_port": {
                "123456789": PortBaseline(
                    port_id="oslo_port",
                    mmsi="123456789",
                    last_known_inside=True,
                    last_known_timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                )
            }
        }
        
        # First observation: vessel exits
        test_vessel["latitude"] = 60.0  # Move north (outside 5 km radius)
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], baseline)
        assert len(calls) == 0  # Pending
        
        # Second observation: vessel still outside (confirms departure)
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], baseline)
        
        assert len(calls) == 1
        assert calls[0].call_type == "departure"

    def test_jitter_ignored(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that boundary jitter (second obs closer) is ignored."""
        # First observation: vessel enters
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0  # Pending
        
        # Second observation: vessel moves away (jitter at boundary)
        # Vessel is now just outside (>5 km away)
        test_vessel["latitude"] = 60.0
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        # Jitter ignored, no call emitted, pending cleared
        assert len(calls) == 0
        assert ("oslo_port", "123456789") not in port_tracker._pending_transitions

    def test_multiple_transitions_same_update(
        self, port_tracker: PortCallTracker
    ) -> None:
        """Test vessel entering one port while leaving another in same update."""
        port1 = {
            "id": "port1",
            "name": "Port 1",
            "latitude": 59.9,
            "longitude": 10.75,
            "radius_km": 2.0,
        }
        port2 = {
            "id": "port2",
            "name": "Port 2",
            "latitude": 60.0,
            "longitude": 10.75,
            "radius_km": 2.0,
        }
        
        # Baseline: vessel inside port1
        baseline = {
            "port1": {
                "123456789": PortBaseline(
                    port_id="port1",
                    mmsi="123456789",
                    last_known_inside=True,
                    last_known_timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                )
            }
        }
        
        vessel = {
            "mmsi": "123456789",
            "vessel_name": "Test Ship",
            "latitude": 59.95,  # Now between the two ports
            "longitude": 10.75,
            "msgtime": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            "eta": None,
            "destination": None,
        }
        
        # First observation: vessel leaves port1, enters port2 (pending)
        calls = port_tracker.check_vessel(vessel, [port1, port2], baseline)
        assert len(calls) == 0
        
        # Second observation: vessel still between ports (confirms transitions)
        vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(vessel, [port1, port2], baseline)
        
        # Should get one departure and one arrival
        assert len(calls) == 2
        call_types = {c.call_type for c in calls}
        assert "departure" in call_types
        assert "arrival" in call_types


class TestStaleGapHandling:
    """Test that stale gaps do not fabricate calls."""

    def test_large_gap_clears_pending(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that a gap >24h clears pending state without emitting call."""
        # First observation: vessel enters (pending)
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0
        
        # Long gap (>24 hours)
        test_vessel["msgtime"] = datetime(2024, 1, 3, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        # Gap cleared, no call emitted (does not fabricate)
        assert len(calls) == 0
        assert ("oslo_port", "123456789") not in port_tracker._pending_transitions

    def test_normal_gap_within_threshold(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that a gap within the threshold maintains pending state."""
        # First observation: vessel enters (pending)
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0
        
        # Gap within 24h
        test_vessel["msgtime"] = datetime(2024, 1, 1, 23, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        # Still pending (normal service interruption)
        assert len(calls) == 0
        assert ("oslo_port", "123456789") in port_tracker._pending_transitions


class TestBaselineResumption:
    """Test proper handling of baselines on restart."""

    def test_no_call_on_resume_outside(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that resuming with vessel outside does not emit call."""
        # Baseline: vessel was outside
        baseline = {
            "oslo_port": {
                "123456789": PortBaseline(
                    port_id="oslo_port",
                    mmsi="123456789",
                    last_known_inside=False,
                    last_known_timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                )
            }
        }
        
        # After restart, vessel still outside
        test_vessel["latitude"] = 60.0  # Outside
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], baseline)
        
        assert len(calls) == 0

    def test_no_call_on_resume_inside(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that resuming with vessel inside does not emit call."""
        # Baseline: vessel was inside
        baseline = {
            "oslo_port": {
                "123456789": PortBaseline(
                    port_id="oslo_port",
                    mmsi="123456789",
                    last_known_inside=True,
                    last_known_timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                )
            }
        }
        
        # After restart, vessel still inside
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], baseline)
        
        assert len(calls) == 0


class TestCallAttributes:
    """Test that port call objects have correct attributes."""

    def test_call_has_reported_fields(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that calls include reported ETA and destination."""
        # Get to first confirmation
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0
        
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        assert len(calls) == 1
        call = calls[0]
        assert call.reported_eta == "2024-01-02T10:00:00Z"
        assert call.reported_destination == "Oslo"
        assert call.last_position == (59.9, 10.75)

    def test_call_as_dict(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that call.as_dict() produces a valid event payload."""
        # Confirm a call
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        
        assert len(calls) == 1
        payload = calls[0].as_dict()
        
        assert "port_id" in payload
        assert "port_name" in payload
        assert "mmsi" in payload
        assert "call_type" in payload
        assert "observed_at" in payload
        assert payload["port_id"] == "oslo_port"
        assert payload["call_type"] == "arrival"


class TestDuplicateMessageHandling:
    """Test that repeated messages don't create duplicate calls."""

    def test_same_message_repeated(
        self, port_tracker: PortCallTracker, test_port: dict, test_vessel: dict
    ) -> None:
        """Test that the same message repeated twice creates only one call."""
        # First observation with specific timestamp
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0
        
        # Same message timestamp again (repeated)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 0  # Still pending, same timestamp
        
        # New message confirms
        test_vessel["msgtime"] = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)
        calls = port_tracker.check_vessel(test_vessel, [test_port], {})
        assert len(calls) == 1  # Only one call


class TestClearPending:
    """Test clearing pending state."""

    def test_clear_specific_port(self, port_tracker: PortCallTracker) -> None:
        """Test clearing pending state for a specific port."""
        port_tracker._pending_transitions[("port1", "123")] = (True, datetime.now(UTC))
        port_tracker._pending_transitions[("port2", "123")] = (True, datetime.now(UTC))
        
        port_tracker.clear_pending(port_id="port1")
        
        assert ("port1", "123") not in port_tracker._pending_transitions
        assert ("port2", "123") in port_tracker._pending_transitions

    def test_clear_specific_vessel(self, port_tracker: PortCallTracker) -> None:
        """Test clearing pending state for a specific vessel."""
        port_tracker._pending_transitions[("port1", "123")] = (True, datetime.now(UTC))
        port_tracker._pending_transitions[("port1", "456")] = (True, datetime.now(UTC))
        
        port_tracker.clear_pending(mmsi="123")
        
        assert ("port1", "123") not in port_tracker._pending_transitions
        assert ("port1", "456") in port_tracker._pending_transitions

    def test_clear_all(self, port_tracker: PortCallTracker) -> None:
        """Test clearing all pending state."""
        port_tracker._pending_transitions[("port1", "123")] = (True, datetime.now(UTC))
        port_tracker._pending_transitions[("port2", "456")] = (True, datetime.now(UTC))
        
        port_tracker.clear_pending()
        
        assert len(port_tracker._pending_transitions) == 0
