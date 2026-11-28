"""Check that a README or docs page says what the code does.

    python scripts/check_doc_page.py docs/matching.md

Run it from the repository root. It checks:

- Each python block of the page runs in its own ``python -I`` process and
  exits 0. Its output lines are the ``# output`` comments of its ``print(``
  lines, in order.
- Each relative link of the page reaches a file, and each anchor a heading of
  that file.
- README.md: the ``langcodes`` extra of pyproject.toml is empty.
- docs/index.md: the table links each page of docs/, in the order that the
  page footers give. The links of README.md, AGENTS.md and each docs page are
  checked too.
- docs/data-and-licence.md: the page holds the ``name | source`` line of each
  file in linguatag/data.

It exits 1 at the first mismatch, and 0 otherwise.
"""
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fail(message: str):
    print(message)
    sys.exit(1)


def anchors(file: Path) -> set:
    """The GitHub anchors of the headings of *file*."""
    found, seen = set(), {}
    text = re.sub(r"```.*?```", "", file.read_text(encoding="utf-8"), flags=re.S)
    for heading in re.findall(r"^#{1,6}\s+(.*?)\s*$", text, re.M):
        heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", re.sub(r"`|\*", "", heading)).strip().lower()
        slug = "".join(c for c in heading if c.isalnum() or c in "-_ ").replace(" ", "-")
        found.add(f"{slug}-{seen[slug]}" if slug in seen else slug)
        seen[slug] = seen.get(slug, 0) + 1
    return found


def check_links(file: Path) -> int:
    body = re.sub(r"<!--.*?-->|```.*?```|`[^`\n]*`", "", file.read_text(encoding="utf-8"), flags=re.S)
    links = re.findall(r"\]\(([^)\s]+)\)", body)
    for target in links:
        if re.match(r"[a-z]+:", target):
            continue
        path, _, anchor = target.partition("#")
        dest = (file.parent / path).resolve() if path else file.resolve()
        if not dest.exists():
            fail(f"{file}: the link {target} reaches no file")
        if anchor and dest.suffix == ".md" and anchor not in anchors(dest):
            fail(f"{file}: the link {target} names no heading of {dest.name}")
    return len(links)


page = Path(sys.argv[1])
text = page.read_text(encoding="utf-8")
checked = 0

for block in re.findall(r"```python\n(.*?)```", text, re.S):
    expected = [line.split("# ", 1)[1].strip() for line in block.splitlines()
                if line.strip().startswith("print(") and "# " in line]
    result = subprocess.run([sys.executable, "-I", "-c", block], capture_output=True, text=True, cwd=ROOT)
    if result.returncode:
        fail(f"{page}: a python block exits {result.returncode}:\n{result.stderr}")
    output = [line.strip() for line in result.stdout.splitlines()]
    for wanted, got in zip(expected, output):
        if wanted != got:
            fail(f"{page}: a python block prints {got!r}, the page says {wanted!r}")
    if len(expected) != len(output):
        fail(f"{page}: a python block prints {len(output)} lines, the page shows {len(expected)}")
    checked += len(expected)

is_index = page.resolve() == ROOT / "docs" / "index.md"
for file in [ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").glob("*.md"))] if is_index else [page]:
    checked += check_links(file)

if page.resolve() == ROOT / "README.md":
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]
    if extras.get("langcodes", None) != []:
        fail(f"{page}: the langcodes extra of pyproject.toml is {extras.get('langcodes')!r}, the page says it is empty")
    checked += 1

if is_index:
    docs = ROOT / "docs"
    order = re.findall(r"^\| \[[^]]+\]\(([\w-]+\.md)\)", text, re.M)
    pages = sorted(p.name for p in docs.glob("*.md") if p.name != "index.md")
    if sorted(order) != pages:
        fail(f"{page}: the table links {sorted(order)}, docs/ holds {pages}")
    for before, after in zip(order, order[1:]):
        if not re.search(rf"→\]\({re.escape(after)}\)", (docs / before).read_text(encoding="utf-8")) or not re.search(
                rf"\[← [^]]*\]\({re.escape(before)}\)", (docs / after).read_text(encoding="utf-8")):
            fail(f"{page}: the footers of {before} and {after} do not link each other")
    checked += len(order)

if page.resolve() == ROOT / "docs" / "data-and-licence.md":
    for data in sorted((ROOT / "linguatag" / "data").glob("*.json")):
        line = f"{data.name} | {json.loads(data.read_text(encoding='utf-8'))['source']}"
        if line not in text:
            fail(f"{page}: the page does not hold {line!r}")
        checked += 1

print(f"OK {page}: {checked} checks")
