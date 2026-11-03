"""Scoring the private-use subtag of a dialect."""
import json
from pathlib import Path

import pytest

import linguatag.lects as lects
from linguatag import (DEFAULT_MAX_LANGUAGE_DISTANCE, LECT_MODES, closest_lang,
                       lang_distance, lect_steps)

LINEAGE = json.loads((Path(lects.__file__).parent / "data" / "lineage.json")
                     .read_text(encoding="utf-8"))

# In the orthography2ipa specs, ar-SA-x-qassim and ar-SA-x-shamali have the
# parent ar-SA-x-najd; ar-SA-x-najd, ar-SA-x-hejaz and ar-x-gulf have the
# parent ar-x-peninsular; every an-x-* lect has the parent an.
QASSIM = "ar-SA-x-qassim"


@pytest.mark.parametrize("other,steps", [
    ("ar-SA-x-najd", 1), ("ar-SA-x-shamali", 2), ("ar-SA-x-hejaz", 3),
    ("ar-x-gulf", 3), (QASSIM, 0)])
def test_steps_follow_the_dialect_tree(other, steps):
    assert lect_steps(QASSIM, other) == steps
    assert lect_steps(other, QASSIM) == steps


def test_a_lect_the_tree_does_not_hold_sits_under_its_language():
    assert lect_steps("an-x-zzz", "an") == 1
    assert lect_steps("an-x-zzz", "an-x-cheso") == 2


def test_by_default_a_private_use_subtag_adds_nothing():
    assert lang_distance("an-x-cheso", "an-x-ansotano") == 0
    assert lang_distance("an-x-cheso", "an") == 0


def test_dialect_mode_takes_the_nearest_dialect_before_the_standard():
    assert closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="dialect") == "an-x-ansotano"
    candidates = ["ar-SA", "ar-SA-x-hejaz", "ar-SA-x-shamali", "ar-SA-x-najd"]
    assert closest_lang(QASSIM, candidates, lects="dialect") == "ar-SA-x-najd"
    assert closest_lang(QASSIM, candidates[:3], lects="dialect") == "ar-SA-x-shamali"
    assert closest_lang(QASSIM, candidates[:2], lects="dialect") == "ar-SA-x-hejaz"


def test_standard_mode_takes_the_standard_before_any_dialect():
    assert closest_lang("an-x-cheso", ["an-x-ansotano", "an"], lects="standard") == "an"
    candidates = ["ar-SA-x-hejaz", "ar-SA-x-najd", "ar-SA"]
    assert closest_lang(QASSIM, candidates, lects="standard") == "ar-SA"
    assert closest_lang(QASSIM, candidates[:2], lects="standard") == "ar-SA-x-najd"


@pytest.mark.parametrize("mode", LECT_MODES)
def test_the_exact_tag_wins_in_both_modes(mode):
    assert closest_lang("an-x-cheso", ["an", "an-x-ansotano", "an-x-cheso"], lects=mode) == "an-x-cheso"
    assert closest_lang("an", ["an-x-cheso", "an"], lects=mode) == "an"


@pytest.mark.parametrize("mode,scores", [
    ("dialect", {"an-x-ansotano": 2, "an": 4}),
    ("standard", {"an-x-ansotano": 3, "an": 1})])
def test_the_scores_are_the_documented_steps(mode, scores):
    for candidate, score in scores.items():
        assert lang_distance("an-x-cheso", candidate, lects=mode) == score


def test_a_region_still_outweighs_a_dialect():
    # es-ES-x-andalusia-e has the parent es-ES; es-419 is another region
    assert closest_lang("es-ES-x-andalusia-e", ["es-419", "es-ES-x-andalusia-w"],
                        lects="standard") == "es-ES-x-andalusia-w"


TAGS = sorted(LINEAGE["parents"]) + ["en", "pt-BR", "es-419", "ar", "arz", "eu", "an"]


@pytest.mark.parametrize("mode", LECT_MODES)
def test_a_lect_score_never_crosses_the_default_threshold(mode):
    for a in TAGS:
        for b in TAGS:
            plain, scored = lang_distance(a, b), lang_distance(a, b, lects=mode)
            assert (plain <= DEFAULT_MAX_LANGUAGE_DISTANCE) == \
                (scored <= DEFAULT_MAX_LANGUAGE_DISTANCE), (a, b)


@pytest.mark.parametrize("mode", LECT_MODES)
@pytest.mark.parametrize("max_distance", [0, 3, 5])
def test_a_lect_score_never_decides_a_match(mode, max_distance):
    for a in TAGS:
        found = closest_lang(a, TAGS, max_distance=max_distance, lects=mode)
        plain = closest_lang(a, TAGS, max_distance=max_distance)
        assert (found is None) == (plain is None), a
        if found is not None:
            assert lang_distance(a, found) <= max_distance, (a, found)


def test_a_lect_score_keeps_a_near_candidate_under_a_tight_limit():
    # es-419 is a regional difference (5); a lect score on top would exceed 5
    assert closest_lang("es-ES-x-andalusia-e", ["es-419"], max_distance=5,
                        lects="dialect") == "es-419"


@pytest.mark.parametrize("mode", LECT_MODES)
def test_both_modes_order_the_same_without_langcodes(mode, no_langcodes):
    assert closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects=mode) == \
        {"dialect": "an-x-ansotano", "standard": "an"}[mode]


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        lang_distance("an-x-cheso", "an", lects="nearest")


def test_the_table_reaches_every_lect_ancestor_it_names():
    parents = LINEAGE["parents"]
    assert LINEAGE["source"].startswith("TigreGotico/orthography2ipa@")
    assert sum("-x-" in code for code in parents) >= 190
    assert DEFAULT_MAX_LANGUAGE_DISTANCE == 10


def test_without_langcodes_a_private_use_subtag_also_adds_nothing(no_langcodes):
    assert lang_distance("an-x-cheso", "an-x-ansotano") == 0
    assert lang_distance("an-x-cheso", "an") == 0
    assert lang_distance("an-x-cheso", "es") == 100


@pytest.mark.parametrize("lect", ["ar-SA-x-najd", "ar-x-gulf", "ar-SA-x-rijal-alma"])
def test_a_four_letter_private_use_subtag_is_not_a_script(lect):
    assert lang_distance(lect, "arb") <= 5 and lang_distance(lect, "ar") <= 5
    assert closest_lang(lect, ["arb"]) == "arb"


@pytest.mark.parametrize("lect", ["ar-SA-x-najd", "ar-x-gulf", "ar-SA-x-rijal-alma"])
def test_without_langcodes_a_four_letter_private_use_subtag_is_not_a_script(lect, no_langcodes):
    assert closest_lang(lect, ["arb"]) == "arb"


@pytest.mark.parametrize("tag", ["apc-x-test", "arz-x-cair"])
def test_a_four_letter_private_use_subtag_keeps_the_arabic_cap(tag):
    assert lang_distance(tag, "arb") == lang_distance(tag.split("-x-")[0], "arb") == 5


@pytest.mark.parametrize("spelling", ["arb", "ar-001", "arb-x-zzz", "ar-x-zzz"])
def test_every_msa_spelling_is_measured_as_bare_ar(spelling):
    for candidate in ["ar-EG", "ar-MA", "ar-SA", "arz", "ar-001", "arb"]:
        assert lang_distance(spelling, candidate) == lang_distance("ar", candidate), candidate


def test_msa_with_a_private_use_subtag_prefers_msa_to_egypt():
    assert closest_lang("arb-x-zzz", ["ar-EG", "ar"]) == "ar"
    assert closest_lang("arb", ["ar-EG", "ar"]) == "ar"
