"""Read team-setting candidates from this checkout and the authenticated gh CLI."""
from dataclasses import dataclass
from pathlib import Path
import copy
import json
import os
import re
import subprocess
from urllib.parse import urlparse

from . import team


@dataclass
class Result:
    config: dict
    sources: list
    warnings: list


def clean(value):
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.replace("**", "").replace("`", "").strip()


def repository_url(remote):
    """Normalize HTTPS, SCP-like SSH and ssh:// remotes; never retain credentials."""
    if "://" not in remote:
        match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", remote)
        if not match:
            return None, None
        host, path = match.groups()
    else:
        parsed = urlparse(remote)
        host, path = parsed.hostname, parsed.path
    path = path.strip("/").removesuffix(".git")
    if not host or not re.fullmatch(r"[\w.-]+/[\w.-]+", path) or any(p in (".", "..") for p in path.split("/")):
        return None, None
    return f"https://{host}/{path}", path if host.lower() == "github.com" else None


def table_members(content):
    rows, shared_roles = [], []
    headers = None
    for line in content.splitlines():
        if not line.lstrip().startswith("|"):
            headers = None
            continue
        cells = [v.strip() for v in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r"[\s:-]*", c) for c in cells):
            continue
        normalized = [clean(c).lower().replace(" ", "") for c in cells]
        if any("github" in c or "깃허브" in c for c in normalized) and any(c in ("이름", "name", "팀원") for c in normalized):
            headers = normalized
            continue
        if headers is None:
            continue
        def field(names, contains=False):
            return next((cells[i] for i, head in enumerate(headers) if i < len(cells) and
                         (any(n in head for n in names) if contains else head in names)), "")
        name = clean(field(("이름", "name", "팀원")))
        role = clean(field(("역할", "role", "roles")))
        roles = [team.ALIASES.get(r.strip(), r.strip()) for r in re.split(r"[,/]", role) if r.strip() and r.strip() not in ("미정", "-", "—")]
        if "공동" in name:
            shared_roles.extend(roles)
            continue
        gh = field(("github", "깃허브"), contains=True)
        match = re.search(r"github\.com/([\w-]+)|@([\w-]+)", gh)
        github = (next(v for v in match.groups() if v) if match else clean(gh)).lower()
        if not name or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?", github):
            continue
        feature = clean(field(("담당기능", "features", "feature", "담당")))
        rows.append({"name": name, "github": github, "roles": roles,
                     "features": [feature] if feature and feature not in ("미정", "-", "—") else []})
    return rows, shared_roles


def detect(start=None, use_github=True, runner=subprocess.run):
    root = Path(start or Path.cwd()).resolve()
    warnings, sources = [], []
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GIT_TERMINAL_PROMPT": "0"}
    def command(args, label, json_output=False):
        try:
            result = runner(args, cwd=root, env=env, capture_output=True, text=True,
                            encoding="utf-8", timeout=7, check=False)
        except FileNotFoundError:
            warnings.append(f"{args[0]} 없음: {label} 생략")
            return None
        except (subprocess.TimeoutExpired, OSError):
            warnings.append(f"{label} 읽기 실패: 연결·실행 환경 확인")
            return None
        if result.returncode:
            warnings.append(f"{label} 읽기 실패: 로그인·접근 권한 확인" if args[0] == "gh" else f"{label} 확인 불가")
            return None
        try:
            return json.loads(result.stdout) if json_output else result.stdout.strip()
        except (ValueError, TypeError):
            warnings.append(f"{label} 응답 형식 확인 필요")
            return None
    checkout = command(["git", "rev-parse", "--show-toplevel"], "Git 루트")
    if checkout:
        root = Path(checkout).resolve()
    remote = command(["git", "remote", "get-url", "origin"], "origin 원격 저장소")
    url, slug = repository_url(remote) if remote else (None, None)
    if url:
        sources.append("Git origin")
    metadata = user = None
    collaborators = None
    if use_github:
        user = command(["gh", "api", "user"], "gh 로그인 계정", True)
        if isinstance(user, dict) and user.get("login"):
            sources.append("gh 로그인 계정")
        if slug:
            metadata = command(["gh", "api", "repos/" + slug], "GitHub 저장소 정보", True)
            if isinstance(metadata, dict) and metadata.get("html_url"):
                canonical, canonical_slug = repository_url(metadata["html_url"])
                if canonical_slug:
                    url, slug = canonical, canonical_slug
                    sources.append("GitHub 저장소 정보")
            pages = command(["gh", "api", f"repos/{slug}/collaborators", "--paginate", "--slurp"], "GitHub 협력자", True)
            if isinstance(pages, list):
                collaborators = [p for page in pages for p in (page if isinstance(page, list) else [page]) if isinstance(p, dict) and p.get("login") and p.get("type") != "Bot"]
                sources.append("GitHub 협력자 목록")
    known = {p["login"].lower(): p for p in collaborators or []}
    docs = []
    for path in [root / "README.md", root / "docs/team-agreement.md"]:
        if path.is_file():
            try:
                docs.append((path.relative_to(root).as_posix(), path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError):
                warnings.append(f"{path.name} 읽기 실패")
    all_rows, shared = [], []
    raw = {"name": slug.split("/")[-1] if slug else root.name,
           "repository": url or "", "members": [], "me": None, "task_owners": {},
           "agreements": {}, "approved_changes": []}
    raw["name"] = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "-", raw["name"]) or "team"
    for label, content in docs:
        rows, common = table_members(content)
        if rows:
            sources.append(label)
        all_rows.extend(rows)
        shared.extend(common)
        name_match = re.search(r"^#\s*팀\s*약속\s*[—–:-]\s*(.+)$", content, re.M)
        if name_match:
            raw["name"] = clean(name_match[1])
        meeting = re.search(r"정기\s*회의\s*:\s*([^\n]+)", content)
        if meeting:
            raw["agreements"]["meeting"] = clean(meeting[1]).split("불참", 1)[0].strip(" .,")
        for key, pattern in [("chat_hours", r"채팅\s*(\d+)\s*시간"), ("review_hours", r"리뷰\s*(\d+)\s*시간")]:
            match = re.search(pattern, content)
            if match:
                raw["agreements"][key] = int(match[1])
    by_name = {}
    for row in all_rows:
        by_name.setdefault(row["name"], []).append(row)
    for name, candidates in by_name.items():
        preferred = next((r for r in candidates if r["github"] in known), candidates[0])
        person = copy.deepcopy(preferred)
        for row in candidates:
            if row["github"] != person["github"]:
                suffix = "GitHub 협력자와 일치하는 계정 사용" if person["github"] in known else "명단 확인 필요"
                warnings.append(f"{name}: 문서의 GitHub ID가 다름 · {suffix}")
            person["roles"] = list(dict.fromkeys(person["roles"] + row["roles"]))
            if not person["features"]:
                person["features"] = list(row["features"])
        raw["members"].append(person)
    by_login = {}
    for person in raw["members"]:
        if person["github"] not in by_login:
            by_login[person["github"]] = person
        else:
            first = by_login[person["github"]]
            first["roles"] = list(dict.fromkeys(first["roles"] + person["roles"]))
            if not first["features"]:
                first["features"] = person["features"]
            warnings.append(f'{person["github"]}: 문서에 여러 이름이 있어 첫 명단의 이름 사용')
    raw["members"] = list(by_login.values())
    if not all_rows:
        for login, person in known.items():
            raw["members"].append({"name": person.get("name") or login, "github": login, "roles": [], "features": []})
        if known:
            warnings.append("문서에 팀원 명단이 없어 협력자를 팀원 후보로 읽었습니다.")
    for person in raw["members"]:
        person["roles"] = list(dict.fromkeys(person["roles"] + shared))
    # Member introductions only enrich people already identified by the roster.
    members_dir = root / "docs/members"
    if members_dir.is_dir():
        for path in sorted(members_dir.glob("*.md")):
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                warnings.append(f"{path.name} 읽기 실패")
                continue
            name = re.search(r"^이름\s*:\s*(.+)$", content, re.M)
            duty = re.search(r"^담당\s*:\s*(.+)$", content, re.M)
            person = next((p for p in raw["members"] if name and p["name"] == name[1].strip()), None)
            if person and duty:
                for part in duty[1].split(","):
                    part = part.strip()
                    role = team.ALIASES.get(part, part)
                    if role in team.ROLES and role not in person["roles"]:
                        person["roles"].append(role)
                    elif role not in team.ROLES and not person["features"]:
                        person["features"].append(part)
                sources.append(path.relative_to(root).as_posix())
    ids = {p["github"] for p in raw["members"]}
    if isinstance(user, dict) and isinstance(user.get("login"), str):
        login = user["login"].lower()
        if login in ids:
            raw["me"] = login
        else:
            warnings.append("로그인 계정이 팀원 명단에 없어 내 계정은 미정으로 두었습니다.")
    admins = [p["login"].lower() for p in known.values() if p.get("permissions", {}).get("admin") and p["login"].lower() in ids]
    if len(admins) == 1:
        raw["task_owners"]["repository_admin"] = admins[0]
    context_file = root / "docs/guide/team-context.md"
    if context_file.is_file():
        content = context_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if not line.startswith("|"):
                continue
            cells = [clean(x) for x in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] == "팀·기능 구성" and "승인" in cells[1]:
                raw["approved_changes"].append({"description": cells[1], "source": "docs/guide/team-context.md", "date": ""})
            if len(cells) >= 2 and "회의록" in cells[0]:
                for person in raw["members"]:
                    if re.search(re.escape(person["name"]) + r"\s*LMS\s*제출", cells[1]):
                        raw["task_owners"]["minutes_submitter"] = person["github"]
        sources.append("docs/guide/team-context.md")
    return Result(team.validate(raw), list(dict.fromkeys(sources)), list(dict.fromkeys(warnings)))


def merge(existing, detected):
    """Existing choices win; discovery only fills missing settings."""
    if not existing:
        return copy.deepcopy(detected)
    # A different repository is a different team context, not a source of extra members.
    old_repo = existing.get("repository", "").rstrip("/").removesuffix(".git")
    new_repo = detected.get("repository", "").rstrip("/").removesuffix(".git")
    if old_repo and new_repo and old_repo != new_repo:
        return copy.deepcopy(existing)
    result = copy.deepcopy(existing)
    for key in ("name", "repository"):
        if not result.get(key):
            result[key] = detected.get(key, "")
    if not result.get("members"):
        result["members"] = copy.deepcopy(detected["members"])
        if not result.get("me"):
            result["me"] = detected.get("me")
    ids = {p["github"] for p in result["members"]}
    for task, owner in detected.get("task_owners", {}).items():
        if task not in result["task_owners"] and owner in ids:
            result["task_owners"][task] = owner
    # Never replace intentionally unassigned roles, owners, me, or approved changes.
    return team.validate(result)


LABELS = {"name": "팀 이름", "repository": "저장소", "me": "내 계정", "members": "팀원·역할·담당 기능",
          "task_owners": "업무 담당자", "agreements": "팀 약속", "approved_changes": "승인 기록"}


def differences(existing, detected):
    """Only propose information actually found; absent information is not a deletion."""
    old = existing or {}
    changes = []
    for key, label in LABELS.items():
        value = detected.get(key)
        if value not in (None, "", [], {}) and value != old.get(key):
            changes.append((key, label, old.get(key), value))
    return changes


def apply_changes(existing, detected):
    result = copy.deepcopy(existing or detected)
    for key, _, _, value in differences(existing, detected):
        result[key] = copy.deepcopy(value)
    ids = {p["github"] for p in result.get("members", [])}
    if result.get("me") not in ids:
        result["me"] = None
    result["task_owners"] = {k: v if v in ids else None for k, v in result.get("task_owners", {}).items()}
    return team.validate(result)


def describe(value):
    if value in (None, "", [], {}):
        return "미설정"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and "github" in item:
                roles = ", ".join(team.ROLES.get(r, r) for r in item.get("roles", [])) or "역할 미정"
                features = ", ".join(item.get("features", [])) or "기능 미정"
                parts.append(f'{item["name"]} (@{item["github"]}) · {roles} · {features}')
            elif isinstance(item, dict) and "description" in item:
                parts.append(item["description"])
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(value, dict):
        labels = {key: label for key, (_, label) in team.OWNERS.items()}
        labels.update(meeting="정기회의", chat_hours="채팅 응답 시간", review_hours="리뷰 응답 시간")
        return "; ".join(f'{labels.get(k, k)}: {v if v is not None else "미정"}' for k, v in value.items())
    return json.dumps(value, ensure_ascii=False)
