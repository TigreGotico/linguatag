"""One spelling for every way of writing a language tag."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

from langcodes import standardize_tag

__all__ = ["standardize_lang"]


_EXTLANGS = Path(__file__).resolve().parent / "data" / "extlangs.json"


@lru_cache(maxsize=1)
def _extlang_preferred_values() -> Dict[str, str]:
    return json.loads(_EXTLANGS.read_text(encoding="utf-8"))["preferred"]


def _without_extlang(tag: str) -> str:
    """A language and its extlang replaced by the extlang's IANA
    Preferred-Value (RFC 5646 section 4.5): `zh-hak-TW` is `hak-TW`."""
    parts = tag.replace("_", "-").split("-")
    preferred = _extlang_preferred_values().get("-".join(parts[:2]).lower())
    if preferred is None:
        return tag
    return "-".join([preferred, *parts[2:]])


def _case(index: int, subtag: str, after_singleton: bool) -> str:
    if index == 0 or after_singleton:
        return subtag.lower()
    if len(subtag) == 4 and subtag.isalpha():
        return subtag.title()
    if len(subtag) == 2 and subtag.isalpha():
        return subtag.upper()
    return subtag.lower()


def _fold(tag: str) -> str:
    """BCP-47 case conventions for a tag that ``langcodes`` refuses, such as
    a voice id: language and variants lowercase, script titlecase, region
    uppercase, and every subtag after a singleton (an extension or private
    use) lowercase."""
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
    (``zh-hak`` is ``hak``, ``ar-arz-EG`` is ``arz-EG``). It also replaces
    deprecated forms (``iw`` is ``he``) and drops a redundant script, so two
    spellings of one language (``en_us``, ``en-US``) reduce to one string.

    Args:
        tag: a BCP-47-like language tag, possibly underscore-separated or
            mixed-case, as directory names and config values often are.

    Returns:
        ``langcodes.standardize_tag``'s output, or the case-folded tag when
        ``langcodes`` refuses it.
    """
    if tag.lower() in ("tl", "tgl"):
        # langcodes folds Tagalog into the `fil` macrolanguage; the tag stays
        # `tl` here.
        return "tl"
    tag = _without_extlang(tag)
    try:
        return str(standardize_tag(tag))
    except Exception:
        return _fold(tag)
