from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

import pandas as pd


@dataclass(frozen=True)
class FilterCriteria:
    dataset: Optional[str] = None
    tracker: Optional[str] = None
    models: tuple[str, ...] = field(
        default_factory=tuple
    )
    regions: tuple[str, ...] = field(
        default_factory=tuple
    )
    scenarios: tuple[str, ...] = field(
        default_factory=tuple
    )
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    minimum_category: int = 0


def clean_selection(
    values: object,
) -> list[str]:
    if values is None:
        return []

    if isinstance(values, str):
        values = [values]

    cleaned: list[str] = []
    seen: set[str] = set()

    for value in values:
        text = str(value).strip()

        if text and text not in seen:
            cleaned.append(text)
            seen.add(text)

    return cleaned


def create_criteria(
    dataset: Optional[str],
    tracker: Optional[str],
    models: object,
    regions: object,
    scenarios: object,
    years: object,
    minimum_category: object,
) -> FilterCriteria:
    year_start = None
    year_end = None

    if years and len(years) == 2:
        year_start = int(years[0])
        year_end = int(years[1])

    return FilterCriteria(
        dataset=(
            str(dataset).upper()
            if dataset
            else None
        ),
        tracker=(
            str(tracker).upper()
            if tracker
            else None
        ),
        models=tuple(clean_selection(models)),
        regions=tuple(clean_selection(regions)),
        scenarios=tuple(
            value.lower()
            for value in clean_selection(scenarios)
        ),
        year_start=year_start,
        year_end=year_end,
        minimum_category=int(
            minimum_category or 0
        ),
    )


def filter_tracks(
    tracks: pd.DataFrame,
    criteria: FilterCriteria,
) -> pd.DataFrame:
    selected = tracks.copy()

    if selected.empty:
        return selected

    if criteria.dataset:
        selected = selected[
            selected["dataset"].eq(
                criteria.dataset
            )
        ]

    if criteria.tracker:
        selected = selected[
            selected["tracker"].eq(
                criteria.tracker
            )
        ]

    if criteria.models:
        selected = selected[
            selected["driving_model"].isin(
                criteria.models
            )
        ]
    else:
        return selected.iloc[0:0].copy()

    if criteria.regions:
        selected = selected[
            selected["region"].isin(
                criteria.regions
            )
        ]

    if criteria.scenarios:
        selected = selected[
            selected["scenario"]
            .astype(str)
            .str.lower()
            .isin(criteria.scenarios)
        ]

    if (
        criteria.year_start is not None
        and criteria.year_end is not None
    ):
        years = pd.to_numeric(
            selected["analysis_year"],
            errors="coerce",
        )

        selected = selected[
            years.between(
                criteria.year_start,
                criteria.year_end,
                inclusive="both",
            )
        ]

    selected = selected[
        pd.to_numeric(
            selected["max_category"],
            errors="coerce",
        )
        .fillna(0)
        .ge(criteria.minimum_category)
    ]

    return selected.copy()


def points_for_tracks(
    points: pd.DataFrame,
    tracks: pd.DataFrame,
) -> pd.DataFrame:
    if points.empty or tracks.empty:
        return points.iloc[0:0].copy()

    identifiers = tracks[
        "track_id"
    ].dropna().unique()

    return points[
        points["track_id"].isin(identifiers)
    ].copy()