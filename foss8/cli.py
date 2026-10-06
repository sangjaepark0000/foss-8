# PYTHON_ARGCOMPLETE_OK
"""Non-interactive interface; JSON stdout contains only one versioned envelope."""
import argparse
import json
import sys
from datetime import date

import argcomplete
from argcomplete.completers import FilesCompleter, SuppressCompleter

from . import __version__
from .guide import ALIASES, Catalog, display_markdown
from . import templates
from . import focus
from . import weeks
from . import completion


class RequestError(ValueError):
    def __init__(self, message, help_text):
        super().__init__(message)
        self.help_text = help_text


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RequestError(message, self.format_help())


def parser():
    root = Arguments(prog="oss", description="OSS 안내서 탐색·전체 검색·양식 저장. 조회는 로그인 없이 오프라인으로 동작합니다.",
                     formatter_class=argparse.RawDescriptionHelpFormatter,
                     epilog="""바로 사용:
  oss week 6                         6주차 할 일·제출물
  oss format                         쓸 수 있는 양식 목록
  oss guide                          안내서 조회 명령 안내
  oss guide search '회의록 제출'       전체 검색
  oss help                           CLI 명령 안내 (TUI를 열지 않음)
  oss completion bash --install      Tab 자동완성 설치

하위 명령에도 --help를 붙일 수 있습니다. 예: oss format --help""")
    root.context = {}
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command")
    commands.add_parser("help", help="CLI 전체 명령·사용 예시 보기")
    complete = commands.add_parser("completion", help="Bash/zsh/fish Tab 자동완성 출력·설치")
    complete.add_argument("shell", choices=["bash", "zsh", "fish"], nargs="?", default="bash")
    complete.add_argument("--install", action="store_true", help="Bash/fish 사용자용 자동완성 파일 설치")
    commands.add_parser("browse", help="키보드로 탐색하는 TUI 열기")
    now = commands.add_parser("now", help="가장 가까운 제출만 확인")
    now.add_argument("--date", type=date.fromisoformat, help="기준일 YYYY-MM-DD; 기본은 한국 날짜")
    now.add_argument("--json", action="store_true")
    week = commands.add_parser("week", help="주차를 선택해 할 일·제출·개인 점검표 조회")
    week.add_argument("week", nargs="?", help="주차 숫자 또는 일정 ID; 생략하면 가장 가까운 일정").completer = completion.week_choices
    week.add_argument("--makeup", action="store_true", help="4주차 12/11 보강 선택")
    week.add_argument("--list", action="store_true")
    week.add_argument("--json", action="store_true")
    week.add_argument("--checklist", action="store_true", help="부록 A 개인 점검표 표시")
    guide = commands.add_parser("guide", help="안내서 목록·검색·본문 조회",
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog="""예시:
  oss guide list                       문서 ID 목록
  oss guide show minutes               회의록 안내
  oss guide show calendar              주차별 로드맵
  oss guide search '회의록 제출'         전체 검색""")
    root.context["guide"] = guide
    actions = guide.add_subparsers(dest="action")
    listing = actions.add_parser("list", help="안정적인 문서 ID와 원문 위치 목록")
    listing.add_argument("--json", action="store_true")
    show = actions.add_parser("show", help="문서 ID 또는 ID#원문앵커로 본문 조회")
    root.context["show"] = show
    show.add_argument("id", nargs="?", help="예: minutes, calendar, evaluation, 12-minutes#section-12-1").completer = completion.documents
    show.add_argument("--format", choices=["markdown", "text"], default="markdown")
    show.add_argument("--json", action="store_true")
    search = actions.add_parser("search", help="안내서·팀 결정 전체 본문 검색; 공백으로 나눈 단어는 모두 일치")
    root.context["search"] = search
    search.add_argument("query", nargs="?", help="검색어 · 예: '회의록 제출', 중간보고서")
    search.add_argument("--limit", type=int, default=30)
    search.add_argument("--json", action="store_true")
    form = commands.add_parser("format", help="양식 출력·UTF-8 파일 저장",
                               formatter_class=argparse.RawDescriptionHelpFormatter,
                               epilog="""예시:
  oss format                           지원 양식 목록
  oss format minutes                   빈 회의록 양식 출력
  oss format minutes -o 회의록.md       파일로 저장
  oss format minutes-example           원문 작성 예시
  oss format --list --json              에이전트용 목록""")
    form.add_argument("name", nargs="?", help="minutes는 빈 양식, minutes-example은 원문 예시").completer = completion.forms
    form.add_argument("--list", action="store_true", help="지원 양식 목록")
    form.add_argument("--output", "-o", help="저장할 파일; 기본 동작은 stdout 출력").completer = FilesCompleter()
    form.add_argument("--force", action="store_true", help="명시한 저장 파일을 덮어쓰기")
    form.add_argument("--json", action="store_true")
    return root


def emit(data=None, error=None):
    print(json.dumps({"schema_version": 1, "ok": error is None, "data": data, "error": error}, ensure_ascii=False))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = None
    try:
        command_parser = parser()
        argcomplete.autocomplete(command_parser, always_complete_options=False, default_completer=SuppressCompleter())
        args = command_parser.parse_args(argv)
        if args.command == "help":
            command_parser.print_help()
            return 0
        if args.command == "completion":
            if args.install:
                path, activate = completion.install(args.shell)
                print(f"자동완성 설치 완료: {path}\n새 터미널에서 사용하세요. 현재 터미널에 바로 적용:\n{activate}")
            else:
                print(completion.script(args.shell), end="")
            return 0
        if args.command == "browse" or (args.command is None and sys.stdin.isatty() and sys.stdout.isatty()):
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError("TUI에는 터미널이 필요합니다. 자동화에서는 oss guide 명령을 사용하세요.")
            from .tui import GuideApp
            GuideApp().run()
            return 0
        if args.command is None:
            print("OSS 팀프로젝트 도구\n\noss                        터미널에서 첫 화면 열기\noss week 6                 6주차 할 일·제출물\noss now                    가까운 제출 마감\noss guide search 회의록     전체 검색\noss format minutes         빈 회의록 양식\noss --help                 명령 안내\n\n안내서: 2026-2 v1.3 · 48쪽 전체. 팀 결정은 team 문서에서 확인합니다.")
            return 0
        catalog = Catalog()
        if args.command == "now":
            data = focus.next_submissions(catalog, args.date)
            emit(data) if args.json else print(focus.markdown(data))
            return 0
        if args.command == "week":
            if args.list:
                data = weeks.listing(catalog)
                if args.json:
                    emit(data)
                else:
                    for item in data:
                        print(f"{item['id']:20} {item['label']}")
            else:
                data = weeks.get(catalog, args.week or ("4" if args.makeup else weeks.default(catalog)), args.makeup)
                emit(data) if args.json else print(weeks.markdown(data, args.checklist))
            return 0
        if args.command == "guide":
            if args.action is None:
                if "--json" in argv:
                    raise ValueError("guide 다음에 list, show 또는 search를 지정하세요.")
                command_parser.context["guide"].print_help()
                return 0
            if args.action == "list":
                data = catalog.listing()
                if args.json:
                    emit(data)
                else:
                    for item in data:
                        print(f"{item['id']:30} {item['title']}")
            elif args.action == "show":
                if not args.id:
                    if args.json:
                        raise ValueError("문서 ID가 필요합니다. oss guide list --json으로 확인하세요.")
                    command_parser.context["show"].print_help()
                    print("\n쓸 수 있는 문서 (전체 ID는 oss guide list):")
                    for name, target in ALIASES.items():
                        print(f"  {name:16} {catalog.resolve(target)[0].title}")
                    return 0
                data = catalog.show(args.id)
                if args.json:
                    emit(data)
                else:
                    print(display_markdown(data["markdown"]) if args.format == "text" else data["markdown"], end="")
            else:
                if not args.query:
                    if args.json:
                        raise ValueError("검색어가 필요합니다. 예: oss guide search '회의록 제출' --json")
                    command_parser.context["search"].print_help()
                    return 0
                if args.limit < 1 or args.limit > 1000:
                    raise ValueError("--limit은 1~1000이어야 합니다.")
                hits, count = catalog.search(args.query, args.limit)
                if args.json:
                    emit({"query": args.query, "total": count, "results": hits})
                else:
                    print(f"검색 결과 {count}개 (표시 {len(hits)}개)")
                    for hit in hits:
                        page = ",".join(map(str, hit["source"]["pages"])) or "탐색·팀 문서"
                        print(f"\n{hit['selector']} · {hit['title']} · 원문 {page}\n  {hit['excerpt']}")
        else:
            if args.list or (args.name is None and not args.output):
                if args.name or args.output:
                    raise ValueError("--list는 양식 이름·--output과 함께 사용할 수 없습니다.")
                data = [{"id": name, "title": item["title"], "derived": item["derived"], "source": item["source"]}
                        for name, item in templates.listing(catalog).items()]
                if args.json:
                    emit(data)
                else:
                    print("쓸 수 있는 양식:")
                    for item in data:
                        print(f"{item['id']:22} {item['title']}")
                    print("\n예: oss format minutes\n저장: oss format minutes -o 회의록.md\n전체 옵션: oss format --help")
            else:
                if not args.name:
                    raise ValueError("양식 이름 또는 --list를 지정하세요.")
                try:
                    data = templates.get(catalog, args.name)
                except ValueError as error:
                    names = ", ".join(templates.listing(catalog))
                    raise ValueError(f"{error}\n지원 양식: {names}") from error
                if args.output:
                    data["saved_to"] = templates.save(data["content"], args.output, args.force)
                if args.json:
                    emit(data)
                elif args.output:
                    print(data["saved_to"])
                else:
                    print(data["content"], end="")
        return 0
    except (ValueError, OSError) as error:
        message = str(error)
        if isinstance(error, FileExistsError):
            message = "파일이 이미 있습니다. 다른 경로를 지정하거나 --force로 덮어쓰기를 명시하세요."
        if getattr(args, "json", False) or "--json" in argv:
            emit(error={"code": "invalid_request" if isinstance(error, ValueError) else "file_error", "message": message})
        else:
            print(f"오류: {message}", file=sys.stderr)
            if isinstance(error, RequestError):
                print("\n" + error.help_text, file=sys.stderr)
        return 2
