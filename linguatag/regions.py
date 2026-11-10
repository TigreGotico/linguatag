"""The default region of a language tag that names none.

A bare tag defaults to its motherland: the region where the language first
appeared and is still spoken. `en` is `en-GB` and `pt` is `pt-PT`.

CLDR likely-subtags is the base. It picks the most-populous region, which is
the motherland for most languages. `OVERRIDES` replaces it where the two
differ, and every override cites its source. When several countries share
the area where a language first appeared, the CLDR pick is one of them and
stays. A language that names a standard of no country defaults to the world
region, `001`, as CLDR spells it.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Tuple

from linguatag.standardize import standardize_lang

__all__ = ["OVERRIDES", "default_region", "with_default_region"]

#: Language -> (script, region) of its default, where the region is not the
#: CLDR likely region. The script is the one that region writes the language
#: in; a tag that names another script keeps the CLDR region (`yue-Hant` is
#: HK, `en-Dsrt` is US).
OVERRIDES: Dict[str, Tuple[str, str]] = {
    # A bare `ar` is Modern Standard Arabic, the standard of no single
    # country. CLDR spells it `ar-001`, "Arabic (world)"; its likely region
    # for `ar` is EG.
    "ar": ("Arab", "001"),
    # "English is a West Germanic language of the Indo-European language
    # family that emerged in early medieval England"
    # https://en.wikipedia.org/wiki/English_language
    "en": ("Latn", "GB"),
    # Portuguese "evolved from several dialects of Vulgar Latin in the
    # medieval Kingdom of Galicia and the County of Portugal"
    # https://en.wikipedia.org/wiki/Portuguese_language
    "pt": ("Latn", "PT"),
    # "Urdu originated geographically in the upper Ganga-Yamuna doab, in and
    # around the Delhi region of India"
    # https://en.wikipedia.org/wiki/Urdu
    "ur": ("Arab", "IN"),
    # Cantonese "originated in the city of Guangzhou (formerly romanized as
    # Canton) and its surrounding Pearl River Delta."
    # https://en.wikipedia.org/wiki/Cantonese
    "yue": ("Hans", "CN"),
}

_DATA = Path(__file__).resolve().parent / "data" / "likely_regions.json"


@lru_cache(maxsize=1)
def _likely_regions() -> Dict[str, str]:
    return json.loads(_DATA.read_text(encoding="utf-8"))["regions"]


def _is_script(subtag: str) -> bool:
    return len(subtag) == 4 and subtag.isalpha()


def _is_region(subtag: str) -> bool:
    return (len(subtag) == 2 and subtag.isalpha()) or (len(subtag) == 3 and subtag.isdigit())


def _split(tag: str) -> Tuple[str, Optional[str], Optional[str], bool]:
    """`(language, script, region, extended)` of a standardized tag.

    `extended` is true when the second subtag has three letters, as in a
    grandfathered tag (`zh-min-nan`): such a tag has no language subtag of
    its own to give a region to.
    """
    parts = tag.split("-")
    language, index = parts[0], 1
    script = region = None
    extended = index < len(parts) and len(parts[index]) == 3 and parts[index].isalpha()
    if index < len(parts) and _is_script(parts[index]):
        script, index = parts[index], index + 1
    if index < len(parts) and _is_region(parts[index]):
        region = parts[index]
    return language, script, region, extended


def default_region(tag: str) -> Optional[str]:
    """The region `tag` names, or the one it defaults to.

    A tag with a region returns it: `default_region("pt-BR")` is `BR`. A tag
    with none returns its default: `en` is `GB`, `zh-Hant` is `TW`, `ar` is
    `001`. A script with no entry of its own takes its language's region,
    unless an override writes the language in another script. The
    tag is standardized first, so `en_GB`, deprecated codes and three-letter
    codes (`iw`, `eng`) all work. `None` means no region applies: the
    language is unknown, or the tag is a grandfathered form that `langcodes`
    does not replace.
    """
    language, script, region, extended = _split(standardize_lang(tag))
    if region:
        return region
    if extended:
        return None
    regions = _likely_regions()
    if script and f"{language}-{script}" in regions:
        return regions[f"{language}-{script}"]
    if language in OVERRIDES:
        override_script, override_region = OVERRIDES[language]
        if script in (None, override_script):
            return override_region
    return regions.get(language)


def with_default_region(tag: str) -> str:
    """`tag`, standardized, with its default region inserted.

    `en` becomes `en-GB`, `zh-Hant` becomes `zh-Hant-TW` and `en_us` becomes
    `en-US`. A variant or a private-use subtag stays after the region:
    `gl-x-central` becomes `gl-ES-x-central`. A tag with no default region is
    returned standardized and otherwise unchanged.
    """
    tag = standardize_lang(tag)
    _, script, region, _ = _split(tag)
    if region:
        return tag
    region = default_region(tag)
    if region is None:
        return tag
    parts = tag.split("-")
    at = 2 if script else 1
    return "-".join(parts[:at] + [region] + parts[at:])
