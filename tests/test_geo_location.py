"""Tests for the geo_location platform and the tracked-area zone."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.marinetraffic_tracker.const import (
    ATTR_MMSI,
    ATTR_VESSEL_NAME,
    CONF_EAST,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NORTH,
    CONF_RADIUS_KM,
    CONF_SOUTH,
    CONF_TRACKING_MODE,
    CONF_WEST,
    GEO_LOCATION_SOURCE,
    TRACKING_MODE_BOX,
    TRACKING_MODE_RADIUS,
)
from custom_components.marinetraffic_tracker.geo_filter import area_centre_and_radius
from custom_components.marinetraffic_tracker.geo_location import MarineTrafficVesselLocation

from .conftest import MOCK_VESSEL_PASSENGER

_RADIUS_CONFIG = {
    CONF_TRACKING_MODE: TRACKING_MODE_RADIUS,
    CONF_LATITUDE: 59.9,
    CONF_LONGITUDE: 10.7,
    CONF_RADIUS_KM: 50.0,
}


def _make_entity(vessels: dict | None = None) -> MarineTrafficVesselLocation:
    coordinator = MagicMock()
    coordinator.data = vessels if vessels is not None else {"555555555": MOCK_VESSEL_PASSENGER}
    coordinator.last_update_success = True
    return MarineTrafficVesselLocation(coordinator, "555555555", 59.9, 10.7)


def test_source_matches_documented_map_card_value() -> None:
    """The source is what users put in a Map card's geo_location_sources."""
    assert _make_entity().source == GEO_LOCATION_SOURCE == "marinetraffic_tracker"


def test_entity_has_no_unique_id() -> None:
    """Markers must stay out of the entity registry."""
    assert _make_entity().unique_id is None


def test_position_and_distance_come_from_coordinator() -> None:
    """Latitude, longitude and distance reflect the current vessel observation."""
    entity = _make_entity()
    assert entity.latitude == MOCK_VESSEL_PASSENGER.latitude
    assert entity.longitude == MOCK_VESSEL_PASSENGER.longitude
    assert entity.distance == pytest.approx(0.0, abs=0.5)
    assert entity.name == "FJORD QUEEN"


def test_unavailable_when_vessel_purged() -> None:
    """A vessel removed from the coordinator makes its marker unavailable."""
    entity = _make_entity(vessels={})
    assert entity.available is False
    assert entity.latitude is None
    assert entity.distance is None
    assert entity.extra_state_attributes == {ATTR_MMSI: "555555555"}


def test_extra_state_attributes_expose_ais_telemetry() -> None:
    """Map popups need the key AIS fields."""
    attrs = _make_entity().extra_state_attributes
    assert attrs[ATTR_MMSI] == "555555555"
    assert attrs[ATTR_VESSEL_NAME] == "FJORD QUEEN"


def test_area_centre_and_radius_radius_mode() -> None:
    """Radius mode maps straight onto the configured centre and radius."""
    assert area_centre_and_radius(_RADIUS_CONFIG) == (59.9, 10.7, 50.0)


def test_area_centre_and_radius_box_mode_circumscribes_box() -> None:
    """Box mode returns the centre and a radius reaching the box corner."""
    result = area_centre_and_radius(
        {
            CONF_TRACKING_MODE: TRACKING_MODE_BOX,
            CONF_NORTH: 60.0,
            CONF_EAST: 11.0,
            CONF_SOUTH: 59.0,
            CONF_WEST: 10.0,
        }
    )
    assert result is not None
    latitude, longitude, radius_km = result
    assert latitude == pytest.approx(59.5)
    assert longitude == pytest.approx(10.5)
    # Half-diagonal of a 1° x 1° box at ~59.5°N.
    assert radius_km == pytest.approx(61.0, abs=2.0)


def test_area_centre_and_radius_returns_none_when_unconfigured() -> None:
    """An incomplete config yields None rather than raising."""
    assert area_centre_and_radius({CONF_TRACKING_MODE: TRACKING_MODE_RADIUS}) is None
