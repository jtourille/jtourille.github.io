"""Turn every mention of a person listed in links.md into a Markdown link in content/about.md.

Mentions that are already inside a Markdown link are left untouched, so the script
can be run repeatedly.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINKS_FILE = ROOT / "links.md"
TARGET_FILE = ROOT / "content" / "about.md"

# Existing Markdown links: [text](url)
EXISTING_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")


def load_links(path: Path) -> dict[str, str]:
    links = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ": " not in line:
            continue
        name, url = line.split(": ", 1)
        links[name.strip()] = url.strip()
    return links


def link_people(text: str, links: dict[str, str]) -> str:
    # Longest names first so that e.g. "Jean Paul Martin" wins over "Jean Paul"
    names = sorted(links, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")

    def replace(segment: str) -> str:
        return pattern.sub(lambda m: f"[{m.group(1)}]({links[m.group(1)]})", segment)

    # Only substitute in the text between existing links
    result, last = [], 0
    for m in EXISTING_LINK.finditer(text):
        result.append(replace(text[last : m.start()]))
        result.append(m.group(0))
        last = m.end()
    result.append(replace(text[last:]))
    return "".join(result)


def main() -> None:
    links = load_links(LINKS_FILE)
    text = TARGET_FILE.read_text(encoding="utf-8")
    new_text = link_people(text, links)
    if new_text == text:
        print("No changes: all mentions are already linked.")
        return
    TARGET_FILE.write_text(new_text, encoding="utf-8")
    print(f"Updated {TARGET_FILE}")


if __name__ == "__main__":
    main()
