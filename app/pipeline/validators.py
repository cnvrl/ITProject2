from __future__ import annotations

from collections import Counter
from typing import Iterable

from app.models.tc_record import TCRecord


def validate_record(record: TCRecord) -> list[str]:
    issues: list[str] = []
    if not record.track_id:
        issues.append('Missing track_id')
    if not record.dataset_id:
        issues.append('Missing dataset_id')
    if len(record.points) == 0:
        issues.append('Track has no points')
        return issues
    if len(record.points) == 1:
        issues.append('Track has only one point')
    times = [p.time for p in record.points]
    if times != sorted(times):
        issues.append('Track points are not time-ordered')
    if record.max_category is not None and not (0 <= record.max_category <= 5):
        issues.append('max_category outside supported range 0-5')
    return issues


def validate_records(records: Iterable[TCRecord]) -> dict:
    records = list(records)
    report = {
        'total_records': len(records),
        'valid_records': 0,
        'invalid_records': 0,
        'issue_counts': {},
        'record_issues': {}
    }
    issue_counter: Counter[str] = Counter()
    for record in records:
        issues = validate_record(record)
        if issues:
            report['invalid_records'] += 1
            report['record_issues'][record.track_id] = issues
            issue_counter.update(issues)
        else:
            report['valid_records'] += 1
    report['issue_counts'] = dict(issue_counter)
    return report