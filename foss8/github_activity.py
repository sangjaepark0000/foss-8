"""Read GitHub evidence for one course week using the authenticated gh CLI."""
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
import json
import os
import re
import subprocess

from . import assessments, discovery

KST = timezone(timedelta(hours=9))


@dataclass
class Result:
    counts: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def requirements(config):
    config = config or {}
    _, slug = discovery.repository_url(config.get("repository", ""))
    missing = []
    if not slug:
        missing.append(("repository", "GitHub 저장소 설정"))
    if not config.get("me"):
        missing.append(("me", "내 GitHub 계정 선택"))
    return missing


def collect(config, period, runner=subprocess.run, on=None):
    missing = requirements(config)
    if missing:
        raise ValueError(" · ".join(label for _, label in missing) + " 필요")
    _, slug = discovery.repository_url(config["repository"])
    login = config["me"]
    if not re.fullmatch(r"[a-zA-Z0-9-]+", login):
        raise ValueError("내 GitHub 계정 형식을 확인하세요.")
    start = datetime.fromisoformat(period["start"]).date()
    end = datetime.fromisoformat(period["end"]).date()
    bundle = assessments.WeeklyAssessment(start, {}, period["id"], end - timedelta(days=1))
    active = {c.id: [(a, b) for a, b in bundle.active_ranges(c) if on is None or a <= on]
              for c in bundle.criteria if on is None or c.starts <= on}
    active = {key: ranges for key, ranges in active.items() if ranges}
    utc = lambda day: datetime.combine(day, time.min, KST).astimezone(timezone.utc)
    stamp = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    def bounds(a, b):
        return stamp(utc(a)), stamp(utc(b) - timedelta(seconds=1))
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GIT_TERMINAL_PROMPT": "0"}

    def api(endpoint, **params):
        args = ["gh", "api", endpoint, "--method", "GET", "--paginate", "--slurp"]
        for key, value in params.items():
            args.extend(["-f", f"{key}={value}"])
        try:
            response = runner(args, env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=30, check=False)
        except FileNotFoundError as error:
            raise ValueError("gh 설치 필요") from error
        except (subprocess.TimeoutExpired, OSError) as error:
            raise ValueError("GitHub 연결 실패 · r로 재시도") from error
        if response.returncode:
            raise ValueError("GitHub 조회 실패 · gh auth status로 확인, 인증이 없으면 gh auth login · 저장소 접근 권한 확인")
        try:
            pages = json.loads(response.stdout)
            if not isinstance(pages, list):
                raise ValueError()
            return pages
        except (ValueError, TypeError) as error:
            raise ValueError("GitHub 응답 형식 오류 · 기존 집계 유지") from error

    def listing(endpoint, **params):
        pages = api(endpoint, per_page=100, **params)
        if any(not isinstance(page, list) for page in pages):
            raise ValueError("GitHub 목록 응답 형식 오류")
        return [item for page in pages for item in page]

    def search(kind, a, b):
        since, until = bounds(a, b)
        q = f"repo:{slug} author:{login} is:{kind} created:{since}..{until}"
        if kind == "pr":
            q += f" is:merged merged:{since}..{until}"
        pages = api("search/issues", q=q, per_page=100)
        if not pages or any(not isinstance(p, dict) or p.get("incomplete_results") or
                            not isinstance(p.get("items"), list) or type(p.get("total_count")) is not int
                            for p in pages):
            raise ValueError("GitHub 검색이 불완전하여 기존 집계 유지")
        items = {i["number"]: i for p in pages for i in p["items"]}
        if len(items) != pages[0]["total_count"]:
            raise ValueError("GitHub 검색 제한·누락으로 기존 집계 유지")
        return list(items.values())

    result = Result()
    if "commits" in active:
        try:
            branches = listing(f"repos/{slug}/branches")
            commits = {}
            for a, b in active["commits"]:
                since, until = bounds(a, b)
                for branch in branches:
                    for item in listing(f"repos/{slug}/commits", sha=branch["name"], author=login,
                                        since=since, until=until):
                        committed = datetime.fromisoformat(item["commit"]["committer"]["date"].replace("Z", "+00:00"))
                        if utc(a) <= committed < utc(b):
                            commits[item["sha"]] = item
            result.counts["commits"] = len(commits)
            result.evidence["commits"] = [c["html_url"] for c in commits.values()]
        except (ValueError, KeyError, TypeError) as error:
            result.errors.append("커밋: " + (str(error) if isinstance(error, ValueError) else "응답 형식 오류"))
    for key, kind in (("issues", "issue"), ("prs", "pr")):
        if key not in active:
            continue
        try:
            items = {item["number"]: item for a, b in active[key] for item in search(kind, a, b)}
            result.counts[key] = len(items)
            result.evidence[key] = [i["html_url"] for i in items.values()]
        except (ValueError, KeyError, TypeError) as error:
            result.errors.append(key + ": " + (str(error) if isinstance(error, ValueError) else "응답 형식 오류"))
    return result
