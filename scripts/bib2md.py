#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Convert references.bib (Zotero biblatex export) into content/publications.md.

Usage: uv run scripts/bib2md.py [BIB] [OUTPUT]

The `note` field can carry options, e.g. `note = {conf-short={TALN}}`.
Recognized option: `conf-short` (venue acronym shown in parentheses).
A note that is not a list of options is used as the venue (e.g. workshops).
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ME = "Julien Tourille"

LATEX_REPLACEMENTS = {r"\&": "&", r"\%": "%", r"\_": "_", r"\$": "$", "~": " ", "--": "–"}


def parse_bib(text: str) -> list[dict]:
    """Minimal brace-aware parser for Zotero biblatex exports."""
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        entry = {"ENTRYTYPE": m.group(1).lower(), "ID": m.group(2)}
        i = m.end()
        while True:
            fm = re.compile(r"\s*(\w[\w-]*)\s*=\s*").match(text, i)
            if not fm:
                break
            name, i = fm.group(1).lower(), fm.end()
            if text[i] == "{":
                depth, start = 0, i
                while True:
                    if text[i] == "\\":
                        i += 2
                        continue
                    depth += {"{": 1, "}": -1}.get(text[i], 0)
                    i += 1
                    if depth == 0:
                        break
                value = text[start + 1 : i - 1]
            elif text[i] == '"':
                end = text.index('"', i + 1)
                value, i = text[i + 1 : end], end + 1
            else:
                vm = re.compile(r"[^,}\s]+").match(text, i)
                value, i = vm.group(0), vm.end()
            entry[name] = value
            cm = re.compile(r"\s*,?").match(text, i)
            i = cm.end()
        entries.append(entry)
    return entries


def clean(value: str | None) -> str:
    if not value:
        return ""
    for src, dst in LATEX_REPLACEMENTS.items():
        value = value.replace(src, dst)
    value = value.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", value).strip()


def parse_note(note: str | None) -> tuple[dict, str]:
    """Return (options, free_text). `note` is options only if it is a list of key=value."""
    if not note:
        return {}, ""
    parts = [p.strip() for p in re.split(r",(?![^{]*\})", note)]
    if all(re.fullmatch(r"[\w-]+=.+", p) for p in parts):
        return {k: clean(v) for k, v in (p.split("=", 1) for p in parts)}, ""
    return {}, clean(note)


def format_authors(raw: str) -> str:
    names = []
    for author in clean(raw).split(" and "):
        if "," in author:
            last, first = (s.strip() for s in author.split(",", 1))
            author = f"{first} {last}"
        names.append(f"**{author}**" if author == ME else author)
    return ", ".join(names)


def format_entry(e: dict, number: int) -> str:
    options, free_note = parse_note(e.get("note"))
    year = e.get("date", e.get("year", ""))[:4]
    title = clean(e.get("title"))

    venue = clean(e.get("booktitle") or e.get("journaltitle") or e.get("journal")) or free_note
    if venue and options.get("conf-short"):
        venue += f" ({options['conf-short']})"

    title = f"<u>{title}</u>" + ("" if title.endswith(("?", "!", ".")) else ".")
    publisher = clean(e.get("publisher"))
    if venue and publisher:
        source = f"Dans : *{venue}*. {publisher}, {year}."
    elif venue:
        source = f"Dans : *{venue}*, {year}."
    else:
        # Thesis, preprint, ...: institution or DOI instead of a venue
        where = clean(e.get("institution") or e.get("doi") or publisher)
        source = ", ".join(filter(None, [where, year])) + "."

    return f"**[{number}]** {format_authors(e.get('author', ''))}. {title} {source}"


def render(entries: list[dict]) -> str:
    entries = sorted(entries, key=lambda e: e.get("date", e.get("year", "")), reverse=True)
    by_year = defaultdict(list)
    lines = ["# 🎓 Publications", ""]
    for n, e in zip(range(len(entries), 0, -1), entries):
        by_year[e.get("date", e.get("year", ""))[:4]].append(format_entry(e, n))
    for year, items in by_year.items():
        lines += [f"## {year}", ""]
        for item in items:
            lines += [item, ""]
    return "\n".join(lines)


def main() -> None:
    bib = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "references.bib"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "content" / "publications.md"
    entries = parse_bib(bib.read_text(encoding="utf-8"))
    out.write_text(render(entries), encoding="utf-8")
    print(f"Wrote {len(entries)} references to {out}")


if __name__ == "__main__":
    main()
