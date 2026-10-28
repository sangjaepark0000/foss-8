"""Project-local team settings, separate from the common handbook rules."""
import copy
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlparse


ROLES = {"team_lead": "팀장", "development_lead": "개발 리드",
         "documentation": "문서 담당", "quality": "리뷰·품질 담당"}
ALIASES = {**{value: key for key, value in ROLES.items()},
           "개발리드": "development_lead", "문서담당": "documentation",
           "리뷰·품질": "quality"}
OWNERS = {"minutes_writer": ("documentation", "회의록 작성 담당"),
          "minutes_submitter": ("team_lead", "회의록 제출 담당"),
          "repository_admin": ("team_lead", "저장소 관리 담당"),
          "development_lead": ("development_lead", "공통 코드 담당"),
          "cross_team_contact": ("documentation", "타 팀 기여 담당")}


def config_path(start=None):
    start = Path(start or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        target = parent / ".foss8/team.json"
        if target.exists() or (parent / ".git").exists():
            return target
    return start / ".foss8/team.json"


def text(value, label, required=False):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise ValueError(f"{label}: 한 줄 문자열로 입력하세요.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{label}을 입력하세요.")
    return value


def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError("팀 설정은 JSON 객체여야 합니다.")
    allowed = {"schema_version", "name", "repository", "members", "me", "task_owners", "agreements", "approved_changes"}
    if set(raw) - allowed:
        raise ValueError("알 수 없는 팀 설정 항목: " + ", ".join(sorted(set(raw) - allowed)))
    if raw.get("schema_version", 1) != 1:
        raise ValueError("지원하지 않는 팀 설정 버전입니다.")
    name = text(raw.get("name", ""), "팀 이름", required=True)
    if any(c in name for c in '/\\:*?"<>|') or name in (".", ".."):
        raise ValueError("팀 이름에는 파일명에 쓸 수 없는 문자를 사용할 수 없습니다.")
    repository = text(raw.get("repository", ""), "저장소")
    if repository and not repository.startswith("https://") and re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        repository = "https://github.com/" + repository
    if repository:
        parsed = urlparse(repository)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or any(c.isspace() for c in repository):
            raise ValueError("저장소는 HTTPS 주소 또는 GitHub의 소유자/저장소로 입력하세요.")
    members = raw.get("members", [])
    if not isinstance(members, list):
        raise ValueError("members는 팀원 목록이어야 합니다.")
    people, ids = [], set()
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("각 팀원은 name·github·roles·features 객체로 입력하세요.")
        if set(member) - {"name", "github", "roles", "features"}:
            raise ValueError("팀원 설정의 지원 항목: name, github, roles, features")
        github = text(member.get("github", ""), "GitHub ID", True).lstrip("@").lower()
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?", github):
            raise ValueError("GitHub ID 형식을 확인하세요.")
        if github in ids:
            raise ValueError(f"중복 GitHub ID: {github}")
        ids.add(github)
        person = {"name": text(member.get("name", ""), "팀원 이름", True), "github": github}
        for field in ("roles", "features"):
            values = member.get(field, [])
            if not isinstance(values, list):
                raise ValueError(f"{field}는 목록이어야 합니다.")
            values = [text(v, field, True) for v in values]
            person[field] = list(dict.fromkeys(ALIASES.get(v, v) if field == "roles" else v for v in values))
        people.append(person)
    me = raw.get("me")
    if me is not None:
        me = text(me, "내 GitHub ID").lstrip("@").lower() or None
    if me and me not in ids:
        raise ValueError("내 GitHub ID는 등록된 팀원이어야 합니다.")
    owners = raw.get("task_owners", {})
    if not isinstance(owners, dict) or set(owners) - set(OWNERS):
        raise ValueError("task_owners의 업무 이름을 확인하세요: " + ", ".join(OWNERS))
    owners = copy.deepcopy(owners)
    for task, value in owners.items():
        if value is None:
            continue
        value = text(value, "업무 담당 GitHub ID", True).lstrip("@").lower()
        if value not in ids:
            raise ValueError(f"{task}: 등록되지 않은 팀원 {value}")
        owners[task] = value
    agreements = raw.get("agreements", {})
    if not isinstance(agreements, dict) or set(agreements) - {"meeting", "chat_hours", "review_hours"}:
        raise ValueError("agreements의 지원 항목: meeting, chat_hours, review_hours")
    agreements = copy.deepcopy(agreements)
    if "meeting" in agreements:
        agreements["meeting"] = text(agreements["meeting"], "회의 시간")
    for key in ("chat_hours", "review_hours"):
        if key in agreements and (type(agreements[key]) is not int or agreements[key] <= 0):
            raise ValueError(f"{key}는 양의 정수여야 합니다.")
    changes = raw.get("approved_changes", [])
    if not isinstance(changes, list):
        raise ValueError("approved_changes는 승인 기록 목록이어야 합니다.")
    normalized_changes = []
    for change in changes:
        if not isinstance(change, dict) or set(change) - {"description", "source", "date"}:
            raise ValueError("승인 기록은 description·source·date로 입력하세요.")
        normalized_changes.append({key: text(change.get(key, ""), key, key != "date")
                                   for key in ("description", "source", "date")})
    return {"schema_version": 1, "name": name, "repository": repository,
            "members": people, "me": me, "task_owners": owners,
            "agreements": agreements, "approved_changes": normalized_changes}


def load(path=None):
    path = Path(path) if path is not None else config_path()
    return validate(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None


def save(raw, path=None):
    data = validate(raw)
    path = Path(path) if path is not None else config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return data


def bindings(config):
    config = config or {}
    members = config.get("members", [])
    by_id = {p["github"]: p for p in members}
    values = {"team.name": config.get("name", "팀명"),
              "team.repository": config.get("repository") or "저장소 미설정",
              "team.features": " / ".join(f'{feature}: {p["name"]}' for p in members for feature in p["features"]) or "담당 기능 미설정",
              "team.approved_changes": " / ".join(f'{c["description"]} (근거: {c["source"]})' for c in config.get("approved_changes", [])) or "별도 승인 기록 없음"}
    for role, label in ROLES.items():
        values["role." + role] = "·".join(p["name"] for p in members if role in p["roles"]) or (label + " 미정" if config else label)
    for task, (role, label) in OWNERS.items():
        owners = config.get("task_owners", {})
        values["task." + task] = (by_id[owners[task]]["name"] if owners[task] else label + " 미정") if task in owners else values["role." + role]
    return values


def apply(value, config=None):
    values = bindings(config)
    def visit(item):
        if isinstance(item, str):
            return re.sub(r"\{\{([a-z_.]+)\}\}", lambda m: values.get(m[1], m[0]), item)
        if isinstance(item, list):
            return [visit(x) for x in item]
        if isinstance(item, dict):
            return {key: visit(x) for key, x in item.items()}
        return item
    return visit(value)


def setup(existing=None, input_fn=input):
    existing = existing or {}
    def ask(label, default=""):
        answer = input_fn(label + (f" [{default}]" if default != "" else "") + " > ").strip()
        if answer == "-":
            return ""
        return answer or str(default)
    name = ask("팀 이름", existing.get("name", ""))
    repository = ask("저장소 HTTPS 주소 또는 소유자/저장소", existing.get("repository", ""))
    current = existing.get("members", [])
    try:
        count = int(ask("팀원 수", len(current)))
    except ValueError as error:
        raise ValueError("팀원 수는 0 이상의 정수로 입력하세요.") from error
    if count < 0:
        raise ValueError("팀원 수는 0 이상이어야 합니다.")
    people = []
    for i in range(count):
        old = current[i] if i < len(current) else {}
        person = {"name": ask(f"팀원 {i+1} 이름", old.get("name", "")),
                  "github": ask("GitHub ID", old.get("github", ""))}
        person["roles"] = [x.strip() for x in ask("역할 (쉼표로 구분, 비워둘 수 있음)", ", ".join(ROLES.get(r, r) for r in old.get("roles", []))).split(",") if x.strip()]
        person["features"] = [x.strip() for x in ask("담당 기능 (쉼표로 구분)", ", ".join(old.get("features", []))).split(",") if x.strip()]
        people.append(person)
    me = ask("내 GitHub ID (선택)", existing.get("me") or "")
    meeting = ask("정기회의 시간 (선택)", existing.get("agreements", {}).get("meeting", ""))
    present = {p["github"].lstrip("@").lower() for p in people}
    owners = {key: value if value in present else None for key, value in existing.get("task_owners", {}).items()}
    return {**existing, "name": name, "repository": repository, "members": people, "me": me or None,
            "task_owners": owners,
            "agreements": {**existing.get("agreements", {}), "meeting": meeting}}


def run(args):
    path = config_path()
    if args.team_command == "detect":
        from . import discovery
        result = discovery.detect(use_github=not args.no_gh)
        data = discovery.merge(load(path), result.config)
        if args.apply:
            data = save(data, path)
        if args.json:
            from .cli import emit
            emit(data={"team": data, "sources": result.sources, "warnings": result.warnings, "saved": args.apply})
        else:
            print(data["name"] + "\n  " + (data["repository"] or "저장소 미정"))
            for p in data["members"]:
                print(f'  {p["name"]} (@{p["github"]}) · ' + (", ".join(ROLES.get(r, r) for r in p["roles"]) or "역할 미정"))
            print("내 계정: " + (data["me"] or "미정"))
            print("출처: " + ", ".join(result.sources))
            for warning in result.warnings:
                print("확인: " + warning)
            print("설정 저장됨" if args.apply else "조회만 했습니다. 저장하려면 --apply를 붙이세요.")
        return 0
    interactive = sys.stdin.isatty() and sys.stdout.isatty() and not args.json
    if interactive and (args.team_command != "setup" or not (args.source or args.name or args.repo)):
        try:
            from . import tui, weeks
        except ImportError:
            pass
        else:
            periods = weeks.load(load(path))
            return tui.run(periods, weeks.select(periods), start_tab=2)
    if args.team_command == "setup":
        if args.source:
            raw = json.loads(Path(args.source).read_text(encoding="utf-8"))
        elif args.name:
            raw = {**(load(path) or {}), "name": args.name}
        elif sys.stdin.isatty():
            try:
                raw = setup(load(path))
            except (EOFError, KeyboardInterrupt):
                print("\n설정을 저장하지 않았습니다.")
                return 0
        else:
            raise ValueError("터미널에서 team setup을 실행하거나 --from 설정.json을 지정하세요.")
        if not isinstance(raw, dict):
            raise ValueError("팀 설정은 JSON 객체여야 합니다.")
        if args.name:
            raw["name"] = args.name
        if args.repo is not None:
            raw["repository"] = args.repo
        data = save(raw, path)
        if not args.json:
            print(f"팀 설정 저장: {path}")
    else:
        data = load(path)
    if args.json:
        from .cli import emit
        emit(data={"path": str(path), "team": data})
    elif data is None:
        print("팀 설정 없음\n설정: python main.py team setup")
    else:
        print(f'{data["name"]}\n  {data["repository"] or "저장소 미설정"}')
        for person in data["members"]:
            roles = ", ".join(ROLES.get(r, r) for r in person["roles"]) or "역할 미정"
            features = ", ".join(person["features"]) or "기능 미정"
            print(f'  {person["name"]} (@{person["github"]}) · {roles} · {features}')
        print("\n내 GitHub ID: " + (data["me"] or "미설정"))
        values = bindings(data)
        print("회의록 작성: " + values["task.minutes_writer"])
        print("회의록 제출: " + values["task.minutes_submitter"])
        if data["agreements"].get("meeting"):
            print("정기회의: " + data["agreements"]["meeting"])
        print("승인 기록: " + values["team.approved_changes"])
        print("설정 파일: " + str(path))
    return 0
