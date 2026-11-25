"""The default region of a language tag that names none.

A bare tag defaults to its motherland: the region where the language first
appeared and is still spoken. `en` is `en-GB` and `pt` is `pt-PT`.

CLDR 49 likely-subtags is the base (UTS #35 section 4.3, in
:mod:`linguatag.bcp47`). It picks the most-populous region, which is the
motherland for most languages. `OVERRIDES` replaces it where the two
differ, and every override cites its source. When several countries share
the area where a language first appeared, the CLDR pick is one of them and
stays. A language that names a standard of no country defaults to the world
region, `001`, as CLDR spells it.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from linguatag.bcp47 import LanguageTagError, _raw_data, is_region, is_script, maximize, parse
from linguatag.standardize import standardize_lang

__all__ = ["OVERRIDES", "default_region", "likely_script", "with_default_region"]

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


def _split(tag: str) -> Tuple[str, Optional[str], Optional[str], bool]:
    """`(language, script, region, extended)` of a standardized tag.

    `extended` is true when the second subtag has three letters, as in a
    grandfathered tag (`zh-min-nan`): such a tag has no language subtag of
    its own to give a region to.
    """
    language, *rest = tag.split("-")
    script = region = None
    extended = bool(rest) and len(rest[0]) == 3 and rest[0].isalpha()
    if rest and is_script(rest[0]):
        script = rest.pop(0)
    if rest and is_region(rest[0]):
        region = rest[0]
    return language, script, region, extended


def _default_region(tag: str, *, parsed: bool) -> Optional[str]:
    """The region helper; `parsed` says the caller already validated *tag*."""
    if not parsed:
        try:
            parse(tag)
        except LanguageTagError:
            return None
    tag = standardize_lang(tag)
    language, script, region, extended = _split(tag)
    if region:
        return region
    if extended or language == "und":
        return None
    if script:
        likely = _raw_data("likely_subtags.json")["likely"].get(f"{language}-{script}")
        if likely is not None:
            return likely.split("-")[-1]
    maximized = maximize(f"{language}-{script}" if script else language)
    for overridden in (language, maximized and maximized.language):
        if overridden in OVERRIDES:
            override_script, override_region = OVERRIDES[overridden]
            if script in (None, override_script):
                return override_region
    return maximized.region if maximized else None


def default_region(tag: str) -> Optional[str]:
    """The region `tag` names, or the one it defaults to.

    A tag with a region returns it: `default_region("pt-BR")` is `BR`. A tag
    with none returns its default: `en` is `GB`, `zh-Hant` is `TW`, `ar` is
    `001`. A script with no entry of its own takes its language's region,
    unless an override writes the language in another script. The tag is
    standardized first, so `en_GB` and deprecated and three-letter codes
    (`iw`, `eng`) all work, and an encompassed language that CLDR replaces
    with its macrolanguage takes the region of the macrolanguage: `cmn` is
    `CN` and `arb`, Modern Standard Arabic, is `001`. `None` means no region applies: the
    language is unknown or `und`, or the tag is not a language tag.
    """
    return _default_region(tag.strip(), parsed=False)


def _with_default_region(tag: str, *, parsed: bool) -> str:
    """The region-inserting helper; `parsed` says the caller validated *tag*."""
    tag = standardize_lang(tag)
    _, script, region, _ = _split(tag)
    if region:
        return tag
    region = _default_region(tag, parsed=parsed)
    if region is None:
        return tag
    parts = tag.split("-")
    at = 2 if script else 1
    return "-".join(parts[:at] + [region] + parts[at:])


def with_default_region(tag: str) -> str:
    """`tag`, standardized, with its default region inserted.

    `en` becomes `en-GB`, `zh-Hant` becomes `zh-Hant-TW` and `en_us` becomes
    `en-US`. A variant or a private-use subtag stays after the region:
    `gl-x-central` becomes `gl-ES-x-central`. A tag with no default region is
    returned standardized and otherwise unchanged.
    """
    return _with_default_region(tag, parsed=False)


def likely_script(tag: str) -> Optional[str]:
    """The ISO 15924 script that `tag` is written in: the script subtag of the
    tag, or else the script that CLDR 49 likely-subtags gives for the language
    in its default region.

    `zh-TW` is `Hant` and `zh` is `Hans`, as CLDR gives `zh_Hant_TW` and
    `zh_Hans_CN`; `sr-ME` is `Latn`, `pa-PK` is `Arab`, `hyw` is `Armn` and
    `ku-IQ` is `Arab`. A bare tag takes its default region first
    (:func:`with_default_region`), so `yue` is `yue-CN` and `Hans`. None for a
    tag that is not a language tag, for a language that CLDR does not know
    (`zzz`) or `und`, or when no script is known.
    """
    tag = tag.strip()
    try:
        parse(tag)
    except LanguageTagError:
        return None
    tag = _with_default_region(tag, parsed=True)
    _, script, _, extended = _split(tag)
    if script or extended:
        return script
    maximized = maximize(tag)
    return maximized.script if maximized else None


def _with_likely_script(tag: str) -> str:
    """`tag`, standardized and region-expanded, with the script that CLDR 49
    expects for it (:func:`likely_script`).

    `mey-DZ` is `mey-Arab-DZ` and `mey-SN` is `mey-Latn-SN`, as CLDR gives
    `mey_Arab_DZ` and `mey_Latn_SN`; `hyw-AM` is `hyw-Armn-AM` and `lzh-TW` is
    `lzh-Hant-TW`, as CLDR 49 gives `hyw_Armn_AM` and `lzh_Hant_CN`. A tag
    that names a script, or one with no likely script, is returned unchanged.
    """
    _, script, _, extended = _split(tag)
    if script or extended:
        return tag
    likely = likely_script(tag)
    if likely is None:
        return tag
    parts = tag.split("-")
    return "-".join([parts[0], likely, *parts[1:]])
