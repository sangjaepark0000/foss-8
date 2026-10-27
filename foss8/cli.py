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
    form = commands.add_parser("format", help="양식 출력·UTF-8 파일 저장")
    check = commands.add_parser("check", help="완성 기준 배점표 불러오기, 저장소 상태와 비교" )
    week = commands.add_parser("week", help="주차를 선택해 할 일 조회")
    week.add_argument("week", nargs="?", help="주차 숫자 입력; 생략하면 이번 주 일정 출력")
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
            print("기능 준비중")
            return 0
        if args.command == "check":
            print("기능 준비중")
            return 0
        if args.command == "week":
            catalog = Catalog()
            data = weeks.get_weekly_item(catalog, args.week or weeks.get_this_week(catalog))
            print(weeks.result_line(data))
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