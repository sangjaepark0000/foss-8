import argparse
import json
import sys

from . import __version__
from .guide import ALIASES, Catalog, display_markdown
from . import templates
from . import check
from . import weeks

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
  oss help                           CLI 명령 안내

하위 명령에도 --help를 붙일 수 있습니다.""")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command")
    commands.add_parser("help", help="CLI 전체 명령·사용 예시 보기")
    form = commands.add_parser("format", help="회의록·보고서 빈 양식 출력")
    form.add_argument("name", nargs="?", choices=tuple(templates.TITLES),
                      help="minutes: 회의록, proposal: 제안서, midterm: 중간보고서, final: 최종보고서")
    form.add_argument("--date", help="회의 날짜 (YYYY-MM-DD), 회의록 초안 기본값 오늘")
    form.add_argument("--week", help="회의록 제출 회차 (예: 9), 보강: makeup")
    form.add_argument("--team", help="회의록 팀 이름")
    form.add_argument("--team-file", help="팀 기본정보 JSON 파일 (name·repository·members)")
    form.add_argument("-o", "--output", help="UTF-8 Markdown 저장 경로")
    form.add_argument("--force", action="store_true", help="기존 출력 파일 덮어쓰기")
    check = commands.add_parser("check", help="완성 기준 배점표 불러오기, 저장소 상태와 비교" )
    week = commands.add_parser("week", help="주차를 선택해 할 일 조회")
    return root


def emit(data=None, error=None):
    print(json.dumps({"schema_version": 1, "ok": error is None, "data": data, "error": error}, ensure_ascii=False))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = None
    try:
        command_parser = parser()
        args = command_parser.parse_args(argv)
        if args.command == "help":
            command_parser.print_help()
            return 0
        if args.command == "format":
            if args.force and not args.output:
                raise ValueError("--force는 --output 저장 경로와 함께 지정하세요.")
            filled = any((args.date, args.week, args.team, args.team_file))
            if filled and args.name != "minutes":
                raise ValueError("--date·--week·--team·--team-file은 format minutes에서 사용하세요.")
            if args.output and args.name is None:
                raise ValueError("저장할 양식을 선택하세요. 예: format minutes -o 회의록.md")
            if args.name is None:
                print("쓸 수 있는 양식:")
                for name, title in templates.TITLES.items():
                    print(f"  {name:12} {title}")
                print("\n예: python main.py format minutes")
            else:
                if args.name == "minutes" and (filled or args.output):
                    from . import minutes
                    content = minutes.draft(args.date, args.week, minutes.load_config(args.team_file, args.team))
                else:
                    content = templates.get(Catalog(), args.name)["content"]
                if args.output:
                    from .minutes import save_file
                    if not args.output.lower().endswith((".md", ".markdown")):
                        raise ValueError("서식 저장 경로는 .md 또는 .markdown 파일로 지정하세요.")
                    path = save_file(args.output, content, args.force)
                    print("서식 저장: " + str(path))
                else:
                    print(content, end="")
            return 0
        if args.command == "check":
            print("기능 준비중")
            return 0
        if args.command == "week":
            print("기능 준비중")
            return 0
        if args.command is None:
            print("OSS 팀프로젝트 도구")
            return 0
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
