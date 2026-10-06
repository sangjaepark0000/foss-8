"""Terminal navigation over the shared, offline catalog."""
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, OptionList, Select, Static
from textual.widgets.option_list import Option

from .guide import Catalog, CATEGORIES, display_markdown
from . import templates
from . import focus
from . import weeks


CONTROL_HINTS = {
    "start-options": "↑↓ 메뉴 선택 · Enter 열기",
    "week-choice": "주차 선택: Enter/Space로 목록 펼치기 · ↑↓ 선택 · Enter 적용",
    "category": "분류 선택: Enter/Space로 목록 펼치기 · ↑↓ 선택 · Enter 적용",
    "search": "검색어 입력 · 예: 회의록 제출, 중간보고서 · Enter로 결과 목록 이동",
    "results": "↑↓ 항목 선택 · Enter 본문 열기",
    "week-reader": "↑↓/PgUp/PgDn 본문 스크롤 · Tab으로 링크·버튼 이동",
    "reader": "↑↓/PgUp/PgDn 본문 스크롤 · Ctrl+S 본문/양식 저장",
    "focus-text": "↑↓/PgUp/PgDn 스크롤 · 아래 버튼에서 회의록 양식 저장",
    "week-checklist": "Enter: 선택한 주차의 개인 점검표와 할 일 전환",
    "week-deadline": "Enter: 오늘 기준 가장 가까운 제출 마감 확인",
    "week-back": "Enter: 처음 화면으로 돌아가기",
    "focus-save": "Enter: 빈 회의록 양식의 저장 경로 입력",
    "focus-back": "Enter: 이전 화면으로 돌아가기",
    "destination": "저장 경로 입력 · 예: 회의록.md, docs/meetings/회의록.md · Enter 저장",
    "confirm-save": "Enter: 입력한 경로에 저장 · 기존 파일은 보호합니다",
    "cancel-save": "Enter: 저장 취소",
}
START_HINTS = [
    "주차별 할 일: 주차를 골라 할 일·제출물·개인 점검표 확인",
    "회의록 양식 저장: 빈 양식을 파일로 저장하고 작성",
    "검색: 안내서 전체 검색 · 예: 회의록 제출, 중간보고서",
    "전체 안내서: 모든 장·부록을 목록에서 선택해 읽기",
]


class HelpHint(Static):
    DEFAULT_CSS = """
    HelpHint { height: auto; min-height: 2; max-height: 4; margin-top: 1;
               padding: 0 1; color: $text-muted; background: $panel; }
    """

    def __init__(self, hint, **kwargs):
        super().__init__(Text(hint + "\nTab 다음 · Shift+Tab 이전 · F1 도움말 · Ctrl+Q 종료"), **kwargs)

    def show_hint(self, hint):
        self.update(Text(hint + "\nTab 다음 · Shift+Tab 이전 · F1 도움말 · Ctrl+Q 종료"))


class HelpScreen(ModalScreen):
    CSS = """
    HelpScreen { align: center middle; background: $background 70%; }
    #help-card { width: 76; max-width: 96%; height: 90%; border: round $accent; padding: 0 1; background: $surface; }
    #help-reader { height: 1fr; }
    #help-close { margin: 1 0; }
    """
    BINDINGS = [("escape,f1", "close", "닫기"), ("ctrl+q", "app.quit", "종료")]

    def compose(self):
        with Vertical(id="help-card"):
            with VerticalScroll(id="help-reader"):
                yield Markdown("""# TUI 사용법

- **Tab / Shift+Tab**: 다음 / 이전 영역. 아래 힌트가 현재 영역에 맞게 바뀝니다.
- **Enter / Space**: 주차·분류 선택 상자의 후보 목록을 펼칩니다. ↑↓로 고르고 Enter로 적용합니다. Esc는 목록만 닫습니다.
- **↑↓ / Enter**: 메뉴·문서·양식 목록에서 선택하고 엽니다.
- **↑↓ / PgUp / PgDn**: 본문에 포커스가 있을 때 스크롤합니다.
- **Esc**: 이전 화면·문서로 돌아갑니다. 저장 창에서는 취소합니다.
- **/**: 전체 검색으로 이동합니다. 검색창에는 `회의록 제출`, `중간보고서`처럼 입력합니다. Enter로 결과 목록으로 이동합니다.
- **Ctrl+S**: 현재 본문·양식을 저장합니다. 첫 화면·주차 화면·가까운 제출 화면에서는 빈 회의록 양식을 저장합니다.
- **Ctrl+Q**: 종료합니다.

회의록 이외의 양식은 **전체 안내서 → 분류: 양식 저장**에서 선택하세요. 버튼은 Tab으로 이동한 뒤 Enter로 실행하고, 마우스로도 선택할 수 있습니다.

**Esc 또는 F1로 닫으면 원래 작업하던 곳으로 돌아갑니다.**
""", open_links=False)
            yield Button("닫기 · Esc / F1", id="help-close")

    @on(Button.Pressed, "#help-close")
    def action_close(self):
        self.dismiss(None)


class StartScreen(Screen):
    BINDINGS = [("escape", "stay", "")]
    CSS = """
    StartScreen { align: center middle; }
    #start { width: 64; max-width: 95%; height: auto; padding: 2 3; border: round $accent; }
    #start-title { height: auto; margin-bottom: 1; text-style: bold; }
    #start-options { height: auto; border: none; }
    """

    def compose(self):
        with Vertical(id="start"):
            yield Label("OSS · 무엇이 필요하세요?", id="start-title")
            yield OptionList("주차별 할 일", "회의록 양식 저장", "검색", "전체 안내서", id="start-options")
            yield HelpHint("↑↓ 메뉴 선택 · Enter 열기", id="start-hint")

    def on_mount(self):
        self.query_one(OptionList).focus()

    def action_stay(self):
        pass

    @on(OptionList.OptionHighlighted, "#start-options")
    def highlight(self, event):
        self.query_one(HelpHint).show_hint(START_HINTS[event.option_index] + " · ↑↓ / Enter")

    @on(OptionList.OptionSelected)
    async def choose(self, event):
        index = event.option_index
        if index == 1:
            self.app.save_minutes()
            return
        if index == 0:
            self.app.push_screen(WeekScreen())
            return
        self.app.pop_screen()
        if index == 2:
            self.app.action_search()
        else:
            self.app.query_one("#category", Select).value = "전체 안내서"
            self.app.query_one("#results", OptionList).focus()


class WeekScreen(Screen):
    CSS = """
    WeekScreen { align: center middle; }
    #week-card { width: 94; max-width: 98%; height: 96%; border: round $accent; padding: 0 2; }
    #week-choice { margin: 1 0; }
    #week-reader { height: 1fr; }
    #week-content { padding: 0; }
    #week-content MarkdownH1 { display: none; }
    #week-content MarkdownH2 { margin: 1 0 0 0; }
    #week-buttons { height: auto; }
    #week-buttons Button { min-width: 10; margin-right: 1; }
    """
    BINDINGS = [("escape", "back", "뒤로")]

    def __init__(self):
        super().__init__()
        self.selected = None
        self.checklist = False

    def compose(self):
        items = weeks.listing(self.app.catalog)
        with Vertical(id="week-card"):
            yield Select([(item["label"], item["id"]) for item in items], value=weeks.default(self.app.catalog), allow_blank=False, id="week-choice")
            with VerticalScroll(id="week-reader"):
                yield Markdown("", open_links=False, id="week-content")
            with Horizontal(id="week-buttons"):
                yield Button("개인 점검표", id="week-checklist")
                yield Button("가까운 제출", id="week-deadline")
                yield Button("처음으로", id="week-back")
            yield HelpHint(CONTROL_HINTS["week-choice"])

    async def on_mount(self):
        await self.update_week()

    async def update_week(self):
        self.selected = weeks.get(self.app.catalog, str(self.query_one("#week-choice", Select).value))
        await self.query_one("#week-content", Markdown).update(weeks.markdown(self.selected, self.checklist))
        self.query_one("#week-reader", VerticalScroll).scroll_home(animate=False)

    @on(Select.Changed, "#week-choice")
    async def selected_week(self):
        self.checklist = False
        self.query_one("#week-checklist", Button).label = "개인 점검표"
        await self.update_week()

    @on(Button.Pressed, "#week-checklist")
    async def show_checklist(self):
        self.checklist = not self.checklist
        self.query_one("#week-checklist", Button).label = "할 일 보기" if self.checklist else "개인 점검표"
        await self.update_week()

    @on(Button.Pressed, "#week-deadline")
    def deadline(self):
        self.app.push_screen(FocusScreen())

    @on(Button.Pressed, "#week-back")
    def action_back(self):
        self.app.pop_screen()

    @on(Markdown.LinkClicked)
    async def link(self, event):
        self.app.open_browser()
        await self.app.follow_link(event)


class FocusScreen(Screen):
    CSS = """
    FocusScreen { align: center middle; }
    #focus-card { width: 74; max-width: 98%; height: 90%; border: round $accent; padding: 1 2; }
    #focus-text { height: 1fr; }
    #focus-buttons { height: auto; }
    #focus-buttons Button { margin-right: 1; }
    """
    BINDINGS = [("escape", "back", "뒤로")]

    def compose(self):
        with Vertical(id="focus-card"):
            with VerticalScroll(id="focus-text"):
                yield Markdown(focus.markdown(focus.next_submissions(self.app.catalog)), open_links=False)
            with Horizontal(id="focus-buttons"):
                yield Button("회의록 양식 저장", id="focus-save", variant="primary")
                yield Button("뒤로", id="focus-back")
            yield HelpHint(CONTROL_HINTS["focus-text"])

    @on(Button.Pressed, "#focus-save")
    def save(self):
        self.app.save_minutes()

    @on(Button.Pressed, "#focus-back")
    def action_back(self):
        self.app.pop_screen()

    @on(Markdown.LinkClicked)
    async def link(self, event):
        self.app.open_browser()
        await self.app.follow_link(event)


class SaveScreen(ModalScreen):
    CSS = """
    SaveScreen { align: center middle; background: $background 70%; }
    #save-dialog { width: 66; max-width: 96%; height: auto; border: thick $accent; background: $surface; padding: 1 2; }
    #save-dialog Label { height: auto; margin-bottom: 1; }
    #save-error { height: auto; color: $error; }
    #save-buttons { height: 3; margin-top: 1; }
    """
    BINDINGS = [("escape", "dismiss", "취소"), ("f1", "app.help", "도움말"),
                ("ctrl+q", "app.quit", "종료")]

    def __init__(self, content, filename):
        super().__init__()
        self.content, self.filename = content, filename

    def compose(self) -> ComposeResult:
        with Vertical(id="save-dialog"):
            yield Label("UTF-8 Markdown 저장 · 기존 파일은 덮어쓰지 않습니다")
            yield Input(self.filename, id="destination")
            yield Static("", id="save-error")
            with Horizontal(id="save-buttons"):
                yield Button("저장", id="confirm-save", variant="primary")
                yield Button("취소", id="cancel-save")
            yield HelpHint(CONTROL_HINTS["destination"])

    def on_mount(self):
        self.query_one(Input).focus()

    @on(Button.Pressed, "#cancel-save")
    def cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#confirm-save")
    @on(Input.Submitted, "#destination")
    def save(self):
        destination = self.query_one("#destination", Input).value.strip()
        if not destination:
            self.query_one("#save-error", Static).update("파일 경로를 입력하세요.")
            return
        try:
            self.dismiss(templates.save(self.content, destination))
        except OSError as error:
            message = "파일이 이미 있습니다. 다른 이름으로 저장하세요." if isinstance(error, FileExistsError) else str(error)
            self.query_one("#save-error", Static).update(message)


class GuideApp(App):
    TITLE = "OSS 안내서"
    SUB_TITLE = "2026-2 · v1.3 · 48쪽 전체"
    CSS = """
    #body { height: 1fr; }
    #navigation { width: 36; min-width: 24; border-right: solid $primary; padding: 0 1; }
    #category { margin-top: 1; }
    #search { margin: 1 0; }
    #results { height: 1fr; }
    #detail { width: 1fr; }
    #context { height: auto; max-height: 4; padding: 0 1; background: $panel; color: $text-muted; }
    #reader { height: 1fr; padding: 0 2; }
    #status { margin-top: 0; }
    """
    BINDINGS = [
        Binding("/", "search", "검색"), Binding("escape", "back", "뒤로"),
        Binding("ctrl+s", "save", "저장"), Binding("ctrl+q", "quit", "종료"),
        Binding("f1", "help", "도움말"),
    ]

    def __init__(self):
        super().__init__()
        self.catalog = Catalog()
        self.forms = templates.listing(self.catalog)
        self.history = []
        self.current = None
        self.current_content = ""
        self.current_filename = "안내서.md"
        self.entries = []
        self.search_summary = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="navigation"):
                categories = ["하려는 일", "주차·활동·평가", "양식 저장", "전체 안내서", "팀 결정·출처"]
                yield Select([(label, label) for label in categories], value="하려는 일", allow_blank=False, id="category")
                yield Input(placeholder="전체 검색 · Enter로 목록 이동", id="search")
                yield OptionList(id="results")
            with Vertical(id="detail"):
                yield Static("", id="context")
                with VerticalScroll(id="reader"):
                    yield Markdown("", id="document", open_links=False)
        yield HelpHint(CONTROL_HINTS["results"], id="status")
        yield Footer()

    async def on_mount(self):
        self.populate()
        await self.navigate("home")
        self.query_one("#results", OptionList).focus()
        self.push_screen(StartScreen())

    def populate(self):
        query = self.query_one("#search", Input).value.strip()
        category = self.query_one("#category", Select).value
        self.search_summary = ""
        if query:
            hits, count = self.catalog.search(query, limit=100)
            self.entries = [hit["selector"] for hit in hits]
            options = [Option(Text(f"{hit['title']}\n{hit['excerpt'][:100]}"), id=str(i)) for i, hit in enumerate(hits)]
            self.search_summary = f"검색 {count}개 · 표시 {len(hits)}개"
        elif category == "양식 저장":
            self.entries = ["template:" + name for name in self.forms]
            options = [Option(Text(item["title"]), id=str(i)) for i, item in enumerate(self.forms.values())]
        else:
            selectors = [doc.id for doc in self.catalog.documents.values() if doc.pages] if category == "전체 안내서" else CATEGORIES[str(category)]
            self.entries = selectors
            options = [Option(Text(self.catalog.resolve(selector)[0].title), id=str(i)) for i, selector in enumerate(selectors)]
        listing = self.query_one("#results", OptionList)
        listing.clear_options()
        listing.add_options(options)
        if options:
            listing.highlighted = 0
        self.refresh_hint()

    @on(events.DescendantFocus)
    def focus_changed(self, event):
        self.refresh_hint(event.widget)

    def refresh_hint(self, widget=None):
        if widget is not None and widget.screen is not self.screen:
            return
        hints = self.screen.query(HelpHint)
        if not hints:
            return
        widget = widget or self.screen.focused
        while widget is not None:
            if widget.id in CONTROL_HINTS:
                hint = CONTROL_HINTS[widget.id]
                if isinstance(widget, Select) and widget.expanded:
                    hint = "↑↓ 후보 선택 · Enter 적용 · Esc 목록 닫기"
                elif widget.id == "start-options":
                    hint = START_HINTS[widget.highlighted or 0] + " · ↑↓ / Enter"
                elif widget.id in ("search", "results") and self.search_summary:
                    hint = self.search_summary + " · " + hint
                hints.first().show_hint(hint)
                return
            widget = widget.parent

    def action_help(self):
        if not isinstance(self.screen, HelpScreen):
            self.push_screen(HelpScreen())

    @on(Input.Changed, "#search")
    def search_changed(self):
        self.populate()

    @on(Input.Submitted, "#search")
    def search_submitted(self):
        self.query_one("#results", OptionList).focus()

    @on(Select.Changed, "#category")
    def category_changed(self):
        if self.is_mounted:
            self.query_one("#search", Input).value = ""
            self.populate()

    @on(OptionList.OptionSelected, "#results")
    async def selected(self, event):
        await self.navigate(self.entries[event.option_index])
        self.query_one("#reader", VerticalScroll).focus()

    async def navigate(self, selector, remember=True):
        if selector.startswith("template:"):
            name = selector.split(":", 1)[1]
            item = templates.get(self.catalog, name)
            content = "# " + item["title"] + "\n\n" + item["content"]
            source = item["source"]
            self.current_content = item["content"]
            self.current_filename = {
                "readme": "README.md", "contributing": "CONTRIBUTING.md",
                "code-of-conduct": "CODE_OF_CONDUCT.md", "requirements": "requirements.txt",
                "main": "main.py", "gitignore": ".gitignore", "pull-request": "PULL_REQUEST_TEMPLATE.md",
            }.get(name, name + ".md")
            if name == "minutes":
                content = "> 원문 부록 B에서 예시 사실을 비운 양식입니다. 저장 후 주차·팀명·날짜를 채우세요.\n\n" + content
        else:
            item = self.catalog.show(selector)
            content = display_markdown(item["markdown"])
            source = item["source"]
            self.current_content = item["markdown"]
            self.current_filename = item["id"] + ".md"
        if remember and self.current and selector != self.current:
            self.history.append(self.current)
        self.current = selector
        pages = ", ".join(map(str, source["pages"]))
        context = f"{selector} · 원문 {pages}쪽" if pages else f"{selector} · 팀 결정" if source["scope"] == "team-decision" else f"{selector} · 탐색·출처"
        self.query_one("#context", Static).update(Text(context))
        await self.query_one("#document", Markdown).update(content)
        self.query_one("#reader", VerticalScroll).scroll_home(animate=False)

    @on(Markdown.LinkClicked)
    async def follow_link(self, event):
        event.stop()
        target = urlsplit(event.href)
        if target.scheme or target.netloc:
            self.notify(event.href, title="외부 링크 · 오프라인 도구", timeout=10)
            return
        path = unquote(target.path)
        if path.endswith(".pdf"):
            self.notify(str(self.catalog.root.joinpath(path)), title="함께 설치된 원문 PDF", timeout=12)
            return
        if path.startswith("../"):
            self.notify("이 문서는 팀 저장소에서 확인하세요: " + event.href, timeout=8)
            return
        current_doc = self.current.split("#", 1)[0] if not self.current.startswith("template:") else "templates"
        selector = PurePosixPath(path).name if path else current_doc
        if target.fragment:
            selector += "#" + unquote(target.fragment)
        try:
            await self.navigate(selector)
        except ValueError as error:
            self.notify(str(error), severity="warning")

    def action_search(self):
        self.open_browser()
        self.query_one("#search", Input).focus()

    def open_browser(self):
        while len(self.screen_stack) > 1:
            self.pop_screen()

    async def action_back(self):
        if self.history:
            await self.navigate(self.history.pop(), remember=False)
        elif self.current == "home":
            self.push_screen(StartScreen())
            return
        self.query_one("#results", OptionList).focus()

    def action_save(self):
        if isinstance(self.screen, (StartScreen, WeekScreen, FocusScreen)):
            self.save_minutes()
            return
        def saved(path):
            if path:
                self.notify(path, title="저장했습니다", timeout=8)
        self.push_screen(SaveScreen(self.current_content, self.current_filename), saved)

    def save_minutes(self):
        def saved(path):
            if path:
                self.notify(path, title="회의록 양식을 저장했습니다", timeout=8)
        self.push_screen(SaveScreen(templates.get(self.catalog, "minutes")["content"], "회의록.md"), saved)
