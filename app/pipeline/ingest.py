from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Protocol

from app.config import (
    DATASET_TYPE_BY_FILE,
    SUPPORTED_DATASET_TYPES,
)
from app.models.tc_record import TCRecord
from app.pipeline.standardize import standardize_records
from app.pipeline.validators import (
    ValidationReport,
    validate_records,
)


class DatasetLoader(Protocol):
    dataset_type: str

    def supports(
        self,
        path: Path,
        dataset_type: Optional[str] = None,
    ) -> bool:
        ...

    def load(self, path: Path) -> object:
        ...


@dataclass
class IngestionResult:
    source: Path
    dataset_type: str
    records: list[TCRecord]
    validation: ValidationReport
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.validation.is_valid


def infer_dataset_type(path: str | Path) -> Optional[str]:
    source_path = Path(path)
    filename = source_path.name.lower()

    configured_type = DATASET_TYPE_BY_FILE.get(filename)
    if configured_type:
        return configured_type

    if filename.startswith("barpa"):
        return "barpa"

    if filename.startswith("ccam"):
        return "ccam"

    return None


def build_default_loaders() -> list[DatasetLoader]:
    from app.pipeline.loaders import create_default_loaders
    return create_default_loaders()


def unpack_loader_result(
    raw_result: object,
) -> tuple[list[TCRecord], dict[str, Any]]:
    if hasattr(raw_result, "records"):
        records = list(getattr(raw_result, "records"))
        metadata = dict(getattr(raw_result, "metadata", {}) or {})
        return records, metadata

    if isinstance(raw_result, Mapping):
        records = list(raw_result.get("records", []))
        metadata = dict(raw_result.get("metadata", {}) or {})
        return records, metadata

    if isinstance(raw_result, Iterable):
        return list(raw_result), {}

    raise TypeError(
        f"The selected loader returned an unsupported result type: {type(raw_result).__name__}"
    )


class Ingestor:
    def __init__(
        self,
        loaders: Optional[list[DatasetLoader]] = None,
        strict_validation: bool = False,
    ) -> None:
        self._loaders = (
            list(loaders)
            if loaders is not None
            else build_default_loaders()
        )
        self.strict_validation = strict_validation

    def select_loader(
        self,
        path: Path,
        dataset_type: str,
    ) -> DatasetLoader:
        for loader in self._loaders:
            if loader.supports(path, dataset_type):
                return loader

        registered = ", ".join(
            loader.__class__.__name__ for loader in self._loaders
        )

        raise ValueError(
            f"No loader supports {path.name!r} as dataset type "
            f"{dataset_type!r}. Registered loaders: {registered or 'none'}."
        )

    def ingest(
        self,
        source: str | Path,
        dataset_type: Optional[str] = None,
    ) -> IngestionResult:
        path = Path(source).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Dataset file does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Dataset source is not a file: {path}")

        resolved_type = (
            str(dataset_type).strip().lower()
            if dataset_type
            else infer_dataset_type(path)
        )

        if not resolved_type:
            raise ValueError(
                f"Could not infer the dataset type for {path.name!r}."
            )

        if resolved_type not in SUPPORTED_DATASET_TYPES:
            raise ValueError(
                f"Unsupported dataset type {resolved_type!r}. "
                f"Supported types: {sorted(SUPPORTED_DATASET_TYPES)}"
            )

        loader = self.select_loader(path, resolved_type)
        raw_result = loader.load(path)
        raw_records, loader_metadata = unpack_loader_result(raw_result)

        for index, record in enumerate(raw_records):
            if not isinstance(record, TCRecord):
                raise TypeError(
                    f"{loader.__class__.__name__} returned an invalid "
                    f"record at position {index}: {type(record).__name__}. "
                    f"Expected TCRecord."
                )

        standard_records = standardize_records(raw_records)
        validation = validate_records(
            standard_records,
            strict=self.strict_validation,
        )

        metadata = {
            "loader": loader.__class__.__name__,
            "source_filename": path.name,
            "source_path": str(path),
            "record_count": len(standard_records),
            "validation_error_count": validation.error_count,
            "validation_warning_count": validation.warning_count,
            **loader_metadata,
        }

        return IngestionResult(
            source=path,
            dataset_type=resolved_type,
            records=standard_records,
            validation=validation,
            metadata=metadata,
        )