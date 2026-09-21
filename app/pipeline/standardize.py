"""

standardize.py
The standardize_records function takes a list of TCRecord objects and standardizes their attributes based on the source file name and other context. It ensures that required fields are populated, sorts the points in each record by time, and recalculates dependent summary fields. The function returns a list of standardized TCRecord objects.

function: standardize_records(records, source_file=None)
    - Takes an iterable of TCRecord objects and an optional source file path.
    - Standardizes the attributes of each TCRecord based on the source file name and other context.
    - Ensures that required fields (region, scenario, model, tracker) are populated.
    - Sorts the points in each record by time.
    - Re-validates each record to recalculate dependent summary fields.
    - Returns a list of standardized TCRecord objects.

Parameters:
    - records: An iterable of TCRecord objects to be standardized.
    - source_file: An optional string or Path representing the source file path.
    - soure_path: A Path object representing the source file path, derived from source_file if provided.
    - standardised: A list to hold the standardized TCRecord objects.

Returns:
    - standardised: A list of standardized TCRecord objects with updated attributes and recalculated summary fields.

"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.models.tc_record import TCRecord


def standardize_records(
    records: Iterable[TCRecord],
    source_file: str | Path | None = None,) -> list[TCRecord]:
    source_path = Path(source_file) if source_file else None
    standardised: list[TCRecord] = []

    for record in records:
        if source_path is not None:
            if not record.source_file:
                record.source_file = str(source_path)
            if not record.dataset_id:
                record.dataset_id = source_path.stem

        record.points = sorted(record.points, key=lambda point: point.time)

        if not record.region:
            record.region = "Australia"
        if not record.scenario:
            record.scenario = "future"
        if not record.model:
            filename = (record.source_file or "").lower()
            if "barpa" in filename:
                record.model = "BARPA"
            elif "ccam" in filename:
                record.model = "CCAM"
        if not record.tracker:
            filename = (record.source_file or "").lower()
            if "_cdd_" in filename:
                record.tracker = "CDD"
            elif "_te_" in filename:
                record.tracker = "TE"

        # Re-validate to recalculate dependent summary fields.
        standardised.append(TCRecord.model_validate(record.model_dump()))

    return standardised