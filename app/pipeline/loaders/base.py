from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Optional

from app.models.tc_record import TCPoint, TCRecord


class BaseTCLoader(ABC):
    def __init__(self, dataset_id: str, source_file: str | Path, **context: Any) -> None:
        self.dataset_id = dataset_id
        self.source_file = Path(source_file)
        self.context = context

    @abstractmethod
    def load(self) -> list[TCRecord]:
        raise NotImplementedError

    def build_record(self, track_id: str, points: Iterable[TCPoint], **kwargs: Any) -> TCRecord:
        payload = {
            'track_id': track_id,
            'dataset_id': self.dataset_id,
            'source_file': str(self.source_file),
            **self.context,
            **kwargs,
            'points': list(points),
        }
        return TCRecord.model_validate(payload)

    @staticmethod
    def to_float(value: Any) -> Optional[float]:
        if value in (None, '', 'NA', 'NAN', 'nan'):
            return None
        return float(value)

    @staticmethod
    def to_int(value: Any) -> Optional[int]:
        if value in (None, '', 'NA', 'NAN', 'nan'):
            return None
        return int(float(value))