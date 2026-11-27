"""Where a language comes from, where it is spoken and when.

``data/genealogy.json`` holds a parent, weighted ancestors, a family and a
clade flag for each language and lect.
``data/places.json`` and ``data/times.json`` hold a point and a period for
most of them. ``parent``, ``ancestors``, ``family`` and ``family_path`` read
the genealogy. ``ancestry_similarity``, ``geographic_distance`` and
``temporal_distance`` measure two tags against it.

A tag that the data does not hold has no parent, no family, no ancestors and
no place or period, so the metrics answer ``0.0`` or ``None`` for it.
"""
from __future__ import annotations

import math
from collections import deque
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from linguatag._bcp47 import _raw_data, parse as parse_tag
from linguatag._regions import with_default_region
from linguatag._standardize import standardize_lang

_EARTH_RADIUS_KM = 6371.0088


def _nodes() -> Dict[str, dict]:
    return _raw_data("genealogy.json")["nodes"]


@lru_cache(maxsize=4096)
def _key(tag: str) -> str:
    """The data key of ``tag``. The data keys a language by its default-region
    tag when its spec carries a region, so ``gl`` reads ``gl-ES``. A script
    does not change the language, so ``ks-Arab`` reads ``ks`` when it has no
    node of its own. A region with no node of its own reads the language, so ``sr-RS``
    reads ``sr`` and ``bn-IN`` reads ``bn``."""
    tag = standardize_lang(tag)
    if tag in _nodes():
        return tag
    regional = with_default_region(tag)
    if regional in _nodes():
        return regional
    parsed = parse_tag(tag)
    if parsed.script:
        return _key(tag.replace(f"-{parsed.script}", "", 1))
    if parsed.region and not (parsed.variants or parsed.private or parsed.extensions):
        language = _key(parsed.language)
        if language in _nodes():
            return language
    return tag


def parent(tag: str) -> Optional[str]:
    """The genealogical parent of ``tag``, or ``None`` at the top of a tree."""
    return _nodes().get(_key(tag), {}).get("parent")


def ancestors(tag: str) -> List[str]:
    """The parent of ``tag``, its parent and so on, nearest first. Clade nodes
    such as ``x-clade-iberrom`` are part of the chain."""
    chain, node = [], parent(tag)
    while node and node not in chain:
        chain.append(node)
        node = parent(node)
    return chain


def family(tag: str) -> str:
    """The family of ``tag`` as a path, such as ``"Indo-European > Italic >
    Romance"``, or ``""`` when it has none."""
    return _nodes().get(_key(tag), {}).get("family", "")


def family_path(tag: str) -> Tuple[str, ...]:
    """The clade names above ``tag``, broadest first."""
    return tuple(_nodes().get(_key(tag), {}).get("family_path", ()))


def catalog_ids(tag: str) -> Dict[str, Optional[str]]:
    """The ids of ``tag`` in other catalogs: ``glottolog_code`` and
    ``wikidata_qid``. A key with the value ``None`` means that the catalog has
    no entry for the variety. A key that is absent means that no one checked."""
    node = _nodes().get(_key(tag), {})
    return {k: node[k] for k in ("glottolog_code", "wikidata_qid") if k in node}


def _data_ancestors(tag: str) -> List[Tuple[str, float]]:
    """The weighted ancestors of ``tag`` with each clade node replaced by the
    nearest ancestor above it that is not a clade. A clade has no phonology and
    adds nothing to a genealogical distance."""
    nodes = _nodes()
    node = nodes[tag]
    links = node.get("ancestors") or ([[node["parent"], "parent", 1.0]] if "parent" in node else [])
    resolved = []
    for code, _, weight in links:
        target, seen = code, set()
        while target and target not in seen:
            seen.add(target)
            if target not in nodes:
                target = None
                break
            if not nodes[target].get("clade"):
                break
            target = nodes[target].get("parent")
        if target:
            resolved.append((target, weight))
    return resolved


def _period(tag: str) -> Optional[List[Optional[int]]]:
    return _raw_data("times.json")["years"].get(tag)


def _temporal_decay(ancestor: str, descendant: str, halflife: float) -> float:
    """The factor ``exp(-gap / halflife)`` for the years between the end of an
    ancestor and the start of its descendant, or 1.0 when either has no period."""
    old, new = _period(ancestor), _period(descendant)
    if old is None or new is None:
        return 1.0
    gap = new[0] - (old[1] if old[1] is not None else old[0])
    return 1.0 if gap <= 0 else math.exp(-gap / halflife)


@lru_cache(maxsize=256)
def _weights(tag: str, max_depth: int, temporal: bool, halflife: float) -> Dict[str, float]:
    """The best path weight from ``tag`` to each of its ancestors: the product
    of the weights along the path, the largest over all paths."""
    nodes, result = _nodes(), {}
    queue = deque([(tag, 1.0, 0, tag)])
    while queue:
        current, weight, depth, descendant = queue.popleft()
        if depth > max_depth or current not in nodes:
            continue
        for code, link_weight in _data_ancestors(current):
            decay = _temporal_decay(code, descendant, halflife) if temporal and code in nodes else 1.0
            path = weight * link_weight * decay
            if code not in result or path > result[code]:
                result[code] = path
                queue.append((code, path, depth + 1, code if code in nodes else descendant))
    return result


def ancestry_similarity(a: str, b: str, max_depth: int = 10,
                        temporal_decay: bool = False, decay_halflife: float = 1000.0) -> float:
    """How strongly two tags are linked by descent, from 0.0 to 1.0.

    1.0 is the same tag, about 0.7 to 0.9 a dialect of the same language, 0.4
    to 0.7 the same branch, 0.2 to 0.4 the same family and 0.0 no traceable
    link. The weights are those of the ancestors in ``genealogy.json``.
    ``max_depth`` counts the levels above each tag that the trace follows.
    With ``temporal_decay``, a path loses weight with the years between an
    ancestor and its descendant.
    """
    a, b = _key(a), _key(b)
    if a == b:
        return 1.0
    paths_a = _weights(a, max_depth, temporal_decay, decay_halflife)
    paths_b = _weights(b, max_depth, temporal_decay, decay_halflife)
    shared = paths_a.keys() & paths_b.keys()
    best = max((paths_a[c] * paths_b[c] for c in shared), default=0.0)
    if a in paths_b:
        return max(paths_b[a], best)
    if b in paths_a:
        return max(paths_a[b], best)
    return min(best, 1.0)


def geographic_distance(a: str, b: str, normalize: bool = True) -> Optional[float]:
    """The great-circle distance between the points of two tags.

    The result is in kilometres, or with ``normalize`` a share of half the
    circumference of the Earth, from 0.0 to 1.0. It is ``None`` when either
    tag has no point. A point stands for an area, so the number says most about
    dialects of one language and little about a language that is spoken in
    several continents.
    """
    places = _raw_data("places.json")["places"]
    here, there = places.get(_key(a)), places.get(_key(b))
    if here is None or there is None:
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, (*here, *there))
    haversine = (math.sin((lat2 - lat1) / 2) ** 2
                 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    km = 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))
    return km / (math.pi * _EARTH_RADIUS_KM) if normalize else km


def temporal_distance(a: str, b: str, reference_year: int = 2025) -> Optional[float]:
    """One minus the share of time that two tags are both spoken, from 0.0 to 1.0.

    A tag with no end year is spoken until ``reference_year``. The result is
    ``None`` when either tag has no period.
    """
    first, second = _period(_key(a)), _period(_key(b))
    if first is None or second is None:
        return None
    start_a, end_a = first[0], reference_year if first[1] is None else first[1]
    start_b, end_b = second[0], reference_year if second[1] is None else second[1]
    span = max(end_a, end_b) - min(start_a, start_b)
    if span <= 0:
        return 0.0
    return 1.0 - max(0, min(end_a, end_b) - max(start_a, start_b)) / span
