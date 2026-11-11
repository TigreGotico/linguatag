"""Write linguatag/data/likely_regions.json from CLDR likely-subtags.

The table maps every language tag without a region (`en`, `zh-Hant`) to the
region CLDR expects for it. A deprecated code (`ji` is `yi`) has no entry,
because `standardize_lang` replaces it before the lookup. CLDR picks the
most-populous region; the overrides in `linguatag.regions` apply on top at
runtime, so this file stays a plain CLDR snapshot. A tag whose likely region
is unknown (`ZZ`) has no entry; one placed in the world (`001`, as `yi`)
keeps it.

The base is the CLDR snapshot inside the installed `langcodes`. That
snapshot has no entry for some Arabic varieties, and `langcodes` then
expands them to Latin script in the US. For each Arabic variety
(`is_arabic_variety`) whose likely script in the CLDR release below differs
from the one `langcodes` gives, every likely-subtag entry of that language
comes from the CLDR release: its regions go into `regions`, and its scripts
go into `scripts`, which maps a tag without a script (`mey`, `mey-SN`) to the
script CLDR expects for it.

Run it after a langcodes upgrade or a CLDR release:

    python scripts/build_likely_regions.py [cldr-release]
"""
import json
import sys
import xml.etree.ElementTree as ET
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen

from langcodes import Language
from langcodes.data_dicts import LIKELY_SUBTAGS

from linguatag import is_arabic_variety
from linguatag.standardize import standardize_lang

OUT = Path(__file__).resolve().parent.parent / "linguatag" / "data" / "likely_regions.json"
CLDR_RELEASE = "49"
CLDR_URL = ("https://raw.githubusercontent.com/unicode-org/cldr/release-{}"
            "/common/supplemental/likelySubtags.xml")
UNKNOWN = "ZZ"


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
        if region != UNKNOWN:
            regions[tag] = region
    return regions


def cldr_likely_subtags(release: str) -> dict:
    """Each `from` tag of CLDR likelySubtags.xml, hyphenated, mapped to the
    `(language, script, region)` of its `to` tag."""
    with urlopen(CLDR_URL.format(release)) as response:
        root = ET.fromstring(response.read())
    return {entry.get("from").replace("_", "-"): tuple(entry.get("to").split("_"))
            for entry in root.iter("likelySubtag")}


def arabic_scripts_and_regions(cldr: dict) -> tuple:
    """The CLDR scripts and regions of each Arabic variety whose likely
    script `langcodes` gets wrong."""
    languages = {tag for tag, (_, script, _) in cldr.items()
                 if "-" not in tag and is_arabic_variety(tag)
                 and standardize_lang(tag) == tag
                 and Language.get(tag).maximize().script != script}
    scripts, regions = {}, {}
    for tag, (_, script, region) in cldr.items():
        language, *rest = tag.split("-")
        if language not in languages:
            continue
        if not any(_is_script(subtag) for subtag in rest):
            scripts[tag] = script
        if all(_is_script(subtag) for subtag in rest):
            regions[tag] = region
    return scripts, regions


def main() -> None:
    release = sys.argv[1] if len(sys.argv) > 1 else CLDR_RELEASE
    cldr = cldr_likely_subtags(release)
    scripts, arabic_regions = arabic_scripts_and_regions(cldr)
    regions = {**likely_regions(), **arabic_regions}
    payload = {"source": f"CLDR likelySubtags, langcodes {version('langcodes')}; "
                         f"Arabic varieties from CLDR {release}",
               "regions": dict(sorted(regions.items())),
               "scripts": dict(sorted(scripts.items()))}
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(LIKELY_SUBTAGS)} langcodes and {len(cldr)} CLDR {release} likely-subtag "
          f"entries in, {len(regions)} regions and {len(scripts)} scripts out")


if __name__ == "__main__":
    main()
