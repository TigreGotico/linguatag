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

A bare tag is measured from its default region (see :mod:`linguatag.regions`):
``en`` is ``en-GB``, so ``lang_distance("en", "en-GB")`` is ``0`` and
``lang_distance("en", "en-US")`` is a regional difference.

``langcodes`` is optional. Without it, :func:`lang_distance` falls back to a
coarse same-language measure with the same ordering for the cases locale
resolution depends on.
"""
from __future__ import annotations

from typing import Optional, Sequence

from linguatag.regions import with_default_region

__all__ = [
    "standardize_lang",
    "lang_distance",
    "lang_matches",
    "closest_lang",
    "DEFAULT_MAX_LANGUAGE_DISTANCE",
]

# A language distance of 10 or less is a usable regional match, as the
# langcodes distance-values documentation reads it and OVOS-INTENT-2 §2.2
# adopts. The bound is inclusive, so 10 itself qualifies: langcodes gives
# exactly 10 to a specific language against its macrolanguage tag, such as
# "arz" against "ar".
DEFAULT_MAX_LANGUAGE_DISTANCE = 10

# The individual languages of the ISO 639-3 `ara` macrolanguage (SIL
# macrolanguage mappings; ajp and bbz are retired codes). A request for one of
# them, or for `ar` with any region, in Arabic script, falls back to the bare
# Modern Standard Arabic entry (`ar` or `arb`) when nothing closer is
# available, since speakers of every variety expect MSA from a voice
# assistant. Other macrolanguages get no such rule: Cantonese does not fall
# back to Mandarin.
_ARABIC_VARIETIES = frozenset(
    "ar aao abh abv acm acq acw acx acy adf aeb aec afb ajp apc apd arb arq ars "
    "ary arz auz avl ayh ayl ayn ayp bbz pga shu ssh".split())
_MSA = ("ar", "arb")
_ARABIC_FALLBACK_DISTANCE = 5


def standardize_lang(tag: str) -> str:
    """Normalize a BCP-47 language tag for comparison.

    Folds underscores to hyphens, lowercases the primary subtag, uppercases
    the region and, with ``langcodes``, resolves canonical script and region
    forms, so that two spellings of one language (``en_us``, ``en-US``)
    reduce to one comparable string.

    Args:
        tag: a BCP-47-like language tag, possibly underscore-separated or
            mixed-case, as directory names and config values often are.

    Returns:
        ``langcodes.standardize_tag``'s output when ``langcodes`` is
        installed; otherwise a primary-lowercase, region-uppercase form.
    """
    if tag.lower() in ("tl", "tgl"):
        # langcodes folds Tagalog into the `fil` macrolanguage; Tagalog stays
        # a language of its own here.
        return "tl"
    try:
        from langcodes import standardize_tag
        return str(standardize_tag(tag))
    except Exception:
        normalized = tag.replace("_", "-")
        if "-" in normalized:
            primary, rest = normalized.split("-", 1)
            return f"{primary.lower()}-{rest.upper()}"
        return normalized.lower()


def _langcodes_distance(desired: str, supported: str) -> Optional[int]:
    """``langcodes.tag_distance``, retried on the primary subtag if the full
    tag is unparseable. ``None`` if no distance can be computed, including
    when ``langcodes`` is not installed."""
    try:
        from langcodes import tag_distance
    except ImportError:
        return None
    for candidate in (supported, supported.split("-")[0]):
        try:
            return int(tag_distance(desired, candidate))
        except Exception:
            continue
    return None


def _coarse_distance(desired: str, supported: str) -> int:
    """A ``langcodes``-free distance.

    The two tags are already standardized and region-expanded. A shared
    primary subtag is near, a differing one is far; the generic (region-less)
    form of a language counts as nearer than a sibling region of it. The
    values 3, 5 and 100 carry ordering only: what matters is their relative
    order and whether they reach the threshold of 10.
    """
    if desired.split("-")[0].lower() != supported.split("-")[0].lower():
        return 100  # a different language, beyond any usable threshold
    if "-" not in desired or "-" not in supported:
        return 3  # one side is the generic language tag
    return 5  # two different regions of the same language


def lang_distance(desired: str, supported: str) -> int:
    """The distance between two BCP-47 language tags.

    ``0`` is identical; a larger number is further apart; a value above 10 is
    not a usable match. Both tags are standardized, and a tag with no region
    is measured from its default region, so ``lang_distance("pt", "pt-PT")``
    is ``0`` while ``lang_distance("pt", "pt-BR")`` is a regional difference.

    An individual Arabic language (``arz``, ``apc``, ...) or ``ar`` with any
    region, in Arabic script, measured against bare ``ar`` or ``arb``, is at
    most 5.

    Uses ``langcodes.tag_distance`` when available, and a coarse
    same-language measure otherwise.
    """
    a = standardize_lang(desired)
    b = standardize_lang(supported)
    if a.lower() == b.lower():
        return 0
    to_msa = b.lower() in _MSA
    a, b = with_default_region(a), with_default_region(b)
    if a.lower() == b.lower():
        return 0
    distance = _langcodes_distance(a, b)
    if distance is None:
        distance = _coarse_distance(a, b)
    scripts = [t.lower() for t in a.split("-")[1:] if len(t) == 4 and t.isalpha()]
    if (to_msa and a.split("-")[0].lower() in _ARABIC_VARIETIES
            and scripts in ([], ["arab"])):
        distance = min(distance, _ARABIC_FALLBACK_DISTANCE)
    return distance


def lang_matches(a: str, b: str,
                 max_distance: int = DEFAULT_MAX_LANGUAGE_DISTANCE) -> bool:
    """``True`` when two BCP-47 tags are close enough to interchange.

    Args:
        a: one BCP-47 tag.
        b: the other BCP-47 tag. The relation is symmetric.
        max_distance: the inclusive upper bound on an acceptable distance.
            Pass ``max_distance=0`` to require an exact match.
    """
    return lang_distance(a, b) <= max_distance


def closest_lang(target: str, available: Sequence[str],
                 max_distance: int = DEFAULT_MAX_LANGUAGE_DISTANCE
                 ) -> Optional[str]:
    """The entry of ``available`` closest to ``target``.

    The candidate with the smallest :func:`lang_distance` wins when its
    distance is ``max_distance`` or less, so ``max_distance=0`` accepts exact
    matches only. Ties resolve to the first candidate in iteration order.

    Args:
        target: the requested BCP-47 tag.
        available: the tags on hand: directory names, voice ids, model
            languages. Iterated once.
        max_distance: the inclusive upper bound on an acceptable match.

    Returns:
        The original string from ``available`` that best matches ``target``,
        verbatim, or ``None`` when nothing qualifies.
    """
    best: Optional[str] = None
    best_distance: Optional[int] = None
    for candidate in available:
        distance = lang_distance(target, candidate)
        if best_distance is None or distance < best_distance:
            best, best_distance = candidate, distance

    if best is None:
        return None
    if best_distance <= max_distance:
        return best
    return None
