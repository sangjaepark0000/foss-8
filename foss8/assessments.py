"""Period-scoped weekly activity assessments, independent of task checkmarks."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from . import progress


@dataclass(frozen=True)
class Criterion:
    id: str
    title: str
    target: int
    starts: date
    action: str
    after_class: bool = False


CRITERIA = (
    Criterion("commits", "커밋", 2, date(2026, 10, 9), "진행 중인 작업의 의미 있는 변경을 커밋"),
    Criterion("issues", "이슈 작성", 1, date(2026, 10, 9), "실제 작업 전에 목적·할 일·완료 조건을 담은 이슈 등록"),
    Criterion("prs", "PR 생성·병합", 1, date(2026, 10, 30), "작성한 PR의 리뷰·수정을 마치고 승인 후 병합", True),
)
ENDS = date(2026, 12, 13)
EXAM_START, EXAM_END = date(2026, 10, 19), date(2026, 10, 25)


def monday(day):
    return day - timedelta(days=day.weekday())


def read(path):
    if not path.exists():
        return {"schema_version": 1, "contexts": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("contexts"), dict):
        raise ValueError("평가 집계 기록 형식을 확인하세요.")
    for scope, records in data["contexts"].items():
        if not isinstance(scope, str) or not isinstance(records, dict):
            raise ValueError("평가 집계의 사용자·기간 형식을 확인하세요.")
        for start, record in records.items():
            parsed = date.fromisoformat(start)
            if not isinstance(record, dict):
                raise ValueError("평가 집계의 주간 시작일을 확인하세요.")
            validate_counts(record.get("counts"))
    return data


def validate_counts(counts):
    if not isinstance(counts, dict) or set(counts) - {c.id for c in CRITERIA}:
        raise ValueError("지원하는 집계: commits, issues, prs")
    if any(value is not None and (type(value) is not int or value < 0) for value in counts.values()):
        raise ValueError("횟수는 0 이상의 정수로 입력하세요. 미집계는 비워두세요.")


@dataclass(frozen=True)
class WeeklyAssessment:
    start: date
    counts: dict
    course_week: str | None = None
    period_end: date | None = None

    @property
    def end(self):
        return self.period_end or self.start + timedelta(days=6)

    @property
    def exempt(self):
        return EXAM_START <= self.start and self.end <= EXAM_END

    @property
    def exam_overlap(self):
        return self.start <= EXAM_END and self.end >= EXAM_START

    def active_ranges(self, criterion):
        """Inclusive start, exclusive end, excluding only explicit exam dates."""
        start, end = max(self.start, criterion.starts), min(self.end, ENDS) + timedelta(days=1)
        if start >= end:
            return []
        ranges = []
        before = min(end, EXAM_START)
        if start < before:
            ranges.append((start, before))
        after = max(start, EXAM_END + timedelta(days=1))
        if after < end:
            ranges.append((after, end))
        return ranges

    @property
    def scheduled_criteria(self):
        if self.start > ENDS:
            return ()
        return tuple(c for c in CRITERIA if c.starts <= self.end)

    @property
    def criteria(self):
        return tuple(c for c in self.scheduled_criteria if self.active_ranges(c))

    def lifecycle(self, on):
        return "예정" if on < self.start else "종료" if on > self.end else "진행 중"

    def status(self, on):
        if self.exempt:
            return "주간 최소 횟수 면제"
        if not self.criteria:
            return "적용 기준 없음"
        values = [self.counts.get(c.id) for c in self.criteria]
        if all(value is None for value in values):
            return "미집계"
        if any(value is None for value in values):
            return "일부 미집계"
        if all(self.counts[c.id] >= c.target for c in self.criteria):
            return "기준 충족"
        return "미충족" if on > self.end else "진행 중"

    def line(self, criterion):
        value = self.counts.get(criterion.id)
        if value is None:
            return f"{criterion.title}  미집계 / {criterion.target}회"
        remaining = max(0, criterion.target - value)
        suffix = f"{remaining}회 남음" if remaining else "충족"
        return f"{criterion.title}  {value}/{criterion.target}회 · {suffix}"


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.error = None
        try:
            self.data = read(self.path)
        except (ValueError, OSError) as error:
            self.data = {"schema_version": 1, "contexts": {}}
            self.error = str(error)

    def bundle(self, scope, start):
        counts = self.data["contexts"].get(scope, {}).get(start.isoformat(), {}).get("counts", {})
        return WeeklyAssessment(start, dict(counts))

    def for_period(self, scope, period):
        start = date.fromisoformat(period["start"])
        counts = self.bundle(scope, start).counts
        bundle = WeeklyAssessment(start, counts, period["id"],
                                  date.fromisoformat(period["end"]) - timedelta(days=1))
        return [bundle] if bundle.scheduled_criteria else []

    def record(self, scope, start):
        return self.data["contexts"].get(scope, {}).get(start.isoformat(), {})

    def save(self, scope, start, counts, source="manual", evidence=None):
        if self.error:
            raise ValueError("평가 집계 기록을 읽지 못했습니다. 파일을 확인한 뒤 다시 실행하세요.")
        validate_counts(counts)
        data = read(self.path)
        records = data["contexts"].setdefault(scope, {})
        previous = records.get(start.isoformat(), {})
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record = {**previous, "counts": {**previous.get("counts", {}), **counts}, "source": source,
                  "sources": {**previous.get("sources", {}), **{key: source for key in counts}},
                  "updated_at": stamp}
        if source == "github":
            record["evidence"] = {**previous.get("evidence", {}), **(evidence or {})}
            record["synced_at"] = stamp
        records[start.isoformat()] = record
        progress.write(self.path, data)
        self.data = data
        return self.bundle(scope, start)
