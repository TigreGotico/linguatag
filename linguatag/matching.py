"""Language-tag standardization, distance, and closest match.

Everything rests on one distance function, :func:`lang_distance`;
:func:`closest_lang` is the candidate with the smallest distance. All policy
lives inside :func:`lang_distance`: tag standardization, the default region of
a bare tag, the Modern Standard Arabic fallback, and the behaviour when
``langcodes`` is absent.

The distance ladder, from nearest to farthest: identical tags (``0``), a bare
tag against its own default region (``0``), two regions of one language (a
small distance), a member language against its macrolanguage tag (``10``, the
threshold itself), and a different language (``>= 100`` with the coarse
measure, never a usable match).

``langcodes`` replaces an encompassed language with its macrolanguage
before it measures, from the CLDR ``languageAlias`` entries with
``reason="macrolanguage"``. UTS #35 (revision 79, CLDR 49), BCP 47
Conformance: "Each macrolanguage has an identified primary encompassed
language, which is treated as an alias for the macrolanguage, and thus is
replaced when canonicalizing". So ``tw`` against ``ak`` and ``cmn`` against
``zh`` are ``0``. The ``langcodes`` copy is older than CLDR 49 and still holds
three such entries that CLDR has removed::

    <languageAlias type="fat" replacement="ak" reason="macrolanguage"/> <!-- Fanti ⇒ Akan -->
    <languageAlias type="mnk" replacement="man" reason="macrolanguage"/> <!-- Mandinka ⇒ Mandingo -->
    <languageAlias type="knn" replacement="kok" reason="macrolanguage"/> <!-- Konkani (individual language) ⇒ Konkani -->

CLDR 46 dropped the ``knn`` entry and CLDR 48 the ``mnk`` entry. CLDR 49
dropped the ``fat`` entry (CLDR-19720, "Akan (ak) should only have one
encompassed language") and kept
``<languageAlias type="tw" replacement="ak" reason="macrolanguage"/>``. The
CLDR 49 ``languageMatching`` data names neither ``fat`` nor ``mnk``, so their
distance to any other language comes from
``<languageMatch desired="*" supported="*" distance="80"/>``: a different
language. Fanti and Mandinka measured against another language, their
macrolanguage included, are a different language here too. ``knn`` is not in
this rule, because CLDR 49 gives it
``<languageMatch desired="knn" supported="kok" distance="10" oneway="true"/>``.

A bare tag is measured from its default region (see :mod:`linguatag.regions`):
``en`` is ``en-GB``, so ``lang_distance("en", "en-GB")`` is ``0`` and
``lang_distance("en", "en-US")`` is a regional difference.

Tags are compared in their canonical form. RFC 5646 section 4.5, step 3:
"Subtags are replaced by their 'Preferred-Value', if there is one. For
extlangs, the original primary language subtag is also replaced if there is
a primary language subtag in the 'Preferred-Value'." So ``ar-apc`` and
``apc`` are one tag, and so are ``my-BU`` and ``my-MM``.

``langcodes`` is optional. Without it, :func:`lang_distance` falls back to a
coarse same-language measure with the same ordering for the cases locale
resolution depends on.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional, Sequence

from linguatag.lects import lect_score, without_private_use
from linguatag.regions import _is_region, _with_likely_script, with_default_region
from linguatag.standardize import (_preferred_values, _without_deprecated_language,
                                   _without_extlang, standardize_lang)

__all__ = [
    "standardize_lang",
    "lang_distance",
    "lang_matches",
    "closest_lang",
    "is_arabic_variety",
    "DEFAULT_MAX_LANGUAGE_DISTANCE",
]

# langcodes rates a distance of 4 to 9 an unproblematic regional difference
# and 10 to 24 a gray area that depends on the use case. This module accepts
# 10 or less. The bound is inclusive because langcodes uses 10 for a specific
# language against its more-commonly-used macrolanguage tag, such as "arz"
# against "ar".
DEFAULT_MAX_LANGUAGE_DISTANCE = 10

# The individual languages of the ISO 639-3 `ara` macrolanguage (SIL
# macrolanguage mappings; ajp and bbz are retired codes), which are the IANA
# language subtags with `Macrolanguage: ar`, and Hassaniyya (`mey`). The IANA
# record of `mey` names no macrolanguage, but Glottolog 5.4 classifies
# Hassaniyya as Arabic > North African Arabic > Western Middle Arabic
# (languoid hass1238), and CLDR 49 likely subtags write it in Arabic script
# (mey_Arab_DZ). A request for one of them, or for `ar` with any region, in
# Arabic script, falls back to the bare Modern Standard Arabic entry (`ar`,
# `arb` or `ar-001`) when nothing closer is available, since speakers of every
# variety expect MSA from a voice assistant. Other macrolanguages get no such
# rule: Cantonese does not fall back to Mandarin.
_ARABIC_VARIETIES = frozenset(
    "ar aao abh abv acm acq acw acx acy adf aeb aec afb ajp apc apd arb arq ars "
    "ary arz auz avl ayh ayl ayn ayp bbz mey pga shu ssh".split())
# `ara` is the ISO 639-2 code of Arabic. langcodes reads it as `ar`; without
# langcodes it stays `ara`.
_ARABIC_LANGUAGES = _ARABIC_VARIETIES | {"ara"}
# CLDR likely subtags write two of them in Latin script: Cypriot Maronite
# Arabic (acy_Latn_CY) and Juba Arabic (pga_Latn_SS). With no script subtag,
# a request for either is not in Arabic script.
_LATIN_SCRIPT_ARABIC = frozenset({"acy", "pga"})
_MSA = ("ar", "arb", "ar-001")
_ARABIC_FALLBACK_DISTANCE = 5

# Cantonese, Hakka, Min Nan, Wu, Gan and Xiang are never served as Mandarin.
# langcodes measures `yue-CN` or `hak` against `zh-CN` or `cmn` at 10, a
# member against its macrolanguage in one script, and that is a usable match;
# they are not mutually intelligible with Mandarin. Against `cmn`, and against
# `zh` in Simplified script, they count as different languages, as the coarse
# measure counts them. `zh` in Traditional script keeps the langcodes
# distance: a `zh-HK` resource is often Cantonese.
_NOT_MANDARIN = frozenset({"yue", "hak", "nan", "wuu", "gan", "hsn"})
_MANDARIN = "cmn"
_CHINESE = "zh"
_DIFFERENT_LANGUAGE_DISTANCE = 100

# Fanti and Mandinka, which langcodes reads as Akan and Mandingo (see the
# module docstring).
_FORMER_MACROLANGUAGE_ALIASES = frozenset({"fat", "mnk"})


def _is_simplified(tag: str) -> bool:
    try:
        from langcodes import Language
        return Language.get(tag).maximize().script == "Hans"
    except Exception:
        return False


@lru_cache(maxsize=4096)
def _parseable_prefix(tag: str) -> str:
    """The longest leading part of ``tag`` that ``langcodes`` parses.

    A voice id such as ``zh-HK-HiuMaanNeural`` is not a language tag, but its
    ``zh-HK`` is, and that is what it is measured as. A tag with no parseable
    prefix, or any tag when ``langcodes`` is absent, is returned unchanged.
    """
    try:
        from langcodes import Language
    except ImportError:
        return tag
    parts = tag.split("-")
    for end in range(len(parts), 0, -1):
        candidate = "-".join(parts[:end])
        try:
            Language.get(candidate)
        except Exception:
            continue
        return candidate
    return tag


def _sinitic_against_mandarin(a: str, b: str) -> bool:
    languages = {a.split("-")[0].lower(): a, b.split("-")[0].lower(): b}
    if _NOT_MANDARIN.isdisjoint(languages):
        return False
    return _MANDARIN in languages or (_CHINESE in languages
                                      and _is_simplified(languages[_CHINESE]))


def _former_macrolanguage_alias(a: str, b: str) -> bool:
    languages = {a.split("-")[0].lower(), b.split("-")[0].lower()}
    return len(languages) == 2 and not _FORMER_MACROLANGUAGE_ALIASES.isdisjoint(languages)


def _langcodes_distance(desired: str, supported: str) -> Optional[int]:
    """``langcodes.tag_distance``, or ``None`` if no distance can be computed,
    including when ``langcodes`` is not installed."""
    try:
        from langcodes import tag_distance
        return int(tag_distance(desired, supported))
    except Exception:
        return None


def _coarse_distance(desired: str, supported: str) -> int:
    """A ``langcodes``-free distance.

    The two tags are already standardized and region-expanded. A shared
    primary subtag is near, a differing one is far; the generic (region-less)
    form of a language counts as nearer than a sibling region of it. The
    values 3, 5 and 100 carry ordering only: what matters is their relative
    order and whether they reach the threshold of 10. Private-use subtags
    count for nothing, as in ``langcodes``.
    """
    desired, supported = without_private_use(desired), without_private_use(supported)
    if desired.lower() == supported.lower():
        return 0
    if desired.split("-")[0].lower() != supported.split("-")[0].lower():
        return 100  # a different language, beyond any usable threshold
    if "-" not in desired or "-" not in supported:
        return 3  # one side is the generic language tag
    return 5  # two different regions of the same language


def lang_distance(desired: str, supported: str, lects: Optional[str] = None) -> int:
    """The distance between two BCP-47 language tags.

    ``0`` is identical; a larger number is further apart; a value above 10 is
    not a usable match. Both tags are standardized, and a tag with no region
    is measured from its default region, so ``lang_distance("pt", "pt-PT")``
    is ``0`` while ``lang_distance("pt", "pt-BR")`` is a regional difference.

    The spellings of Modern Standard Arabic (``ar``, ``arb``, ``ar-001``) are
    identical. An individual Arabic language (``arz``, ``apc``, ...),
    Hassaniyya (``mey``) or ``ar`` with any region, in Arabic script, measured
    against one of them, is at most 5. Cantonese, Hakka, Min Nan, Wu, Gan or
    Xiang (``yue``, ``hak``, ``nan``, ``wuu``, ``gan``, ``hsn``) measured
    against ``cmn``, or against ``zh`` in Simplified script, is a different
    language. So is Fanti (``fat``) or Mandinka (``mnk``) measured against
    another language, Akan (``ak``) and Mandingo (``man``) included.

    A tag that ``langcodes`` cannot parse, such as a voice id, is measured as
    its longest parseable prefix: ``zh-HK-HiuMaanNeural`` as ``zh-HK``. A tag
    with an empty subtag (``ar-``, ``ar_``, ``-ar``, ``en--US``) is not a
    language tag, and it is no usable match for any tag.

    Uses ``langcodes.tag_distance`` when available, and a coarse
    same-language measure otherwise.

    A private-use subtag counts for nothing unless ``lects`` asks for it:
    ``"dialect"`` scores the nearest other dialect before the standard
    language, ``"standard"`` the standard language before the dialects (see
    :mod:`linguatag.lects`). The lect score reorders candidates; it never
    raises a distance at or below the default threshold above it.
    """
    distance = _language_distance(desired, supported)
    if lects is None:
        return distance
    ceiling = max(distance, DEFAULT_MAX_LANGUAGE_DISTANCE)
    return min(distance + lect_score(desired, supported, lects), ceiling)


def _as_world_arabic(tag: str) -> str:
    """Every spelling of Modern Standard Arabic as ``ar-001``, the region the
    default-region rule gives a bare ``ar``. ``langcodes`` would otherwise
    place ``arb`` in Egypt. A private-use part is kept."""
    base, separator, private = tag.partition("-x-")
    if base.lower() in _MSA:
        return "ar-001" + separator + private
    return tag


def _has_empty_subtag(tag: str) -> bool:
    return "" in tag.split("-")


def _language_distance(desired: str, supported: str) -> int:
    a, b = standardize_lang(desired), standardize_lang(supported)
    # BCP 47 subtags are 1 to 8 characters long: a leading, trailing or
    # doubled separator makes a tag that names no language.
    if _has_empty_subtag(a) or _has_empty_subtag(b):
        return _DIFFERENT_LANGUAGE_DISTANCE
    a = _as_world_arabic(_parseable_prefix(a))
    b = _as_world_arabic(_parseable_prefix(b))
    if a.lower() == b.lower():
        return 0
    to_msa = without_private_use(b).lower() in _MSA
    a = _with_likely_script(with_default_region(a))
    b = _with_likely_script(with_default_region(b))
    if a.lower() == b.lower():
        return 0
    distance = _langcodes_distance(a, b)
    if distance is None:
        distance = _coarse_distance(a, b)
    if _sinitic_against_mandarin(a, b) or _former_macrolanguage_alias(a, b):
        distance = max(distance, _DIFFERENT_LANGUAGE_DISTANCE)
    language = a.split("-")[0].lower()
    scripts = [t.lower() for t in without_private_use(a).split("-")[1:]
               if len(t) == 4 and t.isalpha()]
    if not scripts:
        scripts = ["latn"] if language in _LATIN_SCRIPT_ARABIC else ["arab"]
    if to_msa and language in _ARABIC_VARIETIES and scripts == ["arab"]:
        distance = min(distance, _ARABIC_FALLBACK_DISTANCE)
    return distance


def lang_matches(a: str, b: str,
                 max_distance: int = DEFAULT_MAX_LANGUAGE_DISTANCE) -> bool:
    """``True`` when two BCP-47 tags are close enough to interchange.

    Args:
        a: the requested BCP-47 tag.
        b: the candidate tag. The relation is symmetric except for the
            Modern Standard Arabic fallback: ``arz`` is near ``ar``, but
            ``ar`` is not near ``arz``.
        max_distance: the inclusive upper bound on an acceptable distance.
            Pass ``max_distance=0`` to require an exact match.
    """
    return lang_distance(a, b) <= max_distance


def is_arabic_variety(tag: str) -> bool:
    """``True`` when ``tag`` names Arabic or a variety of Arabic.

    The language subtag decides, after :func:`standardize_lang`. Script,
    region and private-use subtags do not count, so ``ar-Latn-x-buckwalt``,
    ``arz-EG`` and Juba Arabic, ``pga``, are Arabic varieties. Arabic is
    ``ar`` (``ara``), its individual languages (the IANA language subtags
    with ``Macrolanguage: ar``, among them ``arb``, ``arz``, ``acy`` and
    ``pga``), and Hassaniyya, ``mey``. A different language written in Arabic
    script is not one: ``fa``, ``ur`` and ``und-Arab`` are ``False``, and so
    is a tag with an empty subtag.

    This tells what language a tag names. :func:`lang_distance` tells whether
    a resource for one tag can serve a request for another.
    """
    standard = standardize_lang(tag)
    if _has_empty_subtag(standard):
        return False
    return standard.split("-")[0].lower() in _ARABIC_LANGUAGES


def _language_subtag(tag: str) -> str:
    return tag.replace("_", "-").split("-", 1)[0].casefold()


def _has_preferred_value(tag: str) -> bool:
    return _without_deprecated_language(_without_extlang(tag)) != tag


def _region_subtag(tag: str) -> str:
    """The region subtag of ``tag`` (two letters or three digits), or ``""``."""
    for subtag in tag.replace("_", "-").split("-")[1:]:
        if len(subtag) == 1:
            break
        if _is_region(subtag):
            return subtag.lower()
    return ""


def _has_noncanonical_subtag(tag: str) -> bool:
    """Whether canonicalization replaces a subtag of ``tag``: a language,
    extlang or region subtag with an IANA Preferred-Value."""
    return (_has_preferred_value(tag)
            or _region_subtag(tag) in _preferred_values("deprecated_regions.json"))


def _is_other_code_of_language(target: str, candidate: str) -> bool:
    """Whether ``candidate`` writes the language of ``target`` with another
    code: one of the two has an IANA Preferred-Value that gives the other.

    RFC 5646 section 4.5, step 3: "Subtags are replaced by their
    'Preferred-Value', if there is one. For extlangs, the original primary
    language subtag is also replaced if there is a primary language subtag in
    the 'Preferred-Value'." So a deprecated language subtag and its
    Preferred-Value (``ajp`` and ``apc``) are two codes of one language, and
    so are a language-extlang pair and its Preferred-Value (``zh-hak`` and
    ``hak``). An ISO 639-2 or 639-3 code that ``langcodes`` reads as a shorter
    subtag (``fra`` as ``fr``) has no Preferred-Value, so it is not another
    code."""
    return (_language_subtag(candidate) != _language_subtag(target)
            and (_has_preferred_value(target) or _has_preferred_value(candidate))
            and _language_subtag(standardize_lang(candidate))
            == _language_subtag(standardize_lang(target)))


def closest_lang(target: str, available: Sequence[str],
                 max_distance: int = DEFAULT_MAX_LANGUAGE_DISTANCE,
                 lects: Optional[str] = None) -> Optional[str]:
    """The entry of ``available`` closest to ``target``.

    The candidate with the smallest :func:`lang_distance` wins when its
    distance is ``max_distance`` or less, so ``max_distance=0`` accepts exact
    matches only. A tie goes to the candidate that spells ``target`` itself
    (compared after :func:`standardize_lang`, without regard to case), so
    ``pt-PT`` picks ``pt-PT`` over ``pt``, which is also at 0. Next, a
    candidate that writes the target's language with another code of the
    same language (a deprecated code or an extlang form, and its
    Preferred-Value) loses the tie, so ``apc`` picks ``apc`` over ``ajp`` and
    ``hak`` picks ``hak`` over ``zh-hak``. An ISO 639-2 or 639-3 code such as
    ``fra`` for ``fr`` is not such a code. Next, a candidate with a language,
    extlang or region subtag that has a Preferred-Value loses the tie, so
    ``ar-apc`` picks ``apc`` over ``ajp`` and ``my-MM`` picks ``my-MM`` over
    ``my-BU``. Other ties resolve to the first candidate in iteration order.
    With ``lects``, the lect score orders the candidates within
    ``max_distance``; it decides no match.

    Args:
        target: the requested BCP-47 tag.
        available: the tags on hand: directory names, voice ids, model
            languages. Iterated once.
        max_distance: the inclusive upper bound on an acceptable match.
        lects: ``None``, ``"dialect"`` or ``"standard"``, as for
            :func:`lang_distance`. ``closest_lang("an-x-cheso", ["an",
            "an-x-ansotano"], lects="dialect")`` is ``"an-x-ansotano"``.

    Returns:
        The original string from ``available`` that best matches ``target``,
        verbatim, or ``None`` when nothing qualifies.
    """
    wanted = standardize_lang(target).casefold()
    best: Optional[str] = None
    best_rank: Optional[tuple] = None
    for candidate in available:
        distance = lang_distance(target, candidate)
        if distance > max_distance:
            continue
        rank = (distance if lects is None else lang_distance(target, candidate, lects),
                standardize_lang(candidate).casefold() != wanted,
                _is_other_code_of_language(target, candidate),
                _has_noncanonical_subtag(candidate))
        if best_rank is None or rank < best_rank:
            best, best_rank = candidate, rank
    return best
