"""The default region of a language tag that names none.

A bare tag defaults to its motherland: the region where the language first
appeared and is still spoken. `en` is `en-GB` and `pt` is `pt-PT`.

CLDR likely-subtags is the base. It picks the most-populous region, which is
the motherland for most languages. `MOTHERLAND` overrides it where the two
differ, and every override cites its source. When several countries share
the area where a language first appeared, the CLDR pick is one of them and
stays.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

__all__ = ["MOTHERLAND", "default_region", "with_default_region"]

#: Language -> region, where the motherland is not the CLDR likely region.
MOTHERLAND: Dict[str, str] = {
    # "English is a West Germanic language of the Indo-European language
    # family that emerged in early medieval England"
    # https://en.wikipedia.org/wiki/English_language
    "en": "GB",
    # Portuguese "evolved from several dialects of Vulgar Latin in the
    # medieval Kingdom of Galicia and the County of Portugal"
    # https://en.wikipedia.org/wiki/Portuguese_language
    "pt": "PT",
    # "Urdu originated geographically in the upper Ganga-Yamuna doab, in and
    # around the Delhi region of India"
    # https://en.wikipedia.org/wiki/Urdu
    "ur": "IN",
}

_DATA = Path(__file__).resolve().parent / "data" / "likely_regions.json"


@lru_cache(maxsize=1)
def _likely_regions() -> Dict[str, str]:
    return json.loads(_DATA.read_text(encoding="utf-8"))["regions"]


def _is_script(subtag: str) -> bool:
    return len(subtag) == 4 and subtag.isalpha()


def _is_region(subtag: str) -> bool:
    return (len(subtag) == 2 and subtag.isalpha()) or (len(subtag) == 3 and subtag.isdigit())


def _split(tag: str) -> Tuple[str, Optional[str], Optional[str]]:
    """`(language, script, region)` of a hyphenated tag."""
    parts = tag.replace("_", "-").split("-")
    language, index = parts[0].lower(), 1
    script = region = None
    if index < len(parts) and _is_script(parts[index]):
        script, index = parts[index].title(), index + 1
    if index < len(parts) and _is_region(parts[index]):
        region = parts[index].upper()
    return language, script, region


def default_region(tag: str) -> Optional[str]:
    """The region `tag` names, or the one it defaults to.

    A tag with a region returns it: `default_region("pt-BR")` is `BR`. A tag
    with none returns its motherland: `en` is `GB`, `zh-Hant` is `TW`. A
    script with no entry of its own takes its language's region. `None` means
    no region applies: the language is unknown, or CLDR places it nowhere in
    particular (`yi`).
    """
    language, script, region = _split(tag)
    if region:
        return region
    regions = _likely_regions()
    if script and f"{language}-{script}" in regions:
        return regions[f"{language}-{script}"]
    return MOTHERLAND.get(language) or regions.get(language)


def with_default_region(tag: str) -> str:
    """`tag` with its default region inserted when it names none.

    `en` becomes `en-GB` and `zh-Hant` becomes `zh-Hant-TW`. A variant or a
    private-use subtag stays after the region: `gl-x-central` becomes
    `gl-ES-x-central`. A tag that already names a region, or that has no
    default region, is returned unchanged.
    """
    language, script, region = _split(tag)
    if region or not language or language == "x":
        return tag
    region = default_region(tag)
    if region is None:
        return tag
    parts = tag.replace("_", "-").split("-")
    at = 2 if script else 1
    return "-".join(parts[:at] + [region] + parts[at:])
