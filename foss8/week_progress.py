from pathlib import Path
import tempfile
import os
import sys
import json

from .weeks import roadmap

def progress_path() -> Path:
    override = False
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "foss8" / "week_progress.json"

def create_progress(catalog):
    item = roadmap(catalog)
    progress_data = {}
    for week in item:
        temp = []
        for task in week.get("tasks", []):
            task["completed"] = False
            temp.append(task)
        progress_data[week["id"]] = {"tasks": temp, "memo": ""}
    return progress_data

def write_progress(progress_data, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(progress_data, temp_file, ensure_ascii=False, indent=4)
            temp_file.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def load_progress(catalog) -> dict:
    target = progress_path()
    if target.exists():
        with target.open("r", encoding="utf-8") as file:
            progress_data = json.load(file)
    else:
        progress_data = create_progress(catalog)
        write_progress(progress_data, target)
    return progress_data

def change_completed(progress_data, week_id, task_number) -> None:
    tasks = progress_data[week_id]["tasks"]
    if tasks is None:
        raise ValueError(f"{week_id}의 할 일 목록이 week.json에 없습니다.")
    if not task_number.isdigit():
        raise ValueError("할 일 번호는 숫자로 입력해주세요. 예: week 2 --done 1")
    else:
        task_number = int(task_number)
    if task_number < 1 or task_number > len(tasks):
        raise ValueError(f"할 일 번호가 범위를 벗어났습니다. 1부터 {len(tasks)}까지 입력해주세요.")
    task = tasks[task_number - 1]
    task["completed"] = not task["completed"]
    target = progress_path()
    write_progress(progress_data, target)

def change_memo(progress_data, week_id, memo) -> None:
    progress_data[week_id]["memo"] = memo
    target = progress_path()
    write_progress(progress_data, target)