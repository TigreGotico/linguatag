"""One spelling for every way of writing a language tag."""
from __future__ import annotations

from functools import lru_cache

__all__ = ["standardize_lang"]


def _case(index: int, subtag: str, after_x: bool) -> str:
    if index == 0 or after_x:
        return subtag.lower()
    if len(subtag) == 4 and subtag.isalpha():
        return subtag.title()
    if len(subtag) == 2 and subtag.isalpha():
        return subtag.upper()
    return subtag.lower()


def _fold(tag: str) -> str:
    """BCP-47 case conventions without ``langcodes``: language and variants
    lowercase, script titlecase, region uppercase, private use lowercase."""
    out, after_x = [], False
    for index, subtag in enumerate(tag.replace("_", "-").split("-")):
        out.append(_case(index, subtag, after_x))
        after_x = after_x or subtag.lower() == "x"
    return "-".join(out)


@lru_cache(maxsize=4096)
def standardize_lang(tag: str) -> str:
    """Normalize a BCP-47 language tag for comparison.

    Folds underscores to hyphens and applies the BCP-47 case conventions. With
    ``langcodes`` it also replaces deprecated and extended forms (``iw`` is
    ``he``, ``zh-yue`` is ``yue``) and drops a redundant script, so two
    spellings of one language (``en_us``, ``en-US``) reduce to one string.

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
    try:
        from langcodes import standardize_tag
        return str(standardize_tag(tag))
    except Exception:
        return _fold(tag)
