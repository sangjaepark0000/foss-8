import argparse
import json
import sys

from . import __version__
from .guide import ALIASES, Catalog, display_markdown
from . import templates
from . import check
from . import weeks
from . import team

class RequestError(ValueError):
    def __init__(self, message, help_text):
        super().__init__(message)
        self.help_text = help_text


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RequestError(message, self.format_help())


def parser():
    root = Arguments(prog="oss", description="주차별 할 일·방법·평가기준·양식 조회. 로그인 없이 오프라인으로 동작합니다.",
                     formatter_class=argparse.RawDescriptionHelpFormatter,
                     epilog="""바로 사용:
  oss help                           CLI 명령 안내
  oss week 9                         9주차 할 일과 상세 탐색
  oss week --list                    전체 주차 보기
  oss team setup                     팀 정보 설정

하위 명령에도 --help를 붙일 수 있습니다.""")
    root.add_argument("--version", action="version", version=__version__)
    root.set_defaults(number=None, date=None, list=False, task=None,
                      no_interactive=False, json=False)
    commands = root.add_subparsers(dest="command")
    commands.add_parser("help", help="CLI 전체 명령·사용 예시 보기")
    form = commands.add_parser("format", help="회의록·보고서 빈 양식 출력")
    form.add_argument("name", nargs="?", choices=tuple(templates.TITLES),
                      help="minutes: 회의록, proposal: 제안서, midterm: 중간보고서, final: 최종보고서")
    minutes_parser = commands.add_parser("minutes", help="회의록 작성 파일 생성")
    minutes_commands = minutes_parser.add_subparsers(dest="minutes_command", required=True)
    draft = minutes_commands.add_parser("draft", help="기본정보·제출 회차를 채운 Markdown 초안 저장")
    draft.add_argument("--date", help="회의 날짜 (YYYY-MM-DD), 기본값 오늘")
    draft.add_argument("--week", help="제출 회차 (예: 9), 보강: makeup. 기본값 다음 제출 회차")
    draft.add_argument("-o", "--output", help="Markdown 저장 경로. 기본값 docs/meetings/회의날짜.md")
    draft.add_argument("--force", action="store_true", help="기존 초안 덮어쓰기")
    pdf = minutes_commands.add_parser("pdf", help="완성한 회의록을 제출 파일명의 PDF로 저장")
    pdf.add_argument("source", help="작성한 Markdown 회의록 경로")
    pdf.add_argument("-o", "--output", help="PDF 저장 경로. 기본값 원본 폴더/[WEEK번호] 회의록_팀명.pdf")
    pdf.add_argument("--week", help="문서에 제목이 없을 때 제출 회차 지정. 보강: makeup")
    pdf.add_argument("--team", help="문서에 제목이 없을 때 팀 이름 지정")
    pdf.add_argument("--force", action="store_true", help="기존 PDF 덮어쓰기")
    pdf.add_argument("--browser", help="Chrome/Chromium 실행 파일 경로")
    check = commands.add_parser("check", help="완성 기준 배점표 불러오기, 저장소 상태와 비교" )
    week = commands.add_parser("week", help="주차별 할 일·방법·평가기준 탐색")
    week.add_argument("number", nargs="?", help="강의 주차 (예: 9), 보강: makeup. 생략하면 오늘의 학사 주차")
    week.add_argument("--date", help="기준 날짜 (YYYY-MM-DD)")
    week.add_argument("--list", action="store_true", help="전체 주차·기간 목록")
    week.add_argument("--task", help="바로 펼칠 항목 번호 (예: 1 또는 1.2)")
    week.add_argument("--no-interactive", action="store_true", help="번호 선택 없이 현재 화면만 출력")
    week.add_argument("--json", action="store_true", help="구조화 데이터 출력")
    team_parser = commands.add_parser("team", help="팀·팀원·역할·담당 기능 설정")
    team_commands = team_parser.add_subparsers(dest="team_command")
    team_parser.set_defaults(team_command="show")
    show = team_commands.add_parser("show", help="현재 팀 설정 보기")
    show.add_argument("--json", action="store_true")
    setup = team_commands.add_parser("setup", help="팀 설정 입력·수정")
    setup.add_argument("--from", dest="source", help="JSON 설정 파일 가져오기")
    setup.add_argument("--name", help="팀 이름")
    setup.add_argument("--repo", help="저장소 HTTPS 주소 또는 소유자/저장소")
    setup.add_argument("--json", action="store_true")
    detect = team_commands.add_parser("detect", help="현재 폴더·Git·gh에서 팀 설정 읽기")
    detect.add_argument("--no-gh", action="store_true", help="GitHub 조회 없이 로컬 문서만 읽기")
    detect.add_argument("--apply", action="store_true", help="기존 설정을 유지하며 빠진 정보 저장")
    detect.add_argument("--json", action="store_true")
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
                item = templates.get(Catalog(), args.name, team_config=team.load())
                print(item["content"], end="")
            return 0
        if args.command == "check":
            print("기능 준비중")
            return 0
        if args.command == "minutes":
            from . import minutes
            return minutes.run(args)
        if args.command == "week":
            return weeks.run(args)
        if args.command == "team":
            return team.run(args)
        if args.command is None:
            return weeks.run(args)
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
