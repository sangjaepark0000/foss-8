"""Non-interactive interface; JSON stdout contains only one versioned envelope."""
import argparse
import json
import sys

from . import __version__
from .guide import Catalog, display_markdown
from . import templates


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message + ". oss --help로 명령 형식을 확인하세요.")


def parser():
    root = Arguments(prog="oss", description="OSS 안내서 탐색·전체 검색·양식 저장. 조회는 로그인 없이 오프라인으로 동작합니다.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command")
    commands.add_parser("browse", help="키보드로 탐색하는 TUI 열기")
    guide = commands.add_parser("guide", help="안내서 목록·검색·본문 조회")
    actions = guide.add_subparsers(dest="action", required=True)
    listing = actions.add_parser("list", help="안정적인 문서 ID와 원문 위치 목록")
    listing.add_argument("--json", action="store_true")
    show = actions.add_parser("show", help="문서 ID 또는 ID#원문앵커로 본문 조회")
    show.add_argument("id", help="예: minutes, calendar, evaluation, 12-minutes#section-12-1")
    show.add_argument("--format", choices=["markdown", "text"], default="markdown")
    show.add_argument("--json", action="store_true")
    search = actions.add_parser("search", help="안내서·팀 결정 전체 본문 검색; 공백으로 나눈 단어는 모두 일치")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=30)
    search.add_argument("--json", action="store_true")
    form = commands.add_parser("format", help="양식 출력·UTF-8 파일 저장")
    form.add_argument("name", nargs="?", help="minutes는 빈 양식, minutes-example은 원문 예시")
    form.add_argument("--list", action="store_true", help="지원 양식 목록")
    form.add_argument("--output", "-o", help="저장할 파일; 기본 동작은 stdout 출력")
    form.add_argument("--force", action="store_true", help="명시한 저장 파일을 덮어쓰기")
    form.add_argument("--json", action="store_true")
    return root


def emit(data=None, error=None):
    print(json.dumps({"schema_version": 1, "ok": error is None, "data": data, "error": error}, ensure_ascii=False))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = None
    try:
        args = parser().parse_args(argv)
        if args.command is None:
            print("OSS 팀프로젝트 도구\n\noss browse                 안내서 탐색\noss guide search 회의록     전체 검색\noss format minutes         빈 회의록 양식\noss --help                 명령 안내\n\n안내서: 2026-2 v1.3 · 48쪽 전체. 팀 결정은 team 문서에서 확인합니다.")
            return 0
        if args.command == "browse":
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError("TUI에는 터미널이 필요합니다. 자동화에서는 oss guide 명령을 사용하세요.")
            from .tui import GuideApp
            GuideApp().run()
            return 0
        catalog = Catalog()
        if args.command == "guide":
            if args.action == "list":
                data = catalog.listing()
                if args.json:
                    emit(data)
                else:
                    for item in data:
                        print(f"{item['id']:30} {item['title']}")
            elif args.action == "show":
                data = catalog.show(args.id)
                if args.json:
                    emit(data)
                else:
                    print(display_markdown(data["markdown"]) if args.format == "text" else data["markdown"], end="")
            else:
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
            if args.list:
                if args.name or args.output:
                    raise ValueError("--list는 양식 이름·--output과 함께 사용할 수 없습니다.")
                data = [{"id": name, "title": item["title"], "derived": item["derived"], "source": item["source"]}
                        for name, item in templates.listing(catalog).items()]
                if args.json:
                    emit(data)
                else:
                    for item in data:
                        print(f"{item['id']:22} {item['title']}")
            else:
                if not args.name:
                    raise ValueError("양식 이름 또는 --list를 지정하세요.")
                data = templates.get(catalog, args.name)
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
        return 2
