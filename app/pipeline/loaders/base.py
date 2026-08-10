from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Optional

from app.models.tc_record import TCPoint, TCRecord


class BaseTCLoader(ABC):
    def __init__(
        self,
        dataset_id: str,
        source_file: str | Path,
        **context: Any,
    ) -> None:
        self.dataset_id = dataset_id
        self.source_file = Path(source_file)
        self.context = context

    @abstractmethod
    def load(self) -> list[TCRecord]:
        raise NotImplementedError

    def build_record(
        self,
        track_id: str,
        points: Iterable[TCPoint],
        **kwargs: Any,
    ) -> TCRecord:
        payload = {
            "track_id": str(track_id),
            "dataset_id": self.dataset_id,
            "source_file": str(self.source_file),
            **self.context,
            **kwargs,
            "points": list(points),
        }
        return TCRecord.model_validate(payload)

    @staticmethod
    def to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        value = str(value).strip()
        if value.lower() in {"", "na", "nan", "none", "null"}:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def to_int(value: Any) -> Optional[int]:
        number = BaseTCLoader.to_float(value)
        return int(number) if number is not None else None

    @staticmethod
    def to_bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        value = str(value).strip().lower()
        if value in {"1", "true", "yes", "y"}:
            return True
        if value in {"0", "false", "no", "n"}:
            return False
        return None

    @staticmethod
    def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            str(key).strip().lower(): (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in row.items()
            if key is not None
        }
    @staticmethod
    def metres_per_second_to_kmh(value: float | None) -> float | None:
        """Convert a wind speed from metres per second to kilometres per hour."""
        if value is None:
            return None
        return value * 3.6