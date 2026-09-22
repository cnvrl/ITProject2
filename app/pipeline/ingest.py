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
    """Interface implemented by dataset-specific loaders."""

    dataset_type: str

    def supports(
        self,
        path: Path,
        dataset_type: Optional[str] = None,
    ) -> bool:
        """Return whether this loader supports the supplied file."""
        ...

    def load(self, path: Path) -> object:
        """Load records from the supplied file."""
        ...


@dataclass
class IngestionResult:
    """Result returned after loading, standardising, and validating a file."""

    source: Path
    dataset_type: str
    records: list[TCRecord]
    validation: ValidationReport
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.validation.is_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "dataset_type": self.dataset_type,
            "records": self.records,
            "validation": self.validation,
            "metadata": dict(self.metadata),
            "is_valid": self.is_valid,
        }

    def get(
        self,
        key: str,
        default: object = None,
    ) -> object:
        """Provide compatibility with code expecting dictionary results."""

        return self.to_dict().get(key, default)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def infer_dataset_type(path: str | Path) -> Optional[str]:
    """Infer the dataset type from a known filename or filename prefix."""

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
    """Create the BARPA and CCAM production loaders."""

    from app.pipeline.loaders import create_default_loaders

    return create_default_loaders()


def unpack_loader_result(
    raw_result: object,
) -> tuple[list[TCRecord], dict[str, Any]]:
    """
    Convert supported loader return types into records and metadata.

    The clean loaders return LoaderResult objects, but Mapping and iterable
    results remain supported for compatibility.
    """

    if hasattr(raw_result, "records"):
        records = list(
            getattr(raw_result, "records")
        )

        metadata = dict(
            getattr(
                raw_result,
                "metadata",
                {},
            )
            or {}
        )

        return records, metadata

    if isinstance(raw_result, Mapping):
        records = list(
            raw_result.get(
                "records",
                [],
            )
        )

        metadata = dict(
            raw_result.get(
                "metadata",
                {},
            )
            or {}
        )

        return records, metadata

    if isinstance(raw_result, Iterable):
        return list(raw_result), {}

    raise TypeError(
        "The selected loader returned an unsupported result type: "
        f"{type(raw_result).__name__}"
    )


class Ingestor:
    """
    Coordinate loader selection, standardisation, and validation.

    Runtime flow:

        source file
        -> dataset loader
        -> TCRecord objects
        -> standardisation
        -> validation
        -> IngestionResult
    """

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

    @property
    def loaders(self) -> tuple[DatasetLoader, ...]:
        """Return the registered loaders as an immutable tuple."""

        return tuple(self._loaders)

    def register_loader(
        self,
        loader: DatasetLoader,
    ) -> None:
        """Register an additional dataset loader."""

        self._loaders.append(loader)

    def select_loader(
        self,
        path: Path,
        dataset_type: str,
    ) -> DatasetLoader:
        """Select the first loader supporting the file and dataset type."""

        for loader in self._loaders:
            if loader.supports(
                path,
                dataset_type,
            ):
                return loader

        registered = ", ".join(
            loader.__class__.__name__
            for loader in self._loaders
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
        """Load, standardise, and validate one dataset file."""

        path = Path(source).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset file does not exist: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Dataset source is not a file: {path}"
            )

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

        loader = self.select_loader(
            path,
            resolved_type,
        )

        raw_result = loader.load(path)

        raw_records, loader_metadata = (
            unpack_loader_result(raw_result)
        )

        for index, record in enumerate(raw_records):
            if not isinstance(record, TCRecord):
                raise TypeError(
                    f"{loader.__class__.__name__} returned an invalid "
                    f"record at position {index}: "
                    f"{type(record).__name__}. Expected TCRecord."
                )

        standard_records = standardize_records(
            raw_records
        )

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