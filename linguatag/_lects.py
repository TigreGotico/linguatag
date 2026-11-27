"""How near two lects are: tags that name a dialect with a private-use subtag.

BCP-47 gives a private-use subtag no meaning, so the UTS #35 matching
distance ignores it:
``an-x-cheso``, ``an-x-ansotano`` and ``an`` are all at distance 0. ``data/lineage.json``
places each lect in a tree, a dialect under its language and a sub-dialect
under its dialect, cut to what lects need, and the number of steps between
two tags in it is their nearness.

A lect score is added to the language distance only when a caller asks for one,
with one of two orders:

``"dialect"``
    The nearest other dialect first, the standard language after it. A parent
    dialect is 1 step away, a sibling 2, anything further or unknown 3, and
    the standard language 4.
``"standard"``
    The standard language first (1), the dialects after it by the same steps
    (2 to 4).

A request for the standard language scores a dialect of it by its steps plus 1.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, FrozenSet, List, Optional, Tuple

from linguatag._bcp47 import _raw_data
from linguatag._standardize import standardize_lang

LECT_MODES = ("dialect", "standard")

_FAR = 3
_STANDARD_LAST = _FAR + 1


def _parents() -> Dict[str, str]:
    return _raw_data("lineage.json")["parents"]


def private_use(tag: str) -> Tuple[str, ...]:
    """The private-use subtags of ``tag``: ``("cheso",)`` for ``an-x-cheso``."""
    parts = standardize_lang(tag).lower().split("-")
    return tuple(parts[parts.index("x") + 1:]) if "x" in parts else ()


def without_private_use(tag: str) -> str:
    """``tag`` standardized, without its private-use subtags."""
    tag = standardize_lang(tag)
    base, separator, _ = tag.partition("-x-")
    return base if separator else tag


@lru_cache(maxsize=1)
def _known() -> FrozenSet[str]:
    """Every lect that the data names, lowercase."""
    parents = _parents()
    return frozenset(tag.lower() for tag in [*parents, *parents.values(), *_raw_data("lects.json")])


def _drop_last_private_use(tag: str) -> str:
    """``tag`` without its last private-use subtag: ``an-x-cheso-foo`` is
    ``an-x-cheso``, and ``an-x-cheso`` is ``an``."""
    head, _, _ = tag.rpartition("-")
    return head[:-2] if head.endswith("-x") else head


def _ancestors(tag: str) -> List[str]:
    """``tag`` and its ancestors. A lect the tree does not hold loses one
    private-use subtag at a time (RFC 4647 section 3.4) until it reaches a
    lect the tree holds, or its language."""
    parents = _parents()
    chain = [tag]
    while len(chain) <= len(parents) + len(tag):
        node = chain[-1]
        if node in parents:
            chain.append(parents[node])
        elif private_use(node) and not node.lower().startswith("x-"):
            chain.append(_drop_last_private_use(node))
        else:
            break
    return [node.lower() for node in chain]


def _without_extensions(tag: str) -> str:
    """``tag`` without its extensions: ``pt-PT-u-ca-gregory-x-porto`` is
    ``pt-PT-x-porto``."""
    kept, in_extension = [], False
    for index, part in enumerate(tag.split("-")):
        if index and len(part) == 1:
            in_extension = part.lower() != "x"
        if not in_extension:
            kept.append(part)
    return "-".join(kept)


def _as_known_lect(tag: str) -> str:
    """``tag`` as the nearest lect that the data names: an unknown subtag
    after a lect (``pt-BR-x-sp-foo``) does not change the lect."""
    known = _known()
    for node in _ancestors(_without_extensions(standardize_lang(tag))):
        if node in known or _without_region(node) in known:
            return node
        if not private_use(node):
            return node
    return tag


def _without_region(tag: str) -> str:
    """``tag`` without a region subtag: ``eu-fr-x-zuberera`` is ``eu-x-zuberera``."""
    parts = tag.split("-")
    for index, part in enumerate(parts[1:3], start=1):
        if len(part) == 1:
            break
        if (len(part) == 2 and part.isalpha()) or (len(part) == 3 and part.isdigit()):
            return "-".join(parts[:index] + parts[index + 1:])
    return tag


def lookup_tags(tag: str) -> List[str]:
    """The tags that RFC 4647 section 3.4 (Lookup) tries for ``tag``, most
    specific first: one subtag goes at a time from the end, and a singleton
    goes with the subtag after it.

    ``pt-PT-x-lisboa-foo`` gives ``pt-PT-x-lisboa-foo``, ``pt-PT-x-lisboa``,
    ``pt-PT`` and ``pt``. The tag is standardized first."""
    tags = [standardize_lang(tag)]
    while "-" in tags[-1] and not tags[-1].lower().startswith("x-"):
        head = tags[-1].rpartition("-")[0].rstrip("-")
        if len(head.rpartition("-")[2]) == 1:
            head = head.rpartition("-")[0].rstrip("-")
        if not head:
            break
        tags.append(head)
    return tags


def lect_steps(a: str, b: str) -> Optional[int]:
    """Steps between two tags in the lect tree, or ``None`` when they do not meet."""
    up_a = _ancestors(standardize_lang(a))
    up_b = _ancestors(standardize_lang(b))
    for steps_a, node in enumerate(up_a):
        if node in up_b:
            return steps_a + up_b.index(node)
    return None


def lect_score(desired: str, supported: str, mode: str) -> int:
    """The score :func:`~linguatag.lang_distance` adds for ``mode``, 0 to 4."""
    if mode not in LECT_MODES:
        raise ValueError(f"lects must be one of {LECT_MODES} or None, not {mode!r}")
    offered = private_use(supported)
    if private_use(desired) == offered:
        return 0
    desired = _as_known_lect(desired)
    wanted = private_use(desired)
    if wanted == offered:
        return 0
    if wanted and not offered:
        return _STANDARD_LAST if mode == "dialect" else 1
    steps = lect_steps(desired, supported)
    near = _FAR if steps is None else min(steps, _FAR)
    if offered and not wanted:
        return 1 + near
    return near if mode == "dialect" else 1 + near
