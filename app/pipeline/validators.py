from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional

from app.models.tc_record import TCRecord, TrackPoint


Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    record_id: Optional[str] = None
    point_index: Optional[int] = None


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add(
        self,
        severity: Severity,
        code: str,
        message: str,
        record_id: Optional[str] = None,
        point_index: Optional[int] = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=severity,
                code=code,
                message=message,
                record_id=record_id,
                point_index=point_index,
            )
        )

    def extend(self, other: ValidationReport) -> None:
        self.issues.extend(other.issues)


class ValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        message = (
            f"Validation failed with "
            f"{report.error_count} error(s) and "
            f"{report.warning_count} warning(s)."
        )
        super().__init__(message)


def validate_point(point: TrackPoint, record_id: str, point_index: int) -> ValidationReport:
    report = ValidationReport()

    if not -90 <= point.lat <= 90:
        report.add(
            "error",
            "invalid_latitude",
            f"Latitude {point.lat} is outside -90 to 90.",
            record_id,
            point_index,
        )

    if not -180 <= point.lon <= 180:
        report.add(
            "error",
            "invalid_longitude",
            f"Longitude {point.lon} is outside -180 to 180.",
            record_id,
            point_index,
        )

    if point.wind_speed is not None and point.wind_speed < 0:
        report.add(
            "error",
            "negative_wind_speed",
            "Wind speed cannot be negative.",
            record_id,
            point_index,
        )

    if point.category is not None and not 0 <= point.category <= 5:
        report.add(
            "error",
            "invalid_category",
            "Cyclone category must be between 0 and 5.",
            record_id,
            point_index,
        )

    if point.pressure is not None and point.pressure <= 0:
        report.add(
            "warning",
            "invalid_pressure",
            "Pressure should be greater than zero.",
            record_id,
            point_index,
        )

    return report


def validate_record(record: TCRecord) -> ValidationReport:
    report = ValidationReport()
    record_id = str(record.track_id or "unknown")

    if not str(record.dataset_id).strip():
        report.add("error", "missing_dataset_id", "The record has no dataset identifier.", record_id)

    if not str(record.track_id).strip():
        report.add("error", "missing_track_id", "The record has no track identifier.", record_id)

    if not str(record.model).strip():
        report.add("error", "missing_dataset", "The record has no BARPA/CCAM dataset value.", record_id)

    if not str(record.source_model).strip():
        report.add("error", "missing_driving_model", "The record has no driving-model value.", record_id)

    if not str(record.tracker).strip():
        report.add("error", "missing_tracker", "The record has no tracker value.", record_id)

    if record.season is None and record.year is None:
        report.add("error", "missing_season", "The record has no season or year.", record_id)

    if not record.points:
        report.add("error", "missing_points", "The cyclone track contains no observations.", record_id)
        return report

    previous_timestamp = None
    seen_steps: set[int] = set()

    for point_index, point in enumerate(record.points):
        report.extend(validate_point(point, record_id, point_index))

        if point.step is not None:
            if point.step in seen_steps:
                report.add(
                    "warning",
                    "duplicate_step",
                    f"Track step {point.step} is duplicated.",
                    record_id,
                    point_index,
                )
            seen_steps.add(point.step)

        if point.timestamp is not None:
            if previous_timestamp is not None and point.timestamp < previous_timestamp:
                report.add(
                    "warning",
                    "unordered_timestamp",
                    "Track timestamps are not chronological.",
                    record_id,
                    point_index,
                )
            previous_timestamp = point.timestamp

    if record.max_category is not None and not 0 <= record.max_category <= 5:
        report.add("error", "invalid_max_category", "Maximum category must be between 0 and 5.", record_id)

    if record.max_wind_speed is not None and record.max_wind_speed < 0:
        report.add("error", "invalid_max_wind", "Maximum wind speed cannot be negative.", record_id)

    if record.lifetime_hours is not None and record.lifetime_hours < 0:
        report.add("error", "invalid_lifetime", "Cyclone lifetime cannot be negative.", record_id)

    return report


def validate_records(
    records: Iterable[TCRecord],
    strict: bool = False,
) -> ValidationReport:
    report = ValidationReport()
    seen_identities: set[tuple] = set()

    for record in records:
        report.extend(validate_record(record))

        if record.identity in seen_identities:
            report.add(
                "error",
                "duplicate_track_identity",
                "Another record has the same dataset, model, tracker, season, and raw track ID.",
                record.track_id,
            )

        seen_identities.add(record.identity)

    if strict and not report.is_valid:
        raise ValidationError(report)

    return report