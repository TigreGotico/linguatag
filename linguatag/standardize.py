"""One spelling for every way of writing a language tag."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

__all__ = ["standardize_lang"]


_DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def _preferred_values(name: str) -> Dict[str, str]:
    return json.loads((_DATA / name).read_text(encoding="utf-8"))["preferred"]


def _without_extlang(tag: str) -> str:
    """A language and its extlang replaced by the extlang's IANA
    Preferred-Value (RFC 5646 section 4.5): `zh-hak-TW` is `hak-TW`."""
    parts = tag.replace("_", "-").split("-")
    preferred = _preferred_values("extlangs.json").get("-".join(parts[:2]).lower())
    if preferred is None:
        return tag
    return "-".join([preferred, *parts[2:]])


def _without_deprecated_language(tag: str) -> str:
    """A deprecated language subtag replaced by its IANA Preferred-Value
    (RFC 5646 section 4.5): `ajp-JO` is `apc-JO`. The registry copy in
    ``langcodes`` predates some deprecations, so the table comes first."""
    language, sep, rest = tag.replace("_", "-").partition("-")
    preferred = _preferred_values("deprecated_languages.json").get(language.lower())
    return tag if preferred is None else preferred + sep + rest


def _case(index: int, subtag: str, after_singleton: bool) -> str:
    if index == 0 or after_singleton:
        return subtag.lower()
    if len(subtag) == 4 and subtag.isalpha():
        return subtag.title()
    if len(subtag) == 2 and subtag.isalpha():
        return subtag.upper()
    return subtag.lower()


def _fold(tag: str) -> str:
    """BCP-47 case conventions without ``langcodes``: language and variants
    lowercase, script titlecase, region uppercase, and every subtag after a
    singleton (an extension or private use) lowercase."""
    out, after_singleton = [], False
    for index, subtag in enumerate(tag.replace("_", "-").split("-")):
        after_singleton = after_singleton or (index > 0 and len(subtag) == 1)
        out.append(_case(index, subtag, after_singleton))
    return "-".join(out)


@lru_cache(maxsize=4096)
def standardize_lang(tag: str) -> str:
    """Normalize a BCP-47 language tag for comparison.

    Folds underscores to hyphens and applies the BCP-47 case conventions. A
    language and its extlang become the extlang's IANA Preferred-Value
    (``zh-hak`` is ``hak``, ``ar-arz-EG`` is ``arz-EG``), and a deprecated
    language subtag becomes its Preferred-Value (``ajp`` is ``apc``). With ``langcodes``
    it also replaces deprecated forms (``iw`` is ``he``) and drops a redundant
    script, so two spellings of one language (``en_us``, ``en-US``) reduce to
    one string.

    Args:
        tag: a BCP-47-like language tag, possibly underscore-separated or
            mixed-case, as directory names and config values often are.

    Returns:
        ``langcodes.standardize_tag``'s output when ``langcodes`` is
        installed and accepts the tag; otherwise the case-folded tag.
    """
    if tag.lower() in ("tl", "tgl"):
        # langcodes folds Tagalog into the `fil` macrolanguage; the tag stays
        # `tl` here.
        return "tl"
    tag = _without_deprecated_language(_without_extlang(tag))
    try:
        from langcodes import standardize_tag
        return str(standardize_tag(tag))
    except Exception:
        return _fold(tag)
