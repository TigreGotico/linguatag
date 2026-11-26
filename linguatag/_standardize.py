"""One spelling for every way of writing a language tag."""
from __future__ import annotations

from functools import lru_cache
from typing import Dict

from linguatag._bcp47 import LanguageTagError, _raw_registry, standardize

__all__ = ["standardize_lang"]


@lru_cache(maxsize=None)
def _preferred_values(kind: str) -> Dict[str, str]:
    """The IANA Preferred-Value of each deprecated subtag of ``kind``
    (``language`` or ``region``), lowercase; for ``extlang``, of each
    ``prefix-extlang`` pair."""
    if kind == "extlang":
        return {f"{prefix}-{subtag}".lower(): record["preferred"].lower()
                for subtag, record in _raw_registry("extlang").items()
                for prefix in record.get("prefix", [])}
    return {subtag.lower(): record["preferred"].lower()
            for subtag, record in _raw_registry(kind).items()
            if "deprecated" in record and "preferred" in record}


def _without_extlang(tag: str) -> str:
    """A language and its extlang replaced by the extlang's IANA
    Preferred-Value (RFC 5646 section 4.5): `zh-hak-TW` is `hak-TW`."""
    parts = tag.replace("_", "-").split("-")
    preferred = _preferred_values("extlang").get("-".join(parts[:2]).lower())
    if preferred is None:
        return tag
    return "-".join([preferred, *parts[2:]])


def _without_deprecated_language(tag: str) -> str:
    """A deprecated language subtag replaced by its IANA Preferred-Value
    (RFC 5646 section 4.5): `ajp-JO` is `apc-JO`."""
    language, sep, rest = tag.replace("_", "-").partition("-")
    preferred = _preferred_values("language").get(language.lower())
    return tag if preferred is None else preferred + sep + rest


def _fold(tag: str) -> str:
    """BCP-47 case conventions for a string that is not a well-formed tag:
    language and variants lowercase, script titlecase, region uppercase, and
    every subtag after a singleton (an extension or private use) lowercase."""
    out, after_singleton = [], False
    for index, subtag in enumerate(tag.replace("_", "-").split("-")):
        after_singleton = after_singleton or (index > 0 and len(subtag) == 1)
        if index == 0 or after_singleton or not subtag.isalpha():
            out.append(subtag.lower())
        elif len(subtag) == 4:
            out.append(subtag.title())
        elif len(subtag) == 2:
            out.append(subtag.upper())
        else:
            out.append(subtag.lower())
    return "-".join(out)


@lru_cache(maxsize=4096)
def standardize_lang(tag: str) -> str:
    """Normalize a BCP-47 language tag for comparison.

    The tag is put in canonical form (RFC 5646 section 4.5) from the CLDR 49
    alias rules and the IANA registry that this package carries (see
    :mod:`linguatag._bcp47`): underscores become hyphens, each subtag takes
    its BCP-47 case, a deprecated subtag becomes its Preferred-Value (``iw``
    is ``he``, ``ajp`` is ``apc``, ``my-BU`` is ``my-MM``), a language and its
    extlang become the extlang (``zh-hak`` is ``hak``, ``ar-arz-EG`` is
    ``arz-EG``), an ISO 639-2 code becomes its ISO 639-1 code (``eng`` is
    ``en``) and a script that IANA suppresses for the language goes
    (``en-Latn`` is ``en``). An encompassed language keeps its own code
    (``cmn`` stays ``cmn``). Two spellings of one language (``en_us``,
    ``en-US``) reduce to one string.

    Args:
        tag: a BCP-47-like language tag, possibly underscore-separated or
            mixed-case, as directory names and config values often are.
            White space around the tag is no part of it (RFC 5646
            section 2.1) and is removed.

    Returns:
        The canonical tag, or, for a string that is not a well-formed tag
        (``zh-HK-HiuMaanNeural``), the string with its language and extlang
        replaced as above and each subtag in its BCP-47 case.
    """
    tag = tag.strip()
    if tag.lower() in ("tl", "tgl"):
        # CLDR replaces Tagalog with Filipino, `fil`; the tag stays `tl` here.
        return "tl"
    try:
        return standardize(tag)
    except LanguageTagError:
        return _fold(_without_deprecated_language(_without_extlang(tag)))
