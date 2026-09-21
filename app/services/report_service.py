from __future__ import annotations

import numpy as np
import pandas as pd


def _fmt(value, digits=2):
    return "not available" if pd.isna(value) else f"{value:.{digits}f}"


def _trend_word(slope):
    if pd.isna(slope):
        return "could not be determined"
    if slope > 0.05:
        return "increasing"
    if slope < -0.05:
        return "decreasing"
    return "broadly stable"


def _percent_change(value, reference):
    if pd.isna(value) or pd.isna(reference) or reference == 0:
        return np.nan
    return (value - reference) / reference * 100.0


def _comparison_sentence(a, b, metric_name, column, unit):
    change = _percent_change(b[column], a[column])
    if pd.isna(change):
        return f"{metric_name} could not be compared because the baseline is unavailable or zero."
    direction = "higher" if change > 0 else "lower" if change < 0 else "the same"
    return (
        f"{b['Combination']} is {abs(change):.1f}% {direction} than {a['Combination']} "
        f"for {metric_name} ({_fmt(a[column])}{unit} versus {_fmt(b[column])}{unit})."
    )


def build_report(summary: pd.DataFrame) -> str:
    if summary.empty:
        raise ValueError("Cannot generate a report from an empty summary.")
    lines = [
        "TC-EXPLORER 2.0 ANALYSIS REPORT", "=" * 72, "",
        "This report was generated from the current dataset, tracker, model and season selections. "
        "Results are descriptive and do not establish causation or statistical significance.", "",
    ]
    for _, row in summary.iterrows():
        label = row["Combination"]
        lines.extend([
            str(label).upper(), "-" * 72,
            f"Coverage: seasons {int(row['SeasonMin'])}-{int(row['SeasonMax'])}; {int(row['CycloneTracks'])} unique cyclone tracks.", "",
            "Frequency",
            f"Mean frequency is {_fmt(row['MeanFrequency'])} tracks per season, with a median of "
            f"{_fmt(row['MedianFrequency'])} and maximum of {_fmt(row['MaxFrequency'], 0)}. "
            f"The fitted trend is {_fmt(row['FrequencyTrendPerSeason'], 3)} tracks per season and is "
            f"{_trend_word(row['FrequencyTrendPerSeason'])}.", "",
            "Intensity",
            f"Mean track-maximum wind is {_fmt(row['MeanMaxWind'])} km/h; median {_fmt(row['MedianMaxWind'])} km/h; "
            f"90th percentile {_fmt(row['P90MaxWind'])} km/h; strongest track {_fmt(row['StrongestTrackWind'])} km/h.", "",
            "Longevity",
            f"Mean lifetime is {_fmt(row['MeanDurationDays'])} days; median {_fmt(row['MedianDurationDays'])} days; "
            f"90th percentile {_fmt(row['P90DurationDays'])} days; longest track {_fmt(row['LongestDurationDays'])} days.", "",
            "Spatial density",
            f"The peak density cell is near {_fmt(row['HotspotLon'], 1)} degrees east, "
            f"{_fmt(abs(row['HotspotLat']), 1)} degrees south with {_fmt(row['HotspotCount'], 0)} observations. "
            f"The density-weighted centre is near {_fmt(row['DensityCentreLon'], 1)} degrees east, "
            f"{_fmt(abs(row['DensityCentreLat']), 1)} degrees south.", "",
        ])
    if len(summary) >= 2:
        lines.extend(["OVERALL COMPARISON", "=" * 72, ""])
        for description, column, unit in [
            ("highest mean frequency", "MeanFrequency", " tracks/season"),
            ("highest mean track-maximum wind", "MeanMaxWind", " km/h"),
            ("longest mean lifetime", "MeanDurationDays", " days"),
        ]:
            row = summary.loc[summary[column].idxmax()]
            lines.append(f"{row['Combination']} has the {description} at {_fmt(row[column])}{unit}.")
        lines.append("")
        baseline = summary.iloc[0]
        lines.extend([f"PAIRWISE CHANGES RELATIVE TO {baseline['Combination'].upper()}", "-" * 72])
        for _, other in summary.iloc[1:].iterrows():
            lines.append(f"{baseline['Combination']} vs {other['Combination']}")
            lines.append("- " + _comparison_sentence(baseline, other, "mean frequency", "MeanFrequency", " tracks/season"))
            lines.append("- " + _comparison_sentence(baseline, other, "mean track-maximum wind", "MeanMaxWind", " km/h"))
            lines.append("- " + _comparison_sentence(baseline, other, "mean longevity", "MeanDurationDays", " days"))
            lines.append("")
    lines.extend([
        "INTERPRETATION LIMITS", "=" * 72,
        "Differences may reflect regional-model construction, tracker behaviour, driving-model composition, "
        "season coverage or sampling. A density hotspot means more track observations, not necessarily stronger "
        "cyclones. Use matched periods and formal statistical testing before drawing scientific conclusions.",
    ])
    return "\n".join(lines)
