import argparse
import json
import sys

from . import __version__
from .guide import ALIASES, Catalog, display_markdown
from . import templates
from . import check
from . import weeks
from pathlib import Path

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
            if args.name is None:
                print("쓸 수 있는 양식:")
                for name, title in templates.TITLES.items():
                    print(f"  {name:12} {title}")
                print("\n예: python main.py format minutes")
            else:
                item = templates.get(Catalog(), args.name)
                print(item["content"], end="")
            return 0
        if args.command == "check":
            # 기존 평가 기준 출력
            items = check.load_result_items()
            print(check.format_result_items(items))

            # 현재 폴더의 기본 파일 검사
            repository_path = Path.cwd()
            results = check.check_required_files(repository_path)

            print()
            print("[기본 파일 검사]")
            print(f"검사 대상: {repository_path}")
            print()
            print(check.format_file_results(results))

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
