"""Shell completion from the same catalog and parser used for real commands."""
import os
from pathlib import Path
import re
import shlex

import argcomplete

from .guide import ALIASES, Catalog
from . import templates, weeks


def forms(**kwargs):
    return {name: item["title"] for name, item in templates.listing(Catalog()).items()}


def documents(prefix, **kwargs):
    catalog = Catalog()
    if "#" in prefix:
        selector = prefix.split("#", 1)[0]
        try:
            doc, _ = catalog.resolve(selector)
        except ValueError:
            return []
        return [selector + "#" + anchor for anchor in re.findall(r'<a id="([^"]+)">', doc.markdown)]
    return {**{alias: catalog.resolve(alias)[0].title for alias in ALIASES},
            **{doc.id: doc.title for doc in catalog.documents.values()}}


def week_choices(**kwargs):
    result = {}
    for item in weeks.listing(Catalog()):
        result[item["id"]] = item["label"]
        if item["kind"] != "보강":
            result[str(item["week"])] = item["label"]
    return result


def script(shell):
    return "# foss-8 shell completion\n" + argcomplete.shellcode(["oss"], shell=shell, use_defaults=False)


def install(shell):
    if shell == "bash":
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        path = root / "bash-completion/completions/oss"
    elif shell == "fish":
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        path = root / "fish/completions/oss.fish"
    else:
        raise ValueError('zsh는 eval "$(oss completion zsh)"로 활성화하세요. 지속 적용은 ~/.zshrc에 같은 줄을 추가합니다.')
    if path.exists() and not path.read_text(encoding="utf-8").startswith("# foss-8 shell completion\n"):
        raise ValueError(f"기존 사용자 자동완성 파일을 보호합니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script(shell), encoding="utf-8")
    return str(path), "source " + shlex.quote(str(path))
