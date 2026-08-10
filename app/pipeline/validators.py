from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Iterable

from app.models.tc_record import TCRecord


MIN_POINTS_PER_TRACK = 2
MAX_TC_LIFETIME_HOURS = 24 * 60
MAX_POINT_GAP_HOURS = 48.0
MAX_REASONABLE_TRANSLATION_SPEED_KMH = 200.0


def validate_record(record: TCRecord) -> list[str]:
    """
    Return quality problems for one standardised TC record.

    The function does not mutate the record. Ingestion may retain invalid
    records for audit purposes, while consumers can exclude them using
    `is_record_usable`.
    """
    issues: list[str] = []

    if not record.track_id:
        issues.append("Missing track_id.")

    if not record.dataset_id:
        issues.append("Missing dataset_id.")

    if len(record.points) < MIN_POINTS_PER_TRACK:
        issues.append(
            f"Track has fewer than {MIN_POINTS_PER_TRACK} valid points."
        )
        return issues

    times = [point.time for point in record.points]

    if times != sorted(times):
        issues.append("Track points are not time-ordered.")

    for previous, current in zip(record.points, record.points[1:]):
        gap_hours = (current.time - previous.time).total_seconds() / 3600

        if gap_hours <= 0:
            issues.append(
                "Track contains duplicate or non-increasing timestamps."
            )
            break

        if gap_hours > MAX_POINT_GAP_HOURS:
            issues.append(
                f"Track contains a {gap_hours:.1f}-hour gap; "
                "it should have been split into a new segment."
            )
            break

    if record.lifetime_hours is None:
        issues.append("Missing derived lifetime_hours.")
    elif record.lifetime_hours < 0:
        issues.append("Negative lifetime_hours.")
    elif record.lifetime_hours > MAX_TC_LIFETIME_HOURS:
        issues.append(
            f"Lifetime is {record.lifetime_hours:.1f} hours, exceeding "
            f"the {MAX_TC_LIFETIME_HOURS}-hour plausibility limit."
        )

    if record.max_wind_speed is not None and record.max_wind_speed > 450:
        issues.append(
            f"Maximum wind speed is {record.max_wind_speed:.1f} km/h; "
            "check source wind units."
        )

    if record.min_pressure is not None and not 800 <= record.min_pressure <= 1100:
        issues.append(
            f"Minimum pressure is {record.min_pressure:.1f} hPa; "
            "outside the accepted 800–1100 hPa range."
        )

    if (
        record.max_category is not None
        and not 0 <= record.max_category <= 5
    ):
        issues.append("max_category is outside the supported range 0–5.")

    if (
        record.translation_speed_mean is not None
        and record.translation_speed_mean > MAX_REASONABLE_TRANSLATION_SPEED_KMH
    ):
        issues.append(
            f"Mean translation speed is "
            f"{record.translation_speed_mean:.1f} km/h; "
            "check track ordering or coordinates."
        )

    if record.year is None:
        issues.append("Missing genesis calendar year.")

    if record.genesis_time is None:
        issues.append("Missing genesis timestamp.")

    if record.genesis_lat is None or record.genesis_lon is None:
        issues.append("Missing genesis coordinates.")

    return issues


def is_record_usable(record: TCRecord) -> bool:
    """True only when the record passes all scientific plausibility checks."""
    return not validate_record(record)


def validate_records(records: Iterable[TCRecord]) -> dict:
    """
    Validate all records and return a dashboard/API-friendly quality report.

    The records themselves are not removed. DataManager or the dashboard may
    choose to show only `valid_track_ids`, while retaining invalid records in
    `invalid_records` for traceability.
    """
    record_list = list(records)
    issue_counter: Counter[str] = Counter()
    invalid_records: list[dict] = []
    valid_track_ids: list[str] = []
    total_points = 0

    for record in record_list:
        total_points += len(record.points)
        issues = validate_record(record)

        if issues:
            invalid_records.append(
                {
                    "track_id": record.track_id,
                    "dataset_id": record.dataset_id,
                    "point_count": len(record.points),
                    "lifetime_hours": record.lifetime_hours,
                    "issues": issues,
                }
            )
            issue_counter.update(issues)
        else:
            valid_track_ids.append(record.track_id)

    return {
        "total_records": len(record_list),
        "usable_records": len(valid_track_ids),
        "invalid_count": len(invalid_records),
        "total_points": total_points,
        "valid_track_ids": valid_track_ids,
        "invalid_records": invalid_records,
        "issue_counts": dict(issue_counter),
    }