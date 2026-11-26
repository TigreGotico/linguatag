"""Write the figures of docs/ from the repository's own data.

    python scripts/docs_figures.py            # write docs/figures/*.svg
    python scripts/docs_figures.py --check    # exit 1 when a committed SVG differs from a fresh one
    python scripts/docs_figures.py --measure  # time the calls again and write docs/figures/timings.tsv

Inputs:

- ``lang_distance`` on the tag pairs of ``LADDER``. Output: ``docs/figures/distance-ladder.svg``.
- ``linguatag/data/*.json``: the size and the record count of each file.
  Output: ``docs/figures/data-files.svg``.
- ``docs/figures/timings.tsv``: the median of 7 fresh processes for each call,
  written by ``--measure``. Output: ``docs/figures/call-timings.svg``.
- ``linguatag/data/genealogy.json``: the nodes of each top-level family.
  Output: ``docs/figures/genealogy-families.svg``.
- ``standardize_lang``, ``maximize``, ``default_region``, ``family`` and
  ``catalog_ids`` on the tags of ``LEADERS``. Output: ``docs/leader-languages.md``.

The SVG files hold no timestamp, so two runs write the same bytes. A run of
``--measure`` gives different numbers on each machine, so only ``--measure``
changes ``timings.tsv``.
"""
import json
import re
import math
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "docs" / "figures"
DATA = ROOT / "linguatag" / "data"
TIMINGS = FIGURES / "timings.tsv"

TEXT = "#808080"
GRID = "#80808055"
COLOURS = ["#4C8DD6", "#E0883A", "#A66CC9"]
FONT = 'font-family="sans-serif" font-size="15"'

LADDER = [("pt", "pt-PT"), ("nb", "no"), ("en-AU", "en-GB"), ("en-CA", "en-US"), ("pt", "pt-BR"),
          ("arz", "ar"), ("yue-HK", "zh-HK"), ("zh-Hans", "zh-Hant"), ("gsw", "de"), ("en", "fr"),
          ("de", "gsw"), ("yue", "cmn"), ("und", "en")]


def svg(width: int, height: int, title: str, description: str, body: list) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}" role="img" aria-labelledby="t d">\n<title id="t">{title}</title>\n'
            f'<desc id="d">{description}</desc>\n' + "\n".join(body) + "\n</svg>\n")


def text(x, y, content, anchor="start", fill=TEXT) -> str:
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" {FONT}>{content}</text>'


def distance_ladder() -> str:
    from linguatag import DEFAULT_MAX_LANGUAGE_DISTANCE, lang_distance

    rows = sorted(((lang_distance(a, b), a, b) for a, b in LADDER), key=lambda row: (row[0], row[1]))
    left, unit, top, row_height = 200, 4.2, 52, 26
    height = top + row_height * len(rows) + 30
    limit = left + DEFAULT_MAX_LANGUAGE_DISTANCE * unit
    body = [f'<rect x="16" y="14" width="16" height="16" fill="{COLOURS[0]}"/>',
            text(40, 28, "usable match"),
            f'<rect x="170" y="14" width="16" height="16" fill="{COLOURS[1]}"/>',
            text(194, 28, "not a usable match")]
    for tick in range(0, 101, 20):
        x = left + tick * unit
        body.append(f'<line x1="{x:.0f}" y1="{top - 8}" x2="{x:.0f}" y2="{height - 26}" stroke="{GRID}"/>')
        body.append(text(f"{x:.0f}", height - 6, str(tick), "middle"))
    body.append(f'<line x1="{limit:.0f}" y1="{top - 8}" x2="{limit:.0f}" y2="{height - 26}" stroke="{TEXT}" '
                f'stroke-dasharray="5 4"/>')
    for index, (distance, a, b) in enumerate(rows):
        y = top + index * row_height
        body.append(text(left - 10, y + 17, f"{a} to {b}", "end"))
        colour = COLOURS[0] if distance <= DEFAULT_MAX_LANGUAGE_DISTANCE else COLOURS[1]
        body.append(f'<rect x="{left}" y="{y}" width="{max(distance * unit, 2):.1f}" height="20" fill="{colour}"/>')
        body.append(text(f"{left + distance * unit + 8:.1f}", y + 17, str(distance)))
    summary = ", ".join(f"{a} to {b} {d}" for d, a, b in rows)
    return svg(720, height, "lang_distance of 13 tag pairs",
               f"The distance of 13 tag pairs, with the default limit of {DEFAULT_MAX_LANGUAGE_DISTANCE}: {summary}.",
               body)


def _file_rows() -> list:
    rows = []
    for path in sorted(DATA.glob("*.json")):
        content = json.loads(path.read_text(encoding="utf-8"))
        records = sum(len(value) for value in content.values() if not isinstance(value, str))
        rows.append((path.stat().st_size / 1000, path.name, records))
    return sorted(rows, reverse=True)


def data_files_alt() -> str:
    rows = _file_rows()
    kilobytes, name, records = rows[0]
    share = (rows[0][0] + rows[1][0]) / sum(row[0] for row in rows) * 100
    return (f"Horizontal bars of the size and record count of the {len(rows)} data files. The largest is "
            f"{name}, {kilobytes:.0f} kB and {records:,} records, and {name} and {rows[1][1]} hold "
            f"{share:.0f} percent of the bytes.")


def data_files() -> str:
    rows = _file_rows()
    left, unit, top, row_height = 210, 1.8, 20, 30
    height = top + row_height * len(rows) + 12
    body = []
    for index, (kilobytes, name, records) in enumerate(rows):
        y = top + index * row_height
        body.append(text(left - 10, y + 17, name, "end"))
        body.append(f'<rect x="{left}" y="{y}" width="{kilobytes * unit:.1f}" height="22" fill="{COLOURS[0]}"/>')
        body.append(text(f"{left + kilobytes * unit + 8:.1f}", y + 17, f"{kilobytes:.0f} kB, {records:,} records"))
    summary = ", ".join(f"{name} {kilobytes:.0f} kB and {records:,} records" for kilobytes, name, records in rows)
    return svg(720, height, "The data files of linguatag",
               f"Size and record count of the {len(rows)} data files: {summary}.", body)


def genealogy_families() -> str:
    nodes = json.loads((DATA / "genealogy.json").read_text(encoding="utf-8"))["nodes"]
    counts = {}
    for node in nodes.values():
        family = (node.get("family_path") or ["no family"])[0]
        counts[family] = counts.get(family, 0) + 1
    unclassified = counts.pop("no family", 0)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    shown = ranked[:12]
    rest = ranked[12:]
    rows = [(name, count, COLOURS[0]) for name, count in shown]
    rows.append((f"{len(rest)} other families", sum(count for _, count in rest), COLOURS[1]))
    rows.append(("no family", unclassified, COLOURS[2]))
    left, top, row_height = 230, 20, 30
    unit = (720 - left - 70) / max(count for _, count, _ in rows)
    height = top + row_height * len(rows) + 12
    body = []
    for index, (name, count, colour) in enumerate(rows):
        y = top + index * row_height
        body.append(text(left - 10, y + 17, name, "end"))
        body.append(f'<rect x="{left}" y="{y}" width="{count * unit:.1f}" height="22" fill="{colour}"/>')
        body.append(text(f"{left + count * unit + 8:.1f}", y + 17, f"{count:,}"))
    summary = ", ".join(f"{name} {count:,}" for name, count, _ in rows)
    return svg(720, height, f"{len(nodes):,} genealogy nodes in {len(counts)} families",
               f"Nodes of genealogy.json for each top-level family: {summary}.", body)


def _timing_rows() -> list:
    rows = []
    for line in TIMINGS.read_text(encoding="utf-8").splitlines()[1:]:
        label, milliseconds = line.split("\t")
        rows.append((label, float(milliseconds)))
    return rows


def call_timings_alt() -> str:
    rows = _timing_rows()
    label, ms = max(rows, key=lambda row: row[1])
    fastest, fast_ms = min(rows, key=lambda row: row[1])
    return (f"Horizontal bars on a log scale of the median time of each call in a fresh process. The slowest "
            f"is {label}, {ms:.1f} ms, and the fastest is {fastest}, {fast_ms * 1000:.0f} microseconds.")


def call_timings() -> str:
    rows = _timing_rows()
    low, high = -3, 2          # log10 of the axis ends in ms: 0.001 to 100
    left, width, top, row_height = 250, 400, 20, 30
    height = top + row_height * len(rows) + 36

    def x(ms):
        return left + (math.log10(ms) - low) / (high - low) * width

    body = []
    for tick, label in ((0.001, "1 µs"), (0.01, "10 µs"), (0.1, "0.1 ms"), (1, "1 ms"), (10, "10 ms"), (100, "100 ms")):
        body.append(f'<line x1="{x(tick):.1f}" y1="{top - 8}" x2="{x(tick):.1f}" y2="{height - 30}" stroke="{GRID}"/>')
        body.append(text(f"{x(tick):.1f}", height - 10, label, "middle"))
    for index, (label, ms) in enumerate(rows):
        y = top + index * row_height
        colour = COLOURS[0] if label.startswith("first") or label == "import" else COLOURS[1]
        body.append(text(left - 10, y + 17, label, "end"))
        body.append(f'<rect x="{left}" y="{y}" width="{x(ms) - left:.1f}" height="22" fill="{colour}"/>')
        shown = f"{ms * 1000:.0f} µs" if ms < 0.1 else f"{ms:.1f} ms"
        body.append(text(f"{x(ms) + 8:.1f}", y + 17, shown))
    summary = ", ".join(f"{label} {ms:.3g} ms" for label, ms in rows)
    return svg(720, height, "Time of the first call and of a warm call",
               f"Median milliseconds in a fresh process, on a log scale: {summary}.", body)


FIRST_CALLS = {
    "first standardize_lang": "L.standardize_lang('en_us')",
    "first with_default_region": "L.with_default_region('pt')",
    "first lang_distance": "L.lang_distance('en-AU', 'en-US')",
    "first closest_lang": "L.closest_lang('en-AU', ['fr-FR', 'en-US', 'en-GB'])",
}
TAGS = ["pt-BR", "de-CH", "fr-CA", "es-MX", "zh-HK", "ar-EG", "ja-JP", "ko-KR", "it-IT", "nl-BE"]
PROBE = """
import time
start = time.perf_counter()
import linguatag as L
imported = time.perf_counter() - start
def clock(call):
    start = time.perf_counter()
    call()
    return (time.perf_counter() - start) * 1000
out = {"import": imported * 1000}
%s
print(__import__("json").dumps(out))
"""


def probe(body: str) -> dict:
    code = PROBE % body
    result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True, cwd="/")
    return json.loads(result.stdout)


def measure() -> None:
    runs = 7
    samples: dict = {}
    for _ in range(runs):
        for label, call in FIRST_CALLS.items():
            samples.setdefault(label, []).append(probe(f"out[{label!r}] = clock(lambda: {call})")[label])
        samples.setdefault("import", []).append(probe("pass")["import"])
        warm = probe(f"clock(lambda: L.lang_distance('en-AU', 'en-US'))\n"
                     f"times = [clock(lambda t=t: L.lang_distance(t, 'en-US')) for t in {TAGS!r}]\n"
                     f"out['warm, tag not seen before'] = sorted(times)[len(times) // 2]\n"
                     f"out['warm, tag seen before'] = sorted(clock(lambda: L.lang_distance('pt-BR', 'en-US')) "
                     f"for _ in range(200))[100]")
        for label in ("warm, tag not seen before", "warm, tag seen before"):
            samples.setdefault(label, []).append(warm[label])
    order = ["import", *FIRST_CALLS, "warm, tag not seen before", "warm, tag seen before"]
    lines = ["call\tmedian ms of 7 fresh processes"]
    lines += [f"{label}\t{statistics.median(samples[label]):.4f}" for label in order]
    TIMINGS.write_text("\n".join(lines) + "\n", encoding="utf-8")


LEADERS = ["pt-PT", "pt-BR", "es-CO", "fr-FR", "it-IT", "de-DE", "nl-NL", "da-DK", "kab", "hi-IN", "bn-IN", "mwr"]

LEADER_PAGE = """# Leader languages

<!-- agent-hint
covers: the normalised tag, likely subtags, default region, macrolanguage step, family and data source of each leader tag.
source: scripts/docs_figures.py:leader_languages, linguatag/_standardize.py:standardize_lang, linguatag/_bcp47.py:maximize, linguatag/_regions.py:default_region, linguatag/_lineage.py:family, linguatag/_lineage.py:catalog_ids
generated: yes, by scripts/docs_figures.py
verify: python scripts/docs_figures.py --check
see: likely-subtags.md, genealogy.md, data-and-licence.md
-->

This page shows what linguatag returns for each leader tag. The script `scripts/docs_figures.py` writes the table from the public API. Do not edit the table by hand.

Each column comes from one call:

- **Normalised tag** is the result of `standardize_lang`.
- **Script** and **region** are the subtags that `maximize` adds from CLDR likely subtags.
- **Default region** is the result of `default_region`. The table shows it only for a tag that has no region subtag.
- **Macrolanguage step** is the language that `maximize` returns when it is different from the language of the tag. A dash means that `maximize` keeps the language.
- **Family** is the result of `family`. A dash means that the genealogy data has no family for the tag.
- **Catalog ids** is the result of `catalog_ids`. A dash means that the genealogy data has no node for the tag.
- **Data source** is the `source` field of each data file that gives a fact in the row.

%s

---
[Index](index.md) · [← Reference](reference.md)
"""


def _source(name: str) -> str:
    return f"{name}: {json.loads((DATA / name).read_text(encoding='utf-8'))['source']}"


def leader_languages() -> str:
    from linguatag import catalog_ids, default_region, family, maximize, standardize_lang

    lines = ["| Tag | Normalised tag | Script | Region | Default region | Macrolanguage step | Family | Catalog ids "
             "| Data source |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for tag in LEADERS:
        normal = standardize_lang(tag)
        full = maximize(tag)
        region = "-" if "-" in normal else default_region(tag)
        language = normal.split("-")[0]
        step = full.language if full.language != language else "-"
        ids = ", ".join(f"{key}: {value or 'no entry'}" for key, value in catalog_ids(tag).items()) or "-"
        files = ["aliases.json", "likely_subtags.json"]
        if family(tag) or ids != "-":
            files.append("genealogy.json")
        sources = "<br>".join(_source(name) for name in files)
        lines.append(f"| `{tag}` | `{normal}` | {full.script} | {full.region} | {region} | {step} | "
                     f"{family(tag) or '-'} | {ids} | {sources} |")
    return LEADER_PAGE % "\n".join(lines)


GENERATED_PAGES = {"leader-languages.md": leader_languages}


FIGURE_FILES = {"distance-ladder.svg": distance_ladder, "data-files.svg": data_files,
                "call-timings.svg": call_timings, "genealogy-families.svg": genealogy_families}


#: The page and the alt-text writer of each figure that a page shows with an alt text from the data.
ALT_TEXTS = {"data-files.svg": ("data-and-licence.md", data_files_alt),
             "call-timings.svg": ("performance.md", call_timings_alt)}


def _with_alt(page: str, name: str, alt: str) -> str:
    pattern = re.compile(r"!\[[^\]]*\]\(figures/" + re.escape(name) + r"\)")
    if len(pattern.findall(page)) != 1:
        raise ValueError(f"the page must show figures/{name} once")
    return pattern.sub(lambda _: f"![{alt}](figures/{name})", page)


def main(argv) -> int:
    if argv == ["--measure"]:
        measure()
        return 0
    if argv not in ([], ["--check"]):
        print(__doc__)
        return 2
    status = 0
    for name, make in FIGURE_FILES.items():
        path = FIGURES / name
        fresh = make()
        if argv:
            if not path.exists() or path.read_text(encoding="utf-8") != fresh:
                print(f"{path} is out of date: run python scripts/docs_figures.py")
                status = 1
        else:
            FIGURES.mkdir(exist_ok=True)
            path.write_text(fresh, encoding="utf-8")
    for name, make in GENERATED_PAGES.items():
        path = ROOT / "docs" / name
        fresh = make()
        if argv:
            if not path.exists() or path.read_text(encoding="utf-8") != fresh:
                print(f"{path} is out of date: run python scripts/docs_figures.py")
                status = 1
        else:
            path.write_text(fresh, encoding="utf-8")
    for name, (page_name, alt) in ALT_TEXTS.items():
        page = ROOT / "docs" / page_name
        text_now = page.read_text(encoding="utf-8")
        fresh = _with_alt(text_now, name, alt())
        if argv:
            if fresh != text_now:
                print(f"{page} has an out-of-date alt text for {name}: run python scripts/docs_figures.py")
                status = 1
        else:
            page.write_text(fresh, encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
