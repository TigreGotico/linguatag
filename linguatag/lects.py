"""How near two lects are: tags that name a dialect with a private-use subtag.

BCP-47 gives a private-use subtag no meaning, so ``langcodes`` ignores it:
``an-x-cheso``, ``an-x-ansotano`` and ``an`` are all at distance 0. The
orthography2ipa specs place each lect in a tree, a dialect under its language
and a sub-dialect under its dialect. ``data/lineage.json`` is that tree, cut to
what lects need (``scripts/build_lineage.py``), and the number of steps between
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

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from linguatag.standardize import standardize_lang

LECT_MODES = ("dialect", "standard")

_LINEAGE = Path(__file__).resolve().parent / "data" / "lineage.json"
_FAR = 3
_STANDARD_LAST = _FAR + 1


@lru_cache(maxsize=1)
def _parents() -> Dict[str, str]:
    return json.loads(_LINEAGE.read_text(encoding="utf-8"))["parents"]


def private_use(tag: str) -> Tuple[str, ...]:
    """The private-use subtags of ``tag``: ``("cheso",)`` for ``an-x-cheso``."""
    parts = standardize_lang(tag).lower().split("-")
    return tuple(parts[parts.index("x") + 1:]) if "x" in parts else ()


def without_private_use(tag: str) -> str:
    """``tag`` standardized, without its private-use subtags."""
    tag = standardize_lang(tag)
    base, separator, _ = tag.partition("-x-")
    return base if separator else tag


def _ancestors(tag: str) -> List[str]:
    """``tag`` and its ancestors. A lect the tree does not hold is placed
    under its own language."""
    parents = _parents()
    chain = [tag]
    while len(chain) <= len(parents):
        node = chain[-1]
        if node in parents:
            chain.append(parents[node])
        elif without_private_use(node) != node:
            chain.append(without_private_use(node))
        else:
            break
    return [node.lower() for node in chain]


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
    wanted, offered = private_use(desired), private_use(supported)
    if wanted == offered:
        return 0
    steps = lect_steps(desired, supported)
    near = _FAR if steps is None else min(steps, _FAR)
    if wanted and not offered:
        return _STANDARD_LAST if mode == "dialect" else 1
    if offered and not wanted:
        return 1 + near
    return near if mode == "dialect" else 1 + near
