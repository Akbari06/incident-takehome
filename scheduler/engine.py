"""Core scheduling utilities shared between the CLI and web backends."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import tee
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Segment:
    """Represents a contiguous assignment for a single user."""

    start: datetime
    end: datetime
    user: str

    def clamp(self, window_start: datetime, window_end: datetime) -> Optional["Segment"]:
        """Return a new segment trimmed to the requested window or None if it falls outside.

        Args:
            window_start: Inclusive lower bound for the returned segment.
            window_end: Exclusive upper bound for the returned segment.

        Returns:
            A trimmed ``Segment`` if the original overlaps the window, otherwise ``None``.
        """

        clamped_start = max(self.start, window_start)
        clamped_end = min(self.end, window_end)
        if clamped_start >= clamped_end:
            return None
        return Segment(clamped_start, clamped_end, self.user)


def parse_iso8601(value: str) -> datetime:
    """Convert an ISO-8601 string (allowing a trailing ``Z``) into a timezone-aware datetime.

    Args:
        value: Timestamp encoded as ISO-8601.

    Returns:
        A ``datetime`` normalised to UTC.
    """

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def format_iso8601(value: datetime) -> str:
    """Serialize a timezone-aware ``datetime`` into ISO-8601 with a trailing ``Z`` suffix."""

    return (
        value.astimezone(timezone.utc)
        .replace(tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def validate_users(value) -> List[str]:
    """Ensure the schedule contains a non-empty list of user identifiers.

    Args:
        value: Raw ``users`` entry from the schedule payload.

    Returns:
        The validated list of user strings.

    Raises:
        SystemExit: If the value is missing, empty, or contains non-strings.
    """

    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise SystemExit("Schedule users must be a non-empty array of strings")
    return value


def parse_schedule(data: dict) -> Tuple[List[str], datetime, int]:
    """Extract scheduling metadata from a schedule payload.

    Args:
        data: Dictionary containing schedule configuration.

    Returns:
        A tuple of ``(users, handover_start, interval_days)`` ready for downstream processing.
    """

    try:
        users_raw = data["users"]
        handover_start_raw = data["handover_start_at"]
        interval_days_raw = data["handover_interval_days"]
    except KeyError as exc:
        raise SystemExit(f"Missing key in schedule: {exc}") from exc

    users = validate_users(users_raw)
    handover_start = parse_iso8601(handover_start_raw)
    try:
        interval_days = int(interval_days_raw)
    except (TypeError, ValueError) as exc:
        raise SystemExit("handover_interval_days must be an integer") from exc
    if interval_days <= 0:
        raise SystemExit("handover_interval_days must be positive")

    return users, handover_start, interval_days


def parse_overrides(data) -> List[Segment]:
    """Normalise override definitions into ``Segment`` instances.

    Args:
        data: Raw array of overrides supplied by the caller.

    Returns:
        A list of override segments sorted in the order they were declared.
    """

    if data is None:
        return []
    if not isinstance(data, list):
        raise SystemExit("Overrides file must contain a JSON array")

    overrides: List[Segment] = []
    for idx, entry in enumerate(data):
        try:
            user = entry["user"]
            start_at_raw = entry["start_at"]
            end_at_raw = entry["end_at"]
        except KeyError as exc:
            raise SystemExit(f"Missing key in overrides[{idx}]: {exc}") from exc
        if not isinstance(user, str):
            raise SystemExit(f"Override user must be a string (overrides[{idx}])")

        start_at = parse_iso8601(start_at_raw)
        end_at = parse_iso8601(end_at_raw)
        if end_at <= start_at:
            raise SystemExit("Override end_at must be after start_at")
        overrides.append(Segment(start_at, end_at, user))
    return overrides


def build_rotation(
    users: Sequence[str],
    handover_start: datetime,
    interval_days: int,
    window_start: datetime,
    window_end: datetime,
) -> List[Segment]:
    """Create the base rotation segments that would exist without overrides.

    Args:
        users: Sequence of user identifiers in rotation order.
        handover_start: Datetime marking the beginning of the initial shift.
        interval_days: Number of days each shift lasts.
        window_start: Inclusive lower bound for generated data.
        window_end: Exclusive upper bound for generated data.

    Returns:
        A list of rotation segments that cover the requested window.
    """

    interval = timedelta(days=interval_days)
    steps = (window_start - handover_start) // interval
    first_shift_start = handover_start + steps * interval
    while first_shift_start > window_start:
        first_shift_start -= interval
        steps -= 1

    segments: List[Segment] = []
    user_count = len(users)
    shift_index = steps % user_count
    current_start = first_shift_start

    while current_start < window_end:
        segments.append(
            Segment(
                start=current_start,
                end=current_start + interval,
                user=users[shift_index],
            )
        )
        current_start += interval
        shift_index = (shift_index + 1) % user_count

    return segments


def pairwise(values: Iterable[datetime]) -> Iterator[Tuple[datetime, datetime]]:
    """Yield adjacent pairs from a monotonic sequence of datetimes."""

    first, second = tee(values)
    next(second, None)
    for current, nxt in zip(first, second):
        yield current, nxt


def compose_schedule(
    base_segments: Sequence[Segment],
    overrides: Sequence[Segment],
    window_start: datetime,
    window_end: datetime,
) -> List[Segment]:
    """Combine base rotation data with overrides to form the final timeline.

    Args:
        base_segments: Rotation segments generated from the core schedule.
        overrides: Override segments that should take precedence when overlapping.
        window_start: Inclusive lower bound for the response.
        window_end: Exclusive upper bound for the response.

    Returns:
        A list of non-overlapping ``Segment`` objects covering the requested window.
    """

    weighted_segments: List[Tuple[int, Segment]] = []
    for segment in base_segments:
        weighted_segments.append((0, segment))
    for order, segment in enumerate(overrides, start=1):
        weighted_segments.append((order, segment))

    boundaries = {window_start, window_end}
    for _, segment in weighted_segments:
        clamped = segment.clamp(window_start, window_end)
        if clamped is None:
            continue
        boundaries.add(clamped.start)
        boundaries.add(clamped.end)

    sorted_boundaries = sorted(boundaries)
    result: List[Segment] = []

    for start, end in pairwise(sorted_boundaries):
        if start >= end:
            continue

        covering = [
            (priority, segment.user)
            for priority, segment in weighted_segments
            if segment.start <= start and segment.end >= end
        ]
        if not covering:
            continue

        _, user = max(covering, key=lambda item: item[0])
        if result and result[-1].user == user and result[-1].end == start:
            result[-1] = Segment(result[-1].start, end, user)
        else:
            result.append(Segment(start, end, user))

    return result


def generate_schedule(
    schedule_data: dict,
    overrides_data,
    window_start: datetime,
    window_end: datetime,
) -> List[Segment]:
    """High-level helper that validates inputs and produces the final schedule.

    Args:
        schedule_data: Schedule definition payload.
        overrides_data: Iterable of override definitions.
        window_start: Inclusive lower bound for generated entries.
        window_end: Exclusive upper bound for generated entries.

    Returns:
        A list of merged ``Segment`` objects ready for serialisation.
    """

    if window_end <= window_start:
        raise SystemExit("--until must be after --from")

    users, handover_start, interval_days = parse_schedule(schedule_data)
    base_segments = build_rotation(users, handover_start, interval_days, window_start, window_end)
    overrides = parse_overrides(overrides_data)

    return compose_schedule(base_segments, overrides, window_start, window_end)


def to_payload(segments: Sequence[Segment]) -> List[dict]:
    """Convert ``Segment`` objects to JSON-serialisable dictionaries."""

    return [
        {
            "user": segment.user,
            "start_at": format_iso8601(segment.start),
            "end_at": format_iso8601(segment.end),
        }
        for segment in segments
    ]
