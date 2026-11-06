"""One spelling for every way of writing a language tag."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langcodes import Language, LanguageTagError, standardize_tag

__all__ = ["MAX_TAG_LENGTH", "standardize_lang"]

# Tags come from directory names and config values, and a file name stops at 255
# bytes. A longer string is no tag, and parsing one costs seconds.
MAX_TAG_LENGTH = 255

# The IANA Language Subtag Registry gives `tl` (Tagalog) no Preferred-Value, so
# RFC 5646 section 4.5 leaves it canonical, and `tgl` is its ISO 639-2 spelling.
# CLDR aliases both to `fil`, and langcodes follows CLDR.
_TAGALOG = ("tl", "tgl")


@lru_cache(maxsize=4096)
def parseable_prefix(tag: str) -> str:
    """The longest leading part of ``tag`` that ``langcodes`` parses.

    A voice id such as ``zh-HK-HiuMaanNeural`` is not a language tag, but its
    ``zh-HK`` is. A tag with no parseable prefix gives ``""``.
    """
    parts = tag.split("-")
    for end in range(len(parts), 0, -1):
        candidate = "-".join(parts[:end])
        try:
            Language.get(candidate)
        except LanguageTagError:
            continue
        return candidate
    return ""


def _standard_form(tag: str) -> str:
    standard = standardize_tag(tag)
    if tag.split("-")[0].lower() in _TAGALOG:
        return "tl" + standard.removeprefix("fil")
    return standard


@lru_cache(maxsize=4096)
def _stable_form(tag: str) -> str:
    tag = tag.replace("_", "-")
    # BCP 47 subtags are 1 to 8 characters long: a leading, trailing or doubled
    # separator makes a tag that names no language. The standard form can parse
    # differently from the tag: `i-klingon-ex` gives `tlh-ex`, where `ex` is a
    # region, and it can pass the length limit: `sh` is `sr-Latn`.
    while len(tag) <= MAX_TAG_LENGTH and "" not in tag.split("-"):
        prefix = parseable_prefix(tag)
        standard = (_standard_form(prefix) if prefix else "") + tag[len(prefix):].lower()
        if standard == tag:
            return standard
        tag = standard
    return ""


def standardize_lang(tag: Optional[str]) -> str:
    """Normalize a BCP-47 language tag for comparison.

    Folds underscores to hyphens, applies the BCP-47 case conventions, replaces
    deprecated and extended forms (``iw`` is ``he``, ``zh-yue`` is ``yue``) and
    drops a redundant script, so two spellings of one language (``en_us``,
    ``en-US``) reduce to one string. ``tl`` and ``tgl`` are ``tl``, with any
    region: ``tl-PH``, not the ``fil-PH`` of ``langcodes``.

    A tag that ``langcodes`` cannot parse, such as a voice id or a private-use
    subtag over 8 characters, keeps its unparseable part in lowercase after
    its standardized prefix: ``zh-HK-hiumaanneural``. A second call changes
    nothing: ``i-klingon-ex`` is ``tlh-EX``, because ``ex`` is a region of ``tlh``.

    Args:
        tag: a BCP-47-like language tag, possibly underscore-separated or
            mixed-case, as directory names and config values often are.

    Returns:
        The standard form, or ``""`` when ``tag`` names no language: it is
        ``None``, empty, has an empty subtag (``en_``, ``-en``, ``en--US``), or
        it or its standard form is longer than :data:`MAX_TAG_LENGTH`
        characters. Such a tag is refused before any parsing.
    """
    if tag is None or len(tag) > MAX_TAG_LENGTH:
        return ""
    return _stable_form(tag)
