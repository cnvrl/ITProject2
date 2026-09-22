from __future__ import annotations

import pandas as pd


def build_interpretation_report(
    summary: pd.DataFrame,
) -> str:
    lines = [
        "TC Explorer 2.0 — Model Comparison Report",
        "=" * 48,
        "",
    ]

    if summary.empty:
        lines.append(
            "No cyclone records matched the active filters."
        )
        return "\n".join(lines)

    lines.append(
        f"Models compared: {len(summary)}"
    )
    lines.append("")

    for _, row in summary.iterrows():
        lines.extend(
            [
                str(row["model"]),
                "-" * len(str(row["model"])),
                (
                    f"Cyclone tracks: "
                    f"{int(row['cyclone_count'])}"
                ),
                (
                    "Mean frequency per season: "
                    f"{row['mean_frequency_per_season']:.2f}"
                ),
                (
                    "Mean peak wind: "
                    f"{row['mean_peak_wind_kmh']:.1f} km/h"
                ),
                (
                    "Maximum wind: "
                    f"{row['maximum_wind_kmh']:.1f} km/h"
                ),
                (
                    "Mean longevity: "
                    f"{row['mean_longevity_days']:.2f} days"
                ),
                (
                    f"Landfalls: "
                    f"{int(row['landfall_count'])}"
                ),
                "",
            ]
        )

    strongest = summary.loc[
        summary["maximum_wind_kmh"].idxmax()
    ]

    most_frequent = summary.loc[
        summary["mean_frequency_per_season"].idxmax()
    ]

    longest = summary.loc[
        summary["mean_longevity_days"].idxmax()
    ]

    lines.extend(
        [
            "Interpretation",
            "--------------",
            (
                f"{strongest['model']} produced the highest "
                f"maximum wind speed in the filtered selection."
            ),
            (
                f"{most_frequent['model']} had the highest "
                f"mean cyclone frequency per season."
            ),
            (
                f"{longest['model']} had the longest mean "
                f"cyclone duration."
            ),
            "",
            (
                "Results describe the active dashboard filters "
                "and should not be interpreted as an unfiltered "
                "assessment of the full datasets."
            ),
        ]
    )

    return "\n".join(lines)