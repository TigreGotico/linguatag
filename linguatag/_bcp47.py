"""Parse, canonicalize and maximize BCP 47 language tags.

Ported from langcodes 3.5.1 (``tag_parser.py``, ``Language.get``,
``Language.maximize`` and ``standardize_tag``), Copyright (C) 2021 Robyn
Speer, MIT License; see NOTICE. The data is the CLDR 49 release and the IANA
Language Subtag Registry, read from ``linguatag/data`` (written by
``scripts/extract_cldr.py``), never from an installed package.

Parsing follows the RFC 5646 section 2.1 ABNF::

    langtag = language ["-" script] ["-" region] *("-" variant)
              *("-" extension) ["-" privateuse]
    language = 2*3ALPHA ["-" extlang] / 4ALPHA / 5*8ALPHA

Canonicalization follows RFC 5646 section 4.5, "applying each of the
following steps in order": "1. Extension sequences are ordered into
case-insensitive ASCII order by singleton subtag. 2. Redundant or
grandfathered tags are replaced by their 'Preferred-Value', if there is one.
3. Subtags are replaced by their 'Preferred-Value', if there is one. For
extlangs, the original primary language subtag is also replaced if there is
a primary language subtag in the 'Preferred-Value'." The replacements are
the IANA Preferred-Values and the CLDR alias rules, applied as UTS #35 Annex
C, "LocaleId Canonicalization", applies them; an IANA value wins over a CLDR
rule for the same subtag. The CLDR rules add the ISO 639-2 codes (``eng`` is
``en``), the legacy forms (``sh`` is ``sr-Latn``) and the sign-language tags
(``sgn-US`` is ``ase``). A tag with an extlang whose IANA ``Prefix`` is
another language (``en-hak``) is left as written.

UTS #35 Annex C also replaces an encompassed language with its macrolanguage
(``cmn`` is ``zh``, ``arb`` is ``ar``). :func:`standardize` does not: a tag
keeps the language it names. :func:`maximize` does, as UTS #35 section 4.3
requires. CLDR composes two ISO 639-2 aliases with such a replacement
(``twi`` to ``ak`` through ``tw``, ``bih`` to ``bho`` through ``bh``); without
the macrolanguage step ``twi`` is ``tw`` and ``bih`` stays.

The script that IANA names in a language's ``Suppress-Script`` field is
dropped, as RFC 5646 section 3.1.9 says of it: "The subtag for such a script
therefore adds no distinguishing information to a language tag and thus
SHOULD NOT be used for most documents in that language." Variants are put in
alphabetical order, as UTS #35 section 5 "Canonicalizing Syntax" does.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

__all__ = ["LanguageTag", "LanguageTagError", "is_region", "is_script", "language_scope", "load_data", "maximize",
           "parse", "registry", "standardize"]

_DATA = Path(__file__).resolve().parent / "data"


class LanguageTagError(ValueError):
    """A string that is not a well-formed BCP 47 language tag."""


@dataclass(frozen=True)
class LanguageTag:
    """The subtags of a language tag. ``language`` is ``None`` for ``und``.
    ``whole`` holds a tag that is read whole: a private-use tag (``x-foo``)
    or a grandfathered tag with no replacement."""
    language: Optional[str] = None
    extlangs: Tuple[str, ...] = ()
    script: Optional[str] = None
    region: Optional[str] = None
    variants: Tuple[str, ...] = ()
    extensions: Tuple[str, ...] = ()
    private: Optional[str] = None
    whole: Optional[str] = None

    def __str__(self) -> str:
        if self.whole:
            return self.whole
        parts = [self.language or "und", *self.extlangs]
        parts += [p for p in (self.script, self.region) if p]
        parts += [*self.variants, *self.extensions]
        if self.private:
            parts.append(self.private)
        return "-".join(parts)


class _FrozenDict(dict):
    """A dict that refuses changes after it is built.

    It stays a dict, so JSON, copy and pickle still work. ``__reduce__``
    returns a plain dict, so a copy or an unpickled value is mutable.
    """

    def _immutable(self, *args, **kwargs):
        raise TypeError("linguatag package data is read-only")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable

    def __ior__(self, other):
        raise TypeError("linguatag package data is read-only")

    def __reduce__(self):
        return (dict, (dict(self),))


def _freeze(value: object) -> object:
    """A read-only view of parsed JSON: frozen dicts and tuples throughout."""
    if isinstance(value, dict):
        return _FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@lru_cache(maxsize=None)
def _raw_data(name: str) -> dict:
    """The parsed JSON file ``name``, shared and not frozen. Code of this
    package reads it and never changes it; freezing costs more than the
    read."""
    return json.loads((_DATA / name).read_text(encoding="utf-8"))


def _raw_registry(kind: str) -> Dict[str, dict]:
    """The records of ``kind``. The language records are a file of their own,
    as most callers read no language record."""
    return _raw_data("language_subtags.json" if kind == "language" else "subtags.json").get(kind, {})


@lru_cache(maxsize=None)
def load_data(name: str) -> dict:
    """A read-only view of the JSON file ``name`` of ``linguatag/data``.

    The view is made once and shared. A caller cannot change package data by
    changing a returned mapping or sequence. It stays a dict, so JSON, copy
    and pickle work; JSON arrays are tuples.
    """
    return _freeze(_raw_data(name))


@lru_cache(maxsize=None)
def registry(kind: str) -> Dict[str, dict]:
    """The IANA registry records of ``kind`` (``language``, ``extlang``,
    ``script``, ``region``, ``variant``, ``grandfathered``, ``redundant``),
    as a read-only view like :func:`load_data`."""
    return _freeze(_raw_registry(kind))


def language_scope(tag: str) -> Optional[str]:
    """The IANA scope of the primary language subtag of ``tag``:
    ``"language"``, ``"macrolanguage"``, ``"collection"`` (a family such as
    ``itc``), ``"special"`` (``mul``, ``und``, ``zxx``, ``mis``) or
    ``"private-use"``. ``None`` when the registry has no such subtag, as for
    the retired ISO 639-3 code ``mol``."""
    base = tag.strip().replace("_", "-").split("-")[0].lower()
    record = _raw_registry("language").get(base)
    if record is None:
        return "private-use" if len(base) == 3 and "qaa" <= base <= "qtz" else None
    return record.get("scope", "language")


@lru_cache(maxsize=1)
def _whole_tags() -> Dict[str, Optional[str]]:
    """Grandfathered and redundant tags, lowercase, to their IANA
    Preferred-Value or ``None``."""
    tags = {**_raw_registry("grandfathered"), **_raw_registry("redundant")}
    return {tag.lower(): record.get("preferred") for tag, record in tags.items()}


@lru_cache(maxsize=1)
def _irregular() -> FrozenSet[str]:
    """The grandfathered tags, which are read whole (RFC 5646 section 2.1:
    "The only exceptions to this ability to infer meaning from subtag
    structure are the grandfathered tags")."""
    return frozenset(tag.lower() for tag in _raw_registry("grandfathered"))


def _alphanum(subtag: str, low: int, high: int) -> bool:
    return low <= len(subtag) <= high and subtag.isascii() and subtag.isalnum()


def _is_variant(subtag: str) -> bool:
    return (_alphanum(subtag, 5, 8)
            or (len(subtag) == 4 and subtag[0].isdigit() and _alphanum(subtag, 4, 4)))


def is_region(subtag: str) -> bool:
    return (len(subtag) == 2 and subtag.isalpha()) or (len(subtag) == 3 and subtag.isdigit())


def is_script(subtag: str) -> bool:
    return len(subtag) == 4 and subtag.isalpha()


def _parse_rest(subtags: List[str], language: Optional[str],
                allow_extlang: bool) -> LanguageTag:
    extlangs: List[str] = []
    script = region = private = None
    variants: List[str] = []
    extensions: List[str] = []
    index = 0
    while (allow_extlang and index < len(subtags) and len(extlangs) < 3
           and len(subtags[index]) == 3 and subtags[index].isalpha()):
        extlangs.append(subtags[index])
        index += 1
    if index < len(subtags) and is_script(subtags[index]):
        script = subtags[index].title()
        index += 1
    if index < len(subtags) and is_region(subtags[index]):
        region = subtags[index].upper()
        index += 1
    while index < len(subtags) and _is_variant(subtags[index]):
        variants.append(subtags[index])
        index += 1
    while index < len(subtags):
        singleton = subtags[index]
        if len(singleton) != 1:
            raise LanguageTagError(f"subtag {singleton!r} is out of place")
        rest = subtags[index + 1:]
        if singleton == "x":
            if not rest:
                raise LanguageTagError("'x' must be followed by a private-use subtag")
            private = "-".join(subtags[index:])
            break
        end = 0
        while end < len(rest) and len(rest[end]) > 1:
            end += 1
        if end == 0:
            raise LanguageTagError(f"extension {singleton!r} has no subtag")
        if any(e.split("-")[0] == singleton for e in extensions):
            raise LanguageTagError(f"extension {singleton!r} appears twice")
        extensions.append("-".join([singleton, *rest[:end]]))
        index += 1 + end
    return LanguageTag(language=language, extlangs=tuple(extlangs), script=script,
                       region=region, variants=tuple(variants),
                       extensions=tuple(extensions), private=private)


#: glibc locale modifiers that name a script or a variant (`sr_RS@latin`,
#: `ca_ES@valencia`). Any other modifier (`@euro`) names no part of a language.
_POSIX_MODIFIERS = {"latin": "Latn", "cyrillic": "Cyrl", "devanagari": "Deva", "valencia": "valencia"}


def _posix_to_tag(text: str) -> str:
    """The language part of a POSIX locale string, as a tag: the codeset
    after ``.`` goes, and a modifier after ``@`` that names a script or a
    variant becomes that subtag. ``C`` and ``POSIX`` are ``und``. A string
    with no ``.`` or ``@`` comes back unchanged."""
    if text.upper().partition(".")[0] in ("C", "POSIX"):
        return "und"
    if "." not in text and "@" not in text:
        return text
    core, _, modifier = text.partition("@")
    parts = core.partition(".")[0].replace("_", "-").split("-")
    subtag = _POSIX_MODIFIERS.get(modifier.partition(".")[0].lower())
    if subtag and len(subtag) == 4:
        # A script in the tag itself wins over the modifier.
        if not (len(parts) > 1 and len(parts[1]) == 4 and parts[1].isalpha()):
            parts.insert(1, subtag)
    elif subtag:
        parts.append(subtag)
    return "-".join(parts)


def _tolerant(tag: str) -> LanguageTag:
    parts = [part for part in _posix_to_tag(tag.strip()).replace("_", "-").split("-") if part]
    lowered = [part.lower() for part in parts]
    private = None
    if "x" in lowered[1:]:
        at = lowered.index("x", 1)
        if at + 1 < len(parts):
            private = "-".join(lowered[at:])
        parts = parts[:at]
    for end in range(len(parts), 0, -1):
        try:
            prefix = parse("-".join(parts[:end]))
        except LanguageTagError:
            continue
        if prefix.whole:
            return prefix
        return replace(prefix, private=private or prefix.private)
    raise LanguageTagError(f"{tag!r} has no prefix that names a language")


def parse(tag: str, strict: bool = True) -> LanguageTag:
    """The subtags of ``tag``, with the BCP 47 case conventions and nothing
    replaced.

    Underscores count as hyphens and case does not matter. ``root`` is
    ``und`` (UTS #35 section 3.8, "Unicode Locale Identifier: CLDR to BCP
    47": "Replace the special language identifier "root" with the BCP 47
    primary language tag "und"").

    With ``strict=False``, a string that is not well-formed reads as much as
    it can: a POSIX locale (``ar_SA.UTF-8``) reads as its language, the
    longest well-formed prefix before ``-x-`` is the tag, and the private-use
    part stays even with a subtag longer than 8 characters
    (``an-x-benasques``).

    Raises:
        LanguageTagError: ``tag`` is not well-formed (RFC 5646 section 2.1),
            or, with ``strict=False``, no prefix of it names a language.
    """
    if not strict:
        return _tolerant(tag)
    if not tag.isascii():
        raise LanguageTagError(f"{tag!r} is not ASCII")
    text = tag.replace("_", "-").lower()
    if text in _irregular():
        return LanguageTag(whole=text)
    subtags = text.split("-")
    for subtag in subtags:
        if not _alphanum(subtag, 1, 8):
            raise LanguageTagError(f"subtag {subtag!r} is not 1 to 8 letters and digits")
    first = subtags[0]
    if first == "x":
        if len(subtags) == 1:
            raise LanguageTagError("'x' must be followed by a private-use subtag")
        return LanguageTag(whole=text)
    if not first.isalpha() or len(first) < 2:
        raise LanguageTagError(f"{first!r} is not a language subtag")
    if first == "root":
        first = "und"
    language = None if first == "und" else first
    return _parse_rest(subtags[1:], language, allow_extlang=len(first) <= 3)


@dataclass(frozen=True)
class _Rule:
    """A UTS #35 Annex C alias rule: the fields of its type and of its
    replacement. ``regions`` holds several regions for a territory alias that
    names more than one."""
    language: Optional[str]
    script: Optional[str]
    region: Optional[str]
    variants: FrozenSet[str]
    to_language: Optional[str]
    to_script: Optional[str]
    regions: Tuple[str, ...]
    to_variants: FrozenSet[str] = field(default_factory=frozenset)

    def order(self) -> tuple:
        """UTS #35 Annex C, Preprocessing, step 5: more fields first, then
        the fields present in the order L, S, R, V, then the values."""
        fields = (self.language, self.script, self.region)
        count = sum(f is not None for f in fields) + len(self.variants)
        present = tuple(f is None for f in fields) + (not self.variants,)
        values = tuple(f or "" for f in fields) + (tuple(sorted(self.variants)),)
        return -count, present, values

    def matches(self, tag: LanguageTag) -> bool:
        return ((self.language is None or self.language == tag.language)
                and (self.script is None or self.script == tag.script)
                and (self.region is None or self.region == tag.region)
                and self.variants <= set(tag.variants))


def _language_id(text: str) -> Optional[LanguageTag]:
    """``text`` as a UTS #35 unicode_language_id, or ``None`` when it is not
    one (it has an extlang, an extension or a private-use part)."""
    try:
        tag = parse(text)
    except LanguageTagError:
        return None
    if tag.whole or tag.extlangs or tag.extensions or tag.private:
        return None
    return tag


#: The ISO 639-2 codes that CLDR replaces as overlong with the macrolanguage
#: of their ISO 639-1 code. The Library of Congress ISO 639-2 list gives
#: "twi||tw|Twi|twi", so `twi` is `tw`; it gives "bih|||Bihari languages", no
#: ISO 639-1 code, so `bih` stays (IANA replaces the deprecated `bh` with
#: `bih`).
_OVERLONG_WITHOUT_MACROLANGUAGE = {"twi": "tw", "bih": None}
_ALIAS_KINDS = (("language", ""), ("script", "und-"), ("region", "und-"), ("variant", "und-"))


@lru_cache(maxsize=2)
def _alias_table(macrolanguage: bool) -> Tuple[Dict[str, str], Dict[str, str]]:
    """``(rules, legacy)``: the alias types that are language ids, and the
    language alias types that are not (UTS #35 Annex C, Preprocessing, steps
    2 and 3), each lowercase to its replacement.

    The CLDR rules come first and the IANA Preferred-Values over them, so a
    deprecated subtag takes the value RFC 5646 section 4.5 names: `drh` is
    `khk`, where CLDR goes on to the macrolanguage, `mn`."""
    aliases = _raw_data("aliases.json")
    rules: Dict[str, str] = {}
    legacy: Dict[str, str] = {}
    for kind, prefix in _ALIAS_KINDS:
        for type_, (replacement, reason) in aliases[kind].items():
            if not macrolanguage:
                if reason == "macrolanguage":
                    continue
                if type_ in _OVERLONG_WITHOUT_MACROLANGUAGE:
                    replacement = _OVERLONG_WITHOUT_MACROLANGUAGE[type_]
                    if replacement is None:
                        continue
            type_ = (prefix + type_).lower()
            replacement = " ".join(prefix + r for r in replacement.split())
            if _language_id(type_) is not None:
                rules[type_] = replacement
            elif kind == "language":
                legacy[type_] = replacement
    for kind, prefix in _ALIAS_KINDS:
        for subtag, record in _raw_registry(kind).items():
            if "preferred" in record and ".." not in subtag:
                rules[(prefix + subtag).lower()] = prefix + record["preferred"]
    for tag, preferred in _whole_tags().items():
        if preferred:
            (rules if _language_id(tag) is not None else legacy)[tag] = preferred
    return rules, legacy


def _build_rules(macrolanguage: bool) -> List[_Rule]:
    """The alias rules in UTS #35 Annex C order, built from the CLDR and IANA
    data. ``scripts/build_alias_rules.py`` writes them to
    ``alias_rules.json``, which :func:`_rules` reads."""
    table, _ = _alias_table(macrolanguage)
    rules: List[_Rule] = []
    for type_, replacement in table.items():
        source = _language_id(type_)
        targets = [_language_id(r) for r in replacement.split()]
        if source is None or any(t is None for t in targets):
            continue
        first = targets[0]
        rules.append(_Rule(source.language, source.script, source.region,
                           frozenset(source.variants), first.language, first.script,
                           tuple(t.region for t in targets if t.region),
                           frozenset(first.variants)))
    rules.sort(key=_Rule.order)
    return rules


def _rule_row(rule: _Rule) -> list:
    return [rule.language, rule.script, rule.region, sorted(rule.variants), rule.to_language,
            rule.to_script, list(rule.regions), sorted(rule.to_variants)]


@lru_cache(maxsize=1)
def _compiled() -> dict:
    return _raw_data("alias_rules.json")


def _legacy(macrolanguage: bool) -> Dict[str, str]:
    return _compiled()["macrolanguage" if macrolanguage else "standard"]["legacy"]


@lru_cache(maxsize=2)
def _rules(macrolanguage: bool) -> Tuple[List[_Rule], Dict[str, List[int]]]:
    """The alias rules in UTS #35 Annex C order, and the positions of the
    rules under the first field their type names, so a tag is tried only
    against rules that can match."""
    rules = [_Rule(language, script, region, frozenset(variants), to_language, to_script,
                   tuple(regions), frozenset(to_variants))
             for language, script, region, variants, to_language, to_script, regions, to_variants
             in _compiled()["macrolanguage" if macrolanguage else "standard"]["rules"]]
    index: Dict[str, List[int]] = {}
    for position, rule in enumerate(rules):
        key = rule.language or rule.script or rule.region or min(rule.variants)
        index.setdefault(key, []).append(position)
    return rules, index


def _fields(tag: LanguageTag) -> List[Tuple[str, str]]:
    """The ``(field, lowercase subtag)`` pairs of ``tag`` in rule order: a
    rule is indexed under the first of them."""
    pairs = [("language", tag.language), ("script", tag.script), ("region", tag.region)]
    pairs += [("variant", variant) for variant in sorted(tag.variants)]
    return [(field, subtag.lower()) for field, subtag in pairs if subtag]


@lru_cache(maxsize=1)
def _alias_keys() -> Tuple[FrozenSet[Tuple[str, str]], FrozenSet[str]]:
    """``(keys, wholes)``: every field and subtag that a rule of either
    :func:`_rules` table is indexed under, and every lowercase tag that a
    legacy replacement of either :func:`_alias_table` can match whole. Both
    are read from the data without building the tables, and may hold more
    than the tables do, never less. The IANA Preferred-Values add no key: each
    subtag that has one is a CLDR alias type too."""
    aliases = _raw_data("aliases.json")
    replaced = [tag for tag, preferred in _whole_tags().items() if preferred]
    keys = set()
    wholes = set(replaced)
    for kind, prefix in _ALIAS_KINDS:
        for type_ in aliases[kind]:
            if "-" not in type_:
                keys.add((kind, type_.lower()))
                continue
            wholes.add((prefix + type_).lower())
            tag = _language_id((prefix + type_).lower())
            if tag is not None:
                keys.add(_fields(tag)[0])
    keys.update(_fields(tag)[0] for tag in map(_language_id, replaced) if tag is not None)
    return frozenset(keys), frozenset(wholes)


def _has_no_alias(tag: LanguageTag) -> bool:
    """Whether no alias rule can replace any subtag of ``tag``, so that
    canonicalizing it only orders its variants and extensions."""
    if tag.whole or tag.extlangs or tag.language is None:
        return False
    keys, wholes = _alias_keys()
    return str(tag).lower() not in wholes and keys.isdisjoint(_fields(tag))


def _canonical(tag: LanguageTag, macrolanguage: bool) -> LanguageTag:
    if _has_no_alias(tag):
        return replace(tag, variants=tuple(sorted(set(tag.variants))),
                       extensions=tuple(sorted(tag.extensions)))
    legacy = _legacy(macrolanguage)
    whole = str(tag).lower()
    if whole in legacy and (not tag.extlangs or whole in _whole_tags()):
        tag = parse(legacy[whole])
    if tag.whole:
        return tag
    if tag.extlangs:
        record = _raw_registry("extlang").get(tag.extlangs[0], {})
        if tag.language in record.get("prefix", ()) and "preferred" in record:
            tag = replace(tag, language=record["preferred"], extlangs=tag.extlangs[1:])
    rules, index = _rules(macrolanguage)
    seen = set()
    while tag not in seen:
        seen.add(tag)
        keys = [tag.language, tag.script, tag.region, *tag.variants]
        position = min((p for key in keys if key for p in index.get(key, ())
                        if rules[p].matches(tag)), default=None)
        if position is None:
            break
        # UTS #35 Annex C, 4. Replacement, with the Territory Exception.
        rule = rules[position]
        language = (rule.to_language if rule.language is not None
                    else tag.language or rule.to_language)
        script = rule.to_script if rule.script is not None else tag.script or rule.to_script
        if rule.region is not None or (tag.region is None and rule.regions):
            region = rule.regions[0] if rule.regions else None
            if len(rule.regions) > 1:
                likely = _lookup(LanguageTag(language=language, script=script))
                if likely is not None and likely.region in rule.regions:
                    region = likely.region
        else:
            region = tag.region
        if rule.variants:
            variants = (set(tag.variants) - rule.variants) | rule.to_variants
        else:
            variants = set(tag.variants or rule.to_variants)
        tag = replace(tag, language=language, script=script, region=region,
                      variants=tuple(sorted(variants)))
    return replace(tag, variants=tuple(sorted(set(tag.variants))),
                   extensions=tuple(sorted(tag.extensions)))


@lru_cache(maxsize=4096)
def standardize(tag: str, macrolanguage: bool = False) -> str:
    """``tag`` in canonical form (RFC 5646 section 4.5), with the CLDR alias
    rules (the macrolanguage ones only with ``macrolanguage``), and with no
    script that IANA suppresses for its language.

    ``en_us`` is ``en-US``, ``iw`` is ``he``, ``eng`` is ``en``, ``zh-yue`` is
    ``yue``, ``sh`` is ``sr-Latn``, ``en-Latn`` is ``en`` and ``cmn`` stays
    ``cmn``.

    Raises:
        LanguageTagError: ``tag`` is not well-formed.
    """
    canonical = _canonical(parse(tag), macrolanguage=macrolanguage)
    if canonical.language and canonical.script:
        record = _raw_registry("language").get(canonical.language, {})
        if record.get("suppress_script") == canonical.script:
            canonical = replace(canonical, script=None)
    return str(canonical)


def _lookup(tag: LanguageTag) -> Optional[LanguageTag]:
    """The CLDR likely-subtags entry of the first of ``language_script_region``,
    ``language_script``, ``language_region`` and ``language`` that has one
    (UTS #35 section 4.3, "Lookup")."""
    likely = _raw_data("likely_subtags.json")["likely"]
    language = tag.language or "und"
    for parts in ((language, tag.script, tag.region), (language, tag.script),
                  (language, tag.region), (language,)):
        if None in parts:
            continue
        found = likely.get("-".join(parts))
        if found is not None:
            return parse(found)
    return None


@lru_cache(maxsize=4096)
def maximize(tag: str) -> Optional[LanguageTag]:
    """UTS #35 section 4.3, "Add Likely Subtags": ``tag`` with its empty
    script and region filled from CLDR likely subtags.

    ``zh-TW`` is ``zh-Hant-TW``, ``sr-ME`` is ``sr-Latn-ME`` and ``cmn`` is
    ``zh-Hans-CN``. The language comes out canonical, macrolanguage rules
    included. A tag with the language ``und`` is excluded, as section 4.3
    allows ("An implementation may choose to exclude language tags with the
    language subtag "und" from the following operation"), and gives
    ``None``; so does a language with no entry ("If there is no match,
    signal an error and stop") and a tag that is not well-formed.
    """
    try:
        source = _canonical(parse(tag), macrolanguage=True)
    except LanguageTagError:
        return None
    if source.whole or source.language is None:
        return None
    if source.script == "Zzzz":
        source = replace(source, script=None)
    if source.region == "ZZ":
        source = replace(source, region=None)
    if source.script and source.region:
        return source
    match = _lookup(source)
    if match is None:
        return None
    return replace(source, script=source.script or match.script,
                   region=source.region or match.region)
