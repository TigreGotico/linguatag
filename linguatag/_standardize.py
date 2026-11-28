"""One spelling for every way of writing a language tag."""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Dict

from linguatag._bcp47 import LanguageTagError, _raw_registry, parse, _posix_to_tag, standardize

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
def standardize_lang(tag: str, macro: bool = False) -> str:
    """The canonical form of ``tag`` (RFC 5646 section 4.5), from the CLDR 49
    alias rules and the IANA registry.

    White space around the tag is removed (RFC 5646 section 2.1). A string
    that is not a well-formed tag keeps its shape, with its language and
    extlang replaced and each subtag in its BCP-47 case. An empty subtag
    (``pt-BR-``) makes a string that is no tag, and it matches nothing. The rules and
    examples are in ``docs/parsing.md``.

    With ``macro``, an individual language that CLDR folds into its
    macrolanguage takes the macrolanguage: ``cmn`` is ``zh`` and ``arb`` is
    ``ar``. CLDR folds only the main member of a macrolanguage, so ``yue``
    stays ``yue``. A fold drops the private-use subtags of the member:
    ``cmn-x-beijing`` is ``zh``."""
    tag = _posix_to_tag(tag.strip())
    language, sep, rest = tag.replace("_", "-").partition("-")
    try:
        if language.lower() in ("tl", "tgl"):
            # CLDR replaces Tagalog with Filipino, `fil`; the tag stays `tl` here,
            # and drops `Latn`, its IANA Suppress-Script.
            canonical = parse(standardize("fil" + sep + rest))
            script = None if canonical.script == "Latn" else canonical.script
            return str(replace(canonical, language="tl", script=script))
        folded = standardize(tag, macrolanguage=macro)
        if macro and folded.partition("-")[0] != standardize(tag).partition("-")[0]:
            # A private-use lect of the member names nothing under the
            # macrolanguage: cmn-x-beijing is zh, not zh-x-beijing.
            return str(replace(parse(folded), private=None))
        return folded
    except LanguageTagError:
        return _fold(_without_deprecated_language(_without_extlang(tag)))


@lru_cache(maxsize=4096)
def standard_tag(tag: str) -> str:
    """The plain ISO tag to choose a resource for ``tag``: the canonical
    language, with the CLDR macrolanguage fold, plus its script and region.

    Private-use, variant and extension subtags go, so ``pt-PT-x-porto`` is
    ``pt-PT``, ``en-GB-oed`` is ``en-GB`` and ``cmn-x-beijing`` is ``zh``. A
    tag that names no language, such as ``x-foo`` or a malformed string, is
    ``und``. A voice name such as ``zh-HK-HiuMaanNeural`` keeps its
    well-formed prefix, ``zh-HK``."""
    try:
        parsed = parse(standardize_lang(tag, macro=True), strict=False)
    except LanguageTagError:
        return "und"
    if not parsed.language:
        return "und"
    return "-".join(part for part in (parsed.language, parsed.script, parsed.region) if part)
