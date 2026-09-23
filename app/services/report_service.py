from __future__ import annotations

import pandas as pd


def build_interpretation_report(summary_df: pd.DataFrame) -> str:
    if summary_df.empty:
        return "No tropical cyclone data available for the active filter selection."

    total_all = int(summary_df["total_cyclones"].sum()) if "total_cyclones" in summary_df else 0
    total_landfalls = int(summary_df["landfalls"].sum()) if "landfalls" in summary_df else 0
    overall_landfall_pct = (total_landfalls / total_all * 100) if total_all > 0 else 0.0

    lines = [
        "=" * 80,
        "TC EXPLORER 2.0 - TROPICAL CYCLONE INTERPRETATION REPORT",
        "Prepared by Team Susanoo, UNSW Canberra",
        "=" * 80,
        "",
        "--- EXECUTIVE SUMMARY ---",
        f"• Total Evaluated Tracks: {total_all:,}",
        f"• Total Landfall Events:  {total_landfalls:,} ({overall_landfall_pct:.1f}% overall landfall rate)",
        f"• Models Evaluated:      {len(summary_df)} driving model(s)",
        "",
    ]

    if len(summary_df) > 1 and "total_cyclones" in summary_df and "max_wind_kmh" in summary_df:
        max_freq_row = summary_df.loc[summary_df["total_cyclones"].idxmax()]
        max_wind_row = summary_df.loc[summary_df["max_wind_kmh"].idxmax()]
        max_landfall_row = summary_df.loc[summary_df["landfalls"].idxmax()]

        lines.extend([
            "--- COMPARATIVE HIGHLIGHTS ---",
            f"• Highest Activity Model: {max_freq_row.get('model', max_freq_row.get('driving_model'))} ({int(max_freq_row['total_cyclones']):,} tracks)",
            f"• Peak Intensity Model:   {max_wind_row.get('model', max_wind_row.get('driving_model'))} ({float(max_wind_row['max_wind_kmh']):.1f} km/h max wind)",
            f"• Top Coastal Exposure:   {max_landfall_row.get('model', max_landfall_row.get('driving_model'))} ({int(max_landfall_row['landfalls']):,} landfalls)",
            "",
        ])

    lines.append("--- MODEL METRICS & RISK BREAKDOWN ---")

    for _, row in summary_df.iterrows():
        model_name = str(row.get("model") or row.get("driving_model") or "Unknown")
        total = int(row.get("total_cyclones", 0))
        avg_wind = float(row.get("avg_wind_kmh", 0.0))
        max_wind = float(row.get("max_wind_kmh", 0.0))
        avg_dur = float(row.get("avg_duration_hours", 0.0))
        landfalls = int(row.get("landfalls", 0))
        lf_rate = (landfalls / total * 100) if total else 0.0

        # Category scale contextual classification
        if max_wind >= 200:
            cat_desc = "Category 5 Severe TC"
        elif max_wind >= 160:
            cat_desc = "Category 4 Severe TC"
        elif max_wind >= 118:
            cat_desc = "Category 3 Severe TC"
        elif max_wind >= 89:
            cat_desc = "Category 2 TC"
        elif max_wind >= 63:
            cat_desc = "Category 1 TC"
        else:
            cat_desc = "Tropical Low / CDD System (<63 km/h)"

        # Coastal risk rating
        landfall_risk = "High" if lf_rate >= 50 else ("Moderate" if lf_rate >= 25 else "Low")

        lines.extend([
            f"MODEL: {model_name}",
            f"  • Frequency: {total:,} tracks | {landfalls:,} landfalls ({lf_rate:.1f}% | {landfall_risk} Coastal Exposure)",
            f"  • Intensity: Mean {avg_wind:.1f} km/h | Peak {max_wind:.1f} km/h [{cat_desc}]",
            f"  • Longevity: Mean {avg_dur:.1f} hours ({avg_dur / 24.0:.1f} days)",
            "-" * 80,
        ])

    return "\n".join(lines)