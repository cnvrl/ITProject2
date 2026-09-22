from __future__ import annotations

import pandas as pd

from app.config import (
    MODEL_GUIDE,
    MODEL_NUMBER_GUIDE,
)


def configured_models(
    dataset: object,
    tracker: object,
) -> list[str]:
    key = (
        str(dataset or "").upper(),
        str(tracker or "").upper(),
    )

    return list(MODEL_GUIDE.get(key, []))


def loaded_models(
    tracks: pd.DataFrame,
    dataset: object,
    tracker: object,
) -> list[str]:
    if tracks.empty or not dataset or not tracker:
        return []

    selected = tracks[
        tracks["dataset"].eq(
            str(dataset).upper()
        )
        & tracks["tracker"].eq(
            str(tracker).upper()
        )
    ]

    return sorted(
        selected["driving_model"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


def available_models(
    tracks: pd.DataFrame,
    dataset: object,
    tracker: object,
) -> list[str]:
    present = set(
        loaded_models(
            tracks,
            dataset,
            tracker,
        )
    )

    return [
        model
        for model in configured_models(
            dataset,
            tracker,
        )
        if model in present
    ]


def model_options(
    tracks: pd.DataFrame,
    dataset: object,
    tracker: object,
    *,
    selected_elsewhere: set[str] | None = None,
    current_value: str | None = None,
) -> list[dict]:
    selected_elsewhere = (
        selected_elsewhere or set()
    )

    configured = set(
        configured_models(
            dataset,
            tracker,
        )
    )

    present = set(
        loaded_models(
            tracks,
            dataset,
            tracker,
        )
    )

    all_models = list(
        dict.fromkeys(
            model
            for models in MODEL_GUIDE.values()
            for model in models
        )
    )

    result: list[dict] = []

    for model in all_models:
        guide_number = MODEL_NUMBER_GUIDE.get(
            (
                str(dataset or "").upper(),
                str(tracker or "").upper(),
                model,
            )
        )

        prefix = (
            f"{guide_number}. "
            if guide_number is not None
            else ""
        )

        valid = (
            model in configured
            and model in present
        )

        duplicate = (
            model in selected_elsewhere
            and model != current_value
        )

        if model not in configured:
            label = (
                f"{prefix}{model} — unavailable for "
                f"{dataset} + {tracker}"
            )
        elif model not in present:
            label = (
                f"{prefix}{model} — not found in data"
            )
        else:
            label = f"{prefix}{model}"

        result.append(
            {
                "label": label,
                "value": model,
                "disabled": not valid or duplicate,
            }
        )

    return result