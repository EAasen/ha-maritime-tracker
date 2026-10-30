"""Vessel AIS status-transition detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from .client import VesselData

_LOGGER = logging.getLogger(__name__)

MAX_VESSEL_STATUS_BASELINES = 2000
FUTURE_TIMESTAMP_TOLERANCE = timedelta(minutes=5)
_UNKNOWN_STATUSES = frozenset({"unknown", "undefined", "not available", "n/a"})


def _as_utc(value: datetime) -> datetime:
    """Normalize a timestamp to UTC, treating naive source values as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_source_time(value: str | None) -> datetime | None:
    """Parse an optional ISO-8601 AIS source timestamp."""
    if value is None or not value.strip():
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
    except ValueError:
        return None


@dataclass(frozen=True)
class VesselStatusBaseline:
    """Most recent status observation used to detect a continuous transition."""

    mmsi: str
    status: str | None
    source_msgtime: str | None
    observation_time: datetime
    name: str
    source: str | None
    latitude: float
    longitude: float
    continuity_valid: bool = True

    def to_dict(self) -> dict[str, str | float | bool | None]:
        """Return a JSON-serializable representation."""
        return {
            "status": self.status,
            "source_msgtime": self.source_msgtime,
            "observation_time": self.observation_time.isoformat(),
            "name": self.name,
            "source": self.source,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "continuity_valid": self.continuity_valid,
        }

    @classmethod
    def from_dict(cls, mmsi: str, data: object) -> VesselStatusBaseline:
        """Validate and restore one persisted baseline."""
        if not isinstance(data, dict):
            raise ValueError(f"Baseline for MMSI {mmsi} must be an object")

        try:
            observation_time = datetime.fromisoformat(
                str(data["observation_time"]).replace("Z", "+00:00")
            )
            status = data["status"]
            source_msgtime = data["source_msgtime"]
            name = data["name"]
            source = data["source"]
            latitude = data["latitude"]
            longitude = data["longitude"]
            continuity_valid = data["continuity_valid"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid baseline for MMSI {mmsi}") from exc

        if (
            (status is not None and not isinstance(status, str))
            or (source_msgtime is not None and not isinstance(source_msgtime, str))
            or not isinstance(name, str)
            or (source is not None and not isinstance(source, str))
            or not isinstance(latitude, int | float)
            or not isinstance(longitude, int | float)
            or not isinstance(continuity_valid, bool)
        ):
            raise ValueError(f"Invalid baseline fields for MMSI {mmsi}")

        return cls(
            mmsi=mmsi,
            status=status,
            source_msgtime=source_msgtime,
            observation_time=_as_utc(observation_time),
            name=name,
            source=source,
            latitude=float(latitude),
            longitude=float(longitude),
            continuity_valid=continuity_valid,
        )


@dataclass(frozen=True)
class VesselStatusTransition:
    """A confirmed change between two consecutive valid AIS status reports."""

    mmsi: str
    name: str
    old_status: str
    new_status: str
    source_msgtime: str | None
    observation_time: datetime
    source: str | None
    latitude: float
    longitude: float

    def as_event_data(self, entry_id: str) -> dict[str, object]:
        """Return the Home Assistant event payload."""
        return {
            "entry_id": entry_id,
            "mmsi": self.mmsi,
            "name": self.name,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "source_msgtime": self.source_msgtime,
            "observation_time": self.observation_time.isoformat(),
            "source": self.source,
            "position": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
        }


class VesselEventTracker:
    """Track bounded per-entry baselines and decide status transitions."""

    def __init__(
        self,
        entry_id: str,
        stale_timeout: int,
        max_baselines: int = MAX_VESSEL_STATUS_BASELINES,
    ) -> None:
        self.entry_id = entry_id
        self.stale_timeout = max(0, stale_timeout)
        self.max_baselines = max(1, max_baselines)
        self._baselines: dict[str, VesselStatusBaseline] = {}

    @property
    def baselines(self) -> dict[str, VesselStatusBaseline]:
        """Return a copy of the current status baselines."""
        return dict(self._baselines)

    def restore(self, baselines: dict[str, VesselStatusBaseline], now: datetime) -> bool:
        """Restore baselines, dropping expired or over-limit records."""
        self._baselines = dict(baselines)
        changed = self.prune(now)
        if len(self._baselines) > self.max_baselines:
            ordered = sorted(
                self._baselines.values(),
                key=lambda baseline: baseline.observation_time,
            )
            for baseline in ordered[: len(self._baselines) - self.max_baselines]:
                self._baselines.pop(baseline.mmsi)
                _LOGGER.warning(
                    "Evicted restored status baseline for MMSI=%s in entry %s "
                    "because the %d-vessel limit was exceeded",
                    baseline.mmsi,
                    self.entry_id,
                    self.max_baselines,
                )
            changed = True
        return changed

    def prune(self, now: datetime) -> bool:
        """Expire baselines older than the configured continuity timeout."""
        cutoff = _as_utc(now) - timedelta(seconds=self.stale_timeout)
        expired = [
            mmsi for mmsi, baseline in self._baselines.items() if baseline.observation_time < cutoff
        ]
        for mmsi in expired:
            del self._baselines[mmsi]
        return bool(expired)

    def observe(
        self, vessel: VesselData, now: datetime
    ) -> tuple[VesselStatusTransition | None, bool]:
        """Process one observation and report its transition and state change."""
        now = _as_utc(now)
        changed = self.prune(now)
        baseline = self._baselines.get(vessel.mmsi)
        observation_time = _as_utc(vessel.observation_time)
        source_time = _parse_source_time(vessel.source_msgtime)
        has_source_time = bool(vessel.source_msgtime and vessel.source_msgtime.strip())

        if has_source_time and source_time is None:
            return None, self._invalidate(baseline) or changed

        effective_time = source_time or observation_time
        if effective_time > now + FUTURE_TIMESTAMP_TOLERANCE or effective_time < now - timedelta(
            seconds=self.stale_timeout
        ):
            return None, self._invalidate(baseline) or changed

        if baseline is not None and not self._is_newer(baseline, source_time, observation_time):
            return None, changed

        status = vessel.status.strip() if vessel.status else ""
        if not status or status.casefold() in _UNKNOWN_STATUSES:
            if baseline is not None:
                updated = self._from_observation(vessel, None, False, observation_time)
                self._baselines[vessel.mmsi] = updated
                self._enforce_limit()
                return None, True
            return None, changed

        transition: VesselStatusTransition | None = None
        if baseline is not None and baseline.continuity_valid:
            gap = observation_time - baseline.observation_time
            if (
                gap <= timedelta(seconds=self.stale_timeout)
                and baseline.status is not None
                and baseline.status != status
            ):
                transition = VesselStatusTransition(
                    mmsi=vessel.mmsi,
                    name=vessel.name,
                    old_status=baseline.status,
                    new_status=status,
                    source_msgtime=vessel.source_msgtime,
                    observation_time=observation_time,
                    source=vessel.source,
                    latitude=vessel.latitude,
                    longitude=vessel.longitude,
                )

        self._baselines[vessel.mmsi] = self._from_observation(
            vessel, status, True, observation_time
        )
        self._enforce_limit()
        return transition, True

    def _is_newer(
        self,
        baseline: VesselStatusBaseline,
        source_time: datetime | None,
        observation_time: datetime,
    ) -> bool:
        """Reject duplicate or out-of-order observations."""
        previous_source_time = _parse_source_time(baseline.source_msgtime)
        if source_time is not None and previous_source_time is not None:
            return source_time > previous_source_time
        return observation_time > baseline.observation_time

    def _invalidate(self, baseline: VesselStatusBaseline | None) -> bool:
        """Invalidate continuity without letting an implausible time poison ordering."""
        if baseline is None or not baseline.continuity_valid:
            return False
        self._baselines[baseline.mmsi] = replace(baseline, continuity_valid=False)
        return True

    @staticmethod
    def _from_observation(
        vessel: VesselData,
        status: str | None,
        continuity_valid: bool,
        observation_time: datetime,
    ) -> VesselStatusBaseline:
        return VesselStatusBaseline(
            mmsi=vessel.mmsi,
            status=status,
            source_msgtime=vessel.source_msgtime,
            observation_time=observation_time,
            name=vessel.name,
            source=vessel.source,
            latitude=vessel.latitude,
            longitude=vessel.longitude,
            continuity_valid=continuity_valid,
        )

    def _enforce_limit(self) -> None:
        """Evict the least recently observed baseline when over capacity."""
        if len(self._baselines) <= self.max_baselines:
            return
        oldest = min(
            self._baselines.values(),
            key=lambda baseline: baseline.observation_time,
        )
        del self._baselines[oldest.mmsi]
        _LOGGER.warning(
            "Evicted oldest status baseline for MMSI=%s in entry %s "
            "because the %d-vessel limit was exceeded",
            oldest.mmsi,
            self.entry_id,
            self.max_baselines,
        )
