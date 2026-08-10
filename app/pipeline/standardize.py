from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.models.tc_record import TCRecord


def standardize_records(records: Iterable[TCRecord], source_file: str | Path | None = None) -> list[TCRecord]:
    standardized: list[TCRecord] = []
    for record in records:
        if source_file and not record.source_file:
            record.source_file = str(source_file)
        if not record.dataset_id and source_file:
            record.dataset_id = Path(source_file).stem
        record.points = sorted(record.points, key=lambda p: p.time)
        standardized.append(record)
    return standardized