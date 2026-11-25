"""How far apart two writing systems are, from their typology.

``data/scripts.json`` holds, for each of 21 writing systems, its type, the
direction it runs in, whether it has case, how it marks vowels and the scripts
it descends from. The distance of two systems is a weighted sum of the
differences.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Tuple

from linguatag.bcp47 import _raw_data

_VOWEL_ORDER = {"full": 0, "partial": 1, "inherent": 2, "none": 3}


def script_features(name: str) -> dict:
    """The typology of the writing system ``name``, such as ``"Latin"``.
    Raises ``KeyError`` for a name that the table does not hold."""
    return {"name": name, **_raw_data("scripts.json")["scripts"][name]}


@lru_cache(maxsize=None)
def _type_distances() -> Dict[Tuple[str, str], float]:
    table = {}
    for a, b, distance in _raw_data("scripts.json")["type_distances"]:
        table[a, b] = table[b, a] = distance
    return table


def script_distance(a: dict, b: dict) -> float:
    """The distance of two writing systems, from 0.0 to 1.0, given as the
    feature dicts of :func:`script_features`.

    The weights are 0.40 for the type, 0.15 for the direction, 0.15 for the
    vowel marking, 0.05 for case and 0.25 for the scripts that the two do not
    share as ancestors.
    """
    if a["name"] == b["name"]:
        return 0.0
    type_d = 0.0 if a["type"] == b["type"] else _type_distances().get((a["type"], b["type"]), 0.5)
    direction_d = 0.0 if a["directionality"] == b["directionality"] else 1.0
    vowel_d = abs(_VOWEL_ORDER[a["vowel_marking"]] - _VOWEL_ORDER[b["vowel_marking"]]) / 3.0
    case_d = 0.0 if a["has_case"] == b["has_case"] else 1.0
    roots_a, roots_b = set(a["ancestor_scripts"]), set(b["ancestor_scripts"])
    shared = len(roots_a & roots_b) / len(roots_a | roots_b) if roots_a and roots_b else 0.0
    combined = 0.40 * type_d + 0.15 * direction_d + 0.15 * vowel_d + 0.05 * case_d + 0.25 * (1.0 - shared)
    return min(max(combined, 0.0), 1.0)


def script_distance_by_name(a: str, b: str) -> float:
    """:func:`script_distance` for two writing systems given by name. Raises
    ``KeyError`` for a name that the table does not hold."""
    return script_distance(script_features(a), script_features(b))
