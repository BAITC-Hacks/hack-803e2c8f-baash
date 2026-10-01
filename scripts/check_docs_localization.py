"""Validate the offline RU/EN/KK documentation graph and structural parity."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

LANGUAGES = ("ru", "en", "kk")
LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
REFERENCE = re.compile(r"^\s*\[[^]]+\]:\s*(\S+)", re.MULTILINE)
PLACEHOLDER = re.compile(
    r"translation pending|translation goes here|TODO[: ]+translat|"
    r"перевод (?:будет добавлен|в процессе)|аударма (?:кейін қосылады|дайын емес)",
    re.IGNORECASE,
)


def family(path: Path) -> Path:
    return path.with_name(re.sub(r"\.(?:en|kk)\.md$", ".md", path.name))


def variant(path: Path, language: str) -> Path:
    return path if language == "ru" else path.with_name(f"{path.stem}.{language}.md")


def switcher(path: Path) -> str:
    return " · ".join(
        f"[{label}]({variant(path, language).name})"
        for language, label in zip(LANGUAGES, ("Русский", "English", "Қазақша"), strict=True)
    )


def prose(text: str) -> str:
    return re.sub(r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text, flags=re.MULTILINE | re.DOTALL)


def headings(text: str) -> list[tuple[int, str]]:
    return [
        (len(match[1]), match[2].strip().rstrip("#").strip())
        for match in re.finditer(r"^(#{1,6})\s+(.+)$", prose(text), re.MULTILINE)
    ]


def slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).lower()
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = "".join(char for char in text if char in " -_" or unicodedata.category(char)[0] in "LN")
    return text.replace(" ", "-")


def anchors(text: str) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    for _, title in headings(text):
        base = slug(title)
        number = counts.get(base, 0)
        counts[base] = number + 1
        result.add(base if number == 0 else f"{base}-{number}")
    result.update(re.findall(r"(?:id|name)=[\"\']([^\"\']+)", text))
    return result


def fences(text: str) -> list[tuple[str, str]]:
    result = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", lines[index])
        if not match:
            index += 1
            continue
        delimiter, language = match.groups()
        body = []
        index += 1
        while index < len(lines) and not re.match(rf"^\s*{re.escape(delimiter)}\s*$", lines[index]):
            body.append(lines[index])
            index += 1
        if index == len(lines):
            raise ValueError("unclosed code fence")
        result.append((language.strip(), "\n".join(body)))
        index += 1
    return result


def tracked_markdown(root: Path) -> list[Path]:
    result = subprocess.run(  # noqa: S603
        [
            shutil.which("git") or "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "*.md",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted({root / name for name in result.stdout.splitlines()})


def validate(root: Path, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    families = sorted({family(path) for path in paths})
    all_paths = set(paths)
    for source in families:
        texts: dict[str, str] = {}
        structures: dict[str, list[int]] = {}
        blocks: dict[str, list[tuple[str, str]]] = {}
        for language in LANGUAGES:
            path = variant(source, language)
            name = str(path.relative_to(root))
            if path not in all_paths or not path.is_file():
                errors.append(f"{name}: missing {language} translation")
                continue
            if re.search(r"\.(?:en|kk)\.(?:en|kk)\.md$", path.name):
                errors.append(f"{name}: recursive language suffix")
            text = path.read_text(encoding="utf-8-sig")
            texts[language] = text
            if not text.splitlines() or text.splitlines()[0] != switcher(source):
                errors.append(f"{name}: missing or invalid first-line language switcher")
            if PLACEHOLDER.search(prose(text)):
                errors.append(f"{name}: untranslated placeholder")
            structures[language] = [level for level, _ in headings(text)]
            try:
                blocks[language] = fences(text)
            except ValueError as error:
                errors.append(f"{name}: {error}")
            for target in [*LINK.findall(prose(text)), *REFERENCE.findall(prose(text))]:
                target = unquote(target.strip("<>"))
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or target.startswith("/"):
                    continue
                resolved = (path.parent / parsed.path).resolve() if parsed.path else path
                if not resolved.exists():
                    errors.append(f"{name}: broken local link {target}")
                    continue
                if parsed.fragment and resolved.suffix == ".md":
                    if parsed.fragment not in anchors(resolved.read_text(encoding="utf-8-sig")):
                        errors.append(f"{name}: missing anchor {target}")
                # A switcher deliberately links all languages; all other prose links follow
                # the reader's language. Source/code/non-Markdown links remain unchanged.
                if (
                    resolved.suffix == ".md"
                    and source.name != "DOCUMENTATION_MAP.md"
                    and target not in LINK.findall(text.splitlines()[0])
                ):
                    expected = variant(family(resolved), language)
                    if resolved != expected:
                        errors.append(f"{name}: wrong-language link {target}")
        if len(structures) == 3 and len({tuple(item) for item in structures.values()}) != 1:
            errors.append(
                f"{source.relative_to(root)}: heading levels/order differ across languages"
            )
        if len(blocks) == 3:
            for language in ("en", "kk"):
                ru_code = [
                    (lang, body) for lang, body in blocks["ru"] if lang not in ("text", "mermaid")
                ]
                lang_code = [
                    (lang, body)
                    for lang, body in blocks[language]
                    if lang not in ("text", "mermaid")
                ]
                if len(blocks["ru"]) != len(blocks[language]):
                    errors.append(
                        f"{source.relative_to(root)}: code block count differs in {language}"
                    )
                elif ru_code != lang_code:
                    errors.append(f"{source.relative_to(root)}: code blocks differ in {language}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    paths = tracked_markdown(root)
    errors = validate(root, paths)
    if errors:
        print("DOCUMENTATION LOCALIZATION: NOT READY")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    count = len({family(path) for path in paths})
    print(f"DOCUMENTATION LOCALIZATION: READY — {count} families; RU/EN/KK {count} each")
    print(f"Markdown files: {len(paths)}; local links, headings and code fences verified")


if __name__ == "__main__":
    main()
