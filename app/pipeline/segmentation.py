from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Sequence

from app.models.tc_record import TCRecord, TrackPoint


def split_track_by_gap(
    record: TCRecord,
    max_gap_hours: float = 24.0,
) -> list[TCRecord]:
    """
    Split a TCRecord into sub-segments if consecutive observations 
    exceed the max_gap_hours threshold.
    """
    if not record.points or len(record.points) <= 1:
        return [record]

    gap_threshold = timedelta(hours=max_gap_hours)
    segments_points: list[list[TrackPoint]] = []
    current_segment: list[TrackPoint] = [record.points[0]]

    for prev_point, curr_point in zip(record.points[:-1], record.points[1:]):
        if prev_point.timestamp is not None and curr_point.timestamp is not None:
            time_diff = curr_point.timestamp - prev_point.timestamp
            if time_diff > gap_threshold:
                segments_points.append(current_segment)
                current_segment = []

        current_segment.append(curr_point)

    if current_segment:
        segments_points.append(current_segment)

    if len(segments_points) <= 1:
        return [record]

    split_records: list[TCRecord] = []
    parent_raw_id = record.metadata.get("raw_track_id") or record.track_id

    for seg_idx, pts in enumerate(segments_points, start=1):
        # Create lightweight sub-segment copy
        seg_record = TCRecord(
            dataset_id=record.dataset_id,
            track_id=f"{record.track_id}_seg{seg_idx}",
            model=record.model,
            driving_model=record.driving_model,
            tracker=record.tracker,
            scenario=record.scenario,
            region=record.region,
            season=record.season,
            year=record.year,
            points=[deepcopy(pt) for pt in pts],
            metadata=dict(record.metadata),
        )

        for pt_idx, pt in enumerate(seg_record.points):
            pt.step = pt_idx

        seg_record.metadata.update({
            "parent_track_id": record.track_id,
            "raw_track_id": f"{parent_raw_id}_s{seg_idx}",
            "segment_id": str(seg_idx),
            "is_subsegment": True,
        })

        seg_record.refresh_derived_fields()
        split_records.append(seg_record)

    return split_records


def split_tracks_by_gap(
    records: Sequence[TCRecord],
    max_gap_hours: float = 24.0,
) -> list[TCRecord]:
    """Apply time-gap trajectory segmentation across a list of TCRecord objects."""
    split_dataset: list[TCRecord] = []
    for record in records:
        split_dataset.extend(split_track_by_gap(record, max_gap_hours=max_gap_hours))
    return split_dataset