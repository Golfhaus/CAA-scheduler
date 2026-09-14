from __future__ import annotations

import re
from pathlib import Path
from typing import Any


SECTION_HEADING = re.compile(
    r"^###\s+(?P<number>\d+(?:\.\d+)?[a-z]?)\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)
LESSON_HEADING = re.compile(r"^(?P<number>\d+[a-z]?)\.\s+", re.MULTILINE)
CHECK_HEADING = re.compile(r"^\*\*Check (?P<letter>[AB])\s+—", re.MULTILINE)
REFERENCE_PATTERN = re.compile(
    r"§\d+(?:\.\d+)?[a-z]?(?:\s+Check\s+[A-Z]|\s+hard-stop addition)?"
    r"|Lesson\s+\d+[a-z]?",
    re.IGNORECASE,
)


def instruction_id(reference: str) -> str:
    """Return the stable catalog ID used by validation-reference links."""
    normalized = reference.strip().lower().replace("§", "section-")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized


def instruction_references(value: str) -> list[str]:
    return REFERENCE_PATTERN.findall(value)


def _repo_path(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _section_entries(markdown: str, source_path: str) -> list[dict[str, Any]]:
    matches = list(SECTION_HEADING.finditer(markdown))
    entries: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        number = match.group("number")
        reference = f"§{number}"
        entries.append(
            {
                "id": instruction_id(reference),
                "kind": "section",
                "reference": reference,
                "title": match.group("title").strip(),
                "text": markdown[match.end() : end].strip(),
                "sourcePath": source_path,
            }
        )
    return entries


def _lesson_entries(section: dict[str, Any]) -> list[dict[str, Any]]:
    text = section["text"]
    matches = list(LESSON_HEADING.finditer(text))
    entries: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        number = match.group("number")
        reference = f"Lesson {number}"
        entries.append(
            {
                "id": instruction_id(reference),
                "kind": "lesson",
                "reference": reference,
                "title": f"Standing Lesson {number}",
                "text": text[match.end() : end].strip(),
                "sourcePath": section["sourcePath"],
                "parentId": section["id"],
            }
        )
    return entries


def _check_entries(section: dict[str, Any]) -> list[dict[str, Any]]:
    text = section["text"]
    matches = list(CHECK_HEADING.finditer(text))
    entries: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if match.group("letter") == "B":
            trailing_heading = re.search(r"^\*\*Updated priority order:", text[match.end() : end], re.MULTILINE)
            if trailing_heading:
                end = match.end() + trailing_heading.start()
        letter = match.group("letter")
        reference = f"§2.6 Check {letter}"
        entries.append(
            {
                "id": instruction_id(reference),
                "kind": "check",
                "reference": reference,
                "title": f"{section['title']} — Check {letter}",
                "text": text[match.start() : end].strip(),
                "sourcePath": section["sourcePath"],
                "parentId": section["id"],
            }
        )
    return entries


def build_instruction_catalog(
    primary_path: Path,
    addition_paths: list[Path],
    repo_root: Path,
    version: str,
) -> dict[str, Any]:
    """Build browser-facing reference data from editable Markdown sources."""
    primary_text = primary_path.read_text(encoding="utf-8")
    primary_source = _repo_path(primary_path, repo_root)
    sections = _section_entries(primary_text, primary_source)
    entries = list(sections)

    lessons_section = next((entry for entry in sections if entry["id"] == "section-1-12"), None)
    if lessons_section:
        entries.extend(_lesson_entries(lessons_section))

    spacing_section = next((entry for entry in sections if entry["id"] == "section-2-6"), None)
    if spacing_section:
        entries.extend(_check_entries(spacing_section))

    for addition_path in addition_paths:
        addition_text = addition_path.read_text(encoding="utf-8")
        reference = "§1.7 hard-stop addition"
        entries.append(
            {
                "id": instruction_id(reference),
                "kind": "addition",
                "reference": reference,
                "title": "Turn-on-stand hard stop",
                "text": addition_text.strip(),
                "sourcePath": _repo_path(addition_path, repo_root),
                "parentId": "section-1-7",
            }
        )

    entry_ids = [entry["id"] for entry in entries]
    if len(entry_ids) != len(set(entry_ids)):
        raise ValueError("Instruction catalog contains duplicate reference IDs")

    return {
        "schemaVersion": "1.0.0",
        "version": version,
        "sourcePath": primary_source,
        "entries": entries,
    }
