"""Manual completion marks, independent of submission evidence and grades."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile


def context(config):
    config = config or {}
    repository = config.get("repository", "").rstrip("/").removesuffix(".git")
    return json.dumps([repository, config.get("me") or "local"], ensure_ascii=False)


def read(path):
    if not path.exists():
        return {"schema_version": 1, "contexts": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("contexts"), dict):
        raise ValueError("완료 기록 형식을 확인하세요.")
    for scope, records in data["contexts"].items():
        if not isinstance(scope, str) or not isinstance(records, dict):
            raise ValueError("완료 기록의 사용자·작업 형식을 확인하세요.")
        for key, record in records.items():
            if not isinstance(key, str) or not isinstance(record, dict) or type(record.get("completed")) is not bool:
                raise ValueError("완료 기록의 상태 형식을 확인하세요.")
    return data


def write(path, data):
    """Replace local state only after the complete new file has been written."""
    path = Path(path)
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


class Progress:
    def __init__(self, path):
        self.path = Path(path)
        self.error = None
        try:
            self.data = read(self.path)
        except (ValueError, OSError) as error:
            self.data = {"schema_version": 1, "contexts": {}}
            self.error = str(error)

    def done(self, scope, key):
        return self.data["contexts"].get(scope, {}).get(key, {}).get("completed") is True

    def toggle(self, scope, key):
        if self.error:
            raise ValueError("완료 기록을 읽지 못했습니다. 기록 파일을 확인한 뒤 다시 실행하세요.")
        data = read(self.path)  # Preserve marks saved by another running instance.
        records = data["contexts"].setdefault(scope, {})
        completed = not records.get(key, {}).get("completed", False)
        records[key] = {"completed": completed, "source": "manual",
                        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        write(self.path, data)
        self.data = data
        return completed
