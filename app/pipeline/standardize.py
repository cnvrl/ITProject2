from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.models.tc_record import TCRecord


def standardize_records(
    records: Iterable[TCRecord],
    source_file: str | Path | None = None,
) -> list[TCRecord]:
    """
    Apply safe cross-dataset defaults without discarding data.

    Loaders retain precedence: only missing fields are populated here.
    """
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