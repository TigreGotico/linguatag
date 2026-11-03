"""Write linguatag/data/likely_regions.json from CLDR likely-subtags.

The table maps every language tag without a region (`en`, `zh-Hant`) to the
region CLDR expects for it. A deprecated code (`ji` is `yi`) has no entry,
because `standardize_lang` replaces it before the lookup. CLDR picks the
most-populous region; the motherland overrides in `linguatag.regions` apply
on top at runtime, so this file stays a plain CLDR snapshot. A tag whose likely region is
unknown (`ZZ`) or the world (`001`) has no entry.

Run it after a langcodes upgrade: `python scripts/build_likely_regions.py`.
"""
import json
from importlib.metadata import version
from pathlib import Path

from langcodes.data_dicts import LIKELY_SUBTAGS

from linguatag.matching import standardize_lang

OUT = Path(__file__).resolve().parent.parent / "linguatag" / "data" / "likely_regions.json"
NO_REGION = ("ZZ", "001")


def _is_script(subtag: str) -> bool:
    return len(subtag) == 4 and subtag.isalpha()


def likely_regions() -> dict:
    regions = {}
    for tag, likely in LIKELY_SUBTAGS.items():
        parts = tag.split("-")
        if parts[0] == "und" or not all(_is_script(p) for p in parts[1:]):
            continue
        if standardize_lang(tag) != tag:
            continue
        region = likely.split("-")[-1]
        if region not in NO_REGION:
            regions[tag] = region
    return dict(sorted(regions.items()))


def main() -> None:
    regions = likely_regions()
    payload = {"source": f"CLDR likelySubtags, langcodes {version('langcodes')}",
               "regions": regions}
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(LIKELY_SUBTAGS)} likely-subtag entries in, {len(regions)} regions out")


if __name__ == "__main__":
    main()
