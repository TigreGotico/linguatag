"""The CLDR language matching distance between two language tags.

UTS #35 (revision 79, CLDR 49), section 4.4 "Language Matching", gives the
matching distance MD between two locales:

    To find the matching distance (MD) between any two locales, perform the
    following steps:
    - Maximize each locale using Likely Subtags.
      - und is a special case: see below.
    - Set the match-distance MD to 0
    - For each subtag in {language, script, region}
      - If respective subtags in each language tag are identical, remove the
        subtag from each (logically) and continue.
      - Traverse the languageMatching data until a match is found.
        - * matches any field.
        - A matchVariable is matched as in Language Matching Variables.
        - If the oneway flag is false, then the match can go both ways; if
          it's true, then it only matches one direction.
      - Add the distance attribute value to MD.
      - Remove the subtag from each (logically)
    - Return MD

The rules and the match variables are the ``written-new`` data of CLDR 49,
in their order, and the regions of a macroregion come from CLDR 49 territory
containment. Both are read from ``linguatag/data`` (written by
``scripts/extract_cldr.py``), never from an installed package.

``und``: "if the desired base language is und, the language matcher should
not apply likely subtags to it." Section 4.3 lets an implementation exclude
``und`` from Add Likely Subtags, and :func:`linguatag.bcp47.maximize` does,
so a supported ``und`` is not maximized either. A language with no likely
subtags (``zzz``) keeps the subtags it has. A missing script is ``Zzzz`` and
a missing region ``ZZ``, the CLDR codes for an unknown script and region.

Match variables: "When the set is interpreted, then macrolanguages are
(logically) transformed into a list of their contents, so “053+GB” →
“AU+GB+NF+NZ”. This is done recursively", and "we use 019 for all of the
Americas in the variables above, because en-US should be in the same cluster
as es-419 and its contents." A macroregion in a tag (``419``, ``001``) is in
each cluster that holds one of the regions it contains. Its region distance
is the largest distance over those clusters, as ICU's ``LocaleDistance``
measures it, so ``ar-001`` is 5 from ``ar-MA``: ``001`` holds regions inside
and outside ``$maghreb``.

Paradigm locales: "These are locales that are preferred within a cluster.
So when matching desired=[en-SA] against [en-GU en en-IN en-GB], the value
en-GB is returned." They do not change the distance. :func:`is_paradigm`
tells :func:`linguatag.closest_lang` which of two candidates at the same
distance to prefer.

Ported from langcodes 3.5.1 (``language_distance.py`` and
``Language.distance``), Copyright (C) 2021 Robyn Speer, MIT License; see
NOTICE. Every rule, the region rules included, comes from the CLDR 49 data.
The rules for ``sh`` match no tag, because canonical ``sh`` is ``sr-Latn``.
"""
from __future__ import annotations

import re
from functools import lru_cache, reduce
from typing import Dict, FrozenSet, List, Tuple

from linguatag.bcp47 import LanguageTagError, _canonical, load_data, maximize, parse

__all__ = ["is_paradigm", "tag_distance"]

_Triple = Tuple[str, str, str]
_Field = Tuple[bool, FrozenSet[str]]

_MATCHING = load_data("language_matching.json")
_CONTAINS = load_data("territory_containment.json")["contains"]
_UNKNOWN = ("und", "Zzzz", "ZZ")


@lru_cache(maxsize=None)
def _contents(region: str) -> FrozenSet[str]:
    """The leaf regions inside ``region``, or ``region`` itself."""
    if region not in _CONTAINS:
        return frozenset({region})
    return frozenset().union(*map(_contents, _CONTAINS[region]))


# "it allows for + for union and - for set difference, but no precedence"
_VARIABLES = {
    name: reduce(lambda regions, term: (regions - _contents(term[1]) if term[0] == "-"
                                        else regions | _contents(term[1])),
                 re.findall(r"([+-]?)([^+-]+)", value), frozenset())
    for name, value in _MATCHING["variables"].items()}


def _field(pattern: str) -> _Field:
    """``(negated, values)``: a subtag matches when ``(subtag in values) != negated``."""
    if pattern == "*":
        return (True, frozenset())
    if pattern.startswith("$!"):
        return (True, _VARIABLES["$" + pattern[2:]])
    return (False, _VARIABLES.get(pattern, frozenset({pattern})))


# The languageMatch rules by number of fields, each list in data order.
_RULES: Dict[int, List[Tuple[Tuple[_Field, ...], Tuple[_Field, ...], int, bool]]] = {
    fields: [(tuple(map(_field, desired.split("-"))), tuple(map(_field, supported.split("-"))),
              distance, oneway)
             for desired, supported, distance, oneway in _MATCHING["rules"]
             if desired.count("-") + 1 == fields]
    for fields in (1, 2, 3)}

# Regions a rule names as they are, such as ``GB`` in ``en_*_GB``.
_NAMED_REGIONS = frozenset(
    field for rule in _MATCHING["rules"] for side in rule[:2]
    for field in side.split("-")[2:] if field != "*" and not field.startswith("$"))


def _all_match(fields: Tuple[_Field, ...], subtags: Tuple[str, ...]) -> bool:
    return all((subtag in values) != negated for (negated, values), subtag in zip(fields, subtags))


def _rule_distance(desired: Tuple[str, ...], supported: Tuple[str, ...]) -> int:
    """The distance of the first rule that matches, in data order."""
    for want, have, distance, oneway in _RULES[len(desired)]:
        if _all_match(want, desired) and _all_match(have, supported):
            return distance
        if not oneway and _all_match(want, supported) and _all_match(have, desired):
            return distance
    raise LookupError(f"no languageMatch rule for {desired} and {supported}")


@lru_cache(maxsize=None)
def _clusters(region: str) -> Tuple[str, ...]:
    """One leaf of ``region`` for each set of match variables and named
    regions that its leaves fall in."""
    representatives: Dict[tuple, str] = {}
    for part in sorted(_contents(region)):
        key = (frozenset(name for name, members in _VARIABLES.items() if part in members),
               part if part in _NAMED_REGIONS else None)
        representatives.setdefault(key, part)
    return tuple(representatives.values())


@lru_cache(maxsize=8192)
def _triple(tag: str) -> _Triple:
    """``(language, script, region)`` of ``tag`` after Add Likely Subtags,
    with ``und`` and an unknown language as they are."""
    maximized = maximize(tag)
    if maximized is None:
        try:
            maximized = _canonical(parse(tag), macrolanguage=True)
        except LanguageTagError:
            return _UNKNOWN
    if maximized.whole:
        return _UNKNOWN
    return (maximized.language or "und", maximized.script or "Zzzz", maximized.region or "ZZ")


@lru_cache(maxsize=8192)
def _triple_distance(desired: _Triple, supported: _Triple) -> int:
    (language, script, region), (other_language, other_script, other_region) = desired, supported
    distance = 0
    if language != other_language:
        distance += _rule_distance((language,), (other_language,))
    if script != other_script:
        distance += _rule_distance((language, script), (other_language, other_script))
    if region != other_region:
        distance += max(_rule_distance((language, script, part), (other_language, other_script, other))
                        for part in _clusters(region) for other in _clusters(other_region))
    return distance


def tag_distance(desired: str, supported: str) -> int:
    """The UTS #35 matching distance from ``desired`` to ``supported``.

    It is not symmetric: ``gsw`` is 8 from ``de`` and ``de`` is 84 from ``gsw``.
    """
    return _triple_distance(_triple(desired), _triple(supported))


@lru_cache(maxsize=1)
def _paradigms() -> FrozenSet[_Triple]:
    return frozenset(map(_triple, _MATCHING["paradigm_locales"]))


def is_paradigm(tag: str) -> bool:
    """Whether ``tag`` maximizes to a CLDR 49 paradigm locale, such as ``en-GB`` or ``es-419``."""
    return _triple(tag) in _paradigms()
