"""`standardize_lang` reaches the standard form in one call."""
import random
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import pytest
from langcodes import standardize_tag
from langcodes.data_dicts import (DEFAULT_SCRIPTS, LANGUAGE_ALPHA3, LANGUAGE_REPLACEMENTS,
                                  TERRITORY_REPLACEMENTS)

from linguatag import standardize_lang

# Every spec stem of orthography2ipa 2c048be, every voice language of phoonnx
# a8da06c, every entry of the region and lineage tables with its region, and
# hand-picked edge cases.
TAG_SET = (Path(__file__).parent / "data" / "tag_set.txt").read_text(encoding="utf-8").split("\n")[:-1]

FUZZ_ALPHABET = "abzXYé中-_0129 .\n"
FUZZ_HEADS = ["zh", "yue", "cmn", "ar", "arb", "arz", "tl", "tgl", "fil", "en", "pt", "x",
              "i", "und", "sgn", "", "pga", "acy"]

# What follows a tag whose standard form differs from its spelling: a subtag
# that the first spelling cannot hold can fit the standard form.
REMAINDERS = ["ex", "us", "GB", "latn", "cyrl", "hant", "arab", "1996", "rozaj", "x-foo",
              "voice-low", "HiuMaanNeural", "verylongsubtag", "abc", "u-ca-gregory",
              "cyrl-us", "us-cyrl", "ex-1996"]


def _head_rewrites(rewrites: dict) -> dict:
    """Which leading subtags each leading subtag of `rewrites` turns into.

    A rule such as `zh-guoyu` to `zh` keeps its leading subtag, and it rewrites
    a whole tag once, so it adds no edge.
    """
    graph = {}
    for source, target in rewrites.items():
        source, target = source.split("-")[0].lower(), target.split("-")[0].lower()
        if source != target:
            graph.setdefault(source, set()).add(target)
    return graph


def _fuzz(count: int) -> list:
    rng = random.Random(3)
    tags = []
    for _ in range(count):
        tail = "".join(rng.choice(FUZZ_ALPHABET) for _ in range(rng.randint(0, 12)))
        tags.append(rng.choice(FUZZ_HEADS) + rng.choice(["-", "_", ""]) + tail
                    if rng.random() < .8 else tail)
    return tags


def _rewritten_tags() -> list:
    heads = [*LANGUAGE_REPLACEMENTS, *LANGUAGE_ALPHA3,
             *(f"{language}-{script}" for language, script in DEFAULT_SCRIPTS.items()),
             *(f"en-{region}" for region in TERRITORY_REPLACEMENTS)]
    return [f"{head}-{remainder}" for head in heads for remainder in REMAINDERS]


def _not_stable(tags) -> list:
    return sorted(tag for tag in set(tags)
                  if standardize_lang(standardize_lang(tag)) != standardize_lang(tag))


def test_the_tag_set_is_whole():
    assert len(TAG_SET) == 8669
    assert "" in TAG_SET and "zh-HK-HiuMaanNeural" in TAG_SET


def test_the_tag_set_is_stable():
    assert _not_stable(TAG_SET) == []


def test_fuzz_inputs_are_stable():
    assert _not_stable(_fuzz(240_000)) == []


def test_a_remainder_after_a_rewritten_tag_is_stable():
    assert _not_stable(_rewritten_tags()) == []


@pytest.mark.parametrize("tag, standard", [
    ("en-Latn-Latn-Latn", "en"),
    ("en-Latn-Latn-Latn-Latn-Latn", "en"),
    ("SGN-FX-QA-BTJ-PT", "fsl-QA-btj-pt"),
    ("sgn-DD", "gsg"),
    ("sgn-FX", "fsl"),
    ("SGN-276", "gsg"),
    ("sgn-250", "fsl"),
])
def test_a_tag_that_needs_several_rewrites_reaches_the_standard_form(tag, standard):
    assert standardize_lang(tag) == standard
    assert standardize_lang(standard) == standard


@pytest.mark.parametrize("rewrites, source, target", [(LANGUAGE_REPLACEMENTS, "iw", "he"),
                                                      (TERRITORY_REPLACEMENTS, "dd", "de")])
def test_the_rewrite_rules_of_langcodes_hold_no_cycle(rewrites, source, target):
    """`standardize_lang` loops to a fixed point, and only a cycle denies it one.

    The `langcodes` floor has no ceiling, so this test is what reports a cycle
    in a later release of its data.
    """
    graph = _head_rewrites(rewrites)
    assert target in graph[source]
    TopologicalSorter(graph).prepare()


@pytest.mark.parametrize("rewrites, planted", [
    (LANGUAGE_REPLACEMENTS, {"he": "iw"}),
    (LANGUAGE_REPLACEMENTS, {"he": "qaa", "qaa-x-foo": "iw"}),
    (TERRITORY_REPLACEMENTS, {"de": "DD"}),
])
def test_the_cycle_check_finds_a_planted_cycle(rewrites, planted):
    with pytest.raises(CycleError):
        TopologicalSorter(_head_rewrites({**rewrites, **planted})).prepare()


def test_none_is_stable():
    assert standardize_lang(standardize_lang(None)) == standardize_lang(None) == ""


@pytest.mark.parametrize("tag, rewritten", [
    ("i-klingon-ex", "tlh-ex"),
    ("art-lojban-ex", "jbo-ex"),
    ("aa-saaho-latn", "ssy-latn"),
    ("i-navajo-us", "nv-us"),
    ("en-Latn-cyrl", "en-cyrl"),
])
def test_a_remainder_that_fits_the_standard_form_is_standardized(tag, rewritten):
    assert standardize_lang(tag) == standardize_tag(rewritten)
