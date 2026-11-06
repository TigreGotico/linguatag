"""Scoring the private-use subtag of a dialect."""
import json
from pathlib import Path

import pytest

import linguatag.lects as lects
from linguatag import (DEFAULT_MAX_LANGUAGE_DISTANCE, LECT_MODES, closest_lang,
                       lang_distance, lect_steps)

LINEAGE = json.loads((Path(lects.__file__).parent / "data" / "lineage.json")
                     .read_text(encoding="utf-8"))

# In the orthography2ipa specs, ars-SA-x-qassim and ars-SA-x-shamali have the
# parent ars-SA (Najdi); ars-SA, ayn-YE and afb have the parent ar-x-peninsul;
# afb-SA-x-sharqiya has the parent afb; every an-x-* lect has the parent an.
QASSIM = "ars-SA-x-qassim"


@pytest.mark.parametrize("other,steps", [
    ("ars-SA", 1), ("ars-SA-x-shamali", 2), ("ar-x-peninsul", 2),
    ("ayn-YE", 3), ("afb-SA-x-sharqiya", 4), (QASSIM, 0)])
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
    assert closest_lang(QASSIM, ["ars-SA", "ars-SA-x-shamali"], lects="dialect") \
        == "ars-SA-x-shamali"


def test_standard_mode_takes_the_standard_before_any_dialect():
    assert closest_lang("an-x-cheso", ["an-x-ansotano", "an"], lects="standard") == "an"
    assert closest_lang(QASSIM, ["ars-SA-x-shamali", "ars-SA"], lects="standard") == "ars-SA"


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
    # es-ES-x-andalusi-e has the parent es-ES; es-419 is another region
    assert closest_lang("es-ES-x-andalusi-e", ["es-419", "es-ES-x-andalusi-w"],
                        lects="standard") == "es-ES-x-andalusi-w"


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
    assert closest_lang("es-ES-x-andalusi-e", ["es-419"], max_distance=5,
                        lects="dialect") == "es-419"


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        lang_distance("an-x-cheso", "an", lects="nearest")


def test_the_table_reaches_every_lect_ancestor_it_names():
    parents = LINEAGE["parents"]
    assert LINEAGE["source"].startswith("TigreGotico/orthography2ipa@")
    assert sum("-x-" in code for code in parents) >= 180
    assert DEFAULT_MAX_LANGUAGE_DISTANCE == 10


def test_every_subtag_in_the_table_is_one_to_eight_alphanumerics():
    # BCP 47 section 2.1: a subtag is 1 to 8 alphanumeric characters
    codes = set(LINEAGE["parents"]) | set(LINEAGE["parents"].values())
    malformed = sorted(code for code in codes
                       if not all(1 <= len(subtag) <= 8 and subtag.isascii()
                                  and subtag.isalnum()
                                  for subtag in code.split("-")))
    assert malformed == []


@pytest.mark.parametrize("lect", ["ar-SA-x-najd", "ar-x-gulf", "ar-SA-x-rijal-alma"])
def test_a_four_letter_private_use_subtag_is_not_a_script(lect):
    assert lang_distance(lect, "arb") <= 5 and lang_distance(lect, "ar") <= 5
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


ARABIC_CATALOGUE = ["ar-EG", "ar-x-maghrebi", "ar-x-mashriqi", "arb"]


def test_standard_mode_picks_msa_over_the_arabic_clades():
    assert closest_lang("arb-x-zzz", ARABIC_CATALOGUE, lects="standard") == "arb"


@pytest.mark.parametrize("catalogue", [ARABIC_CATALOGUE, ARABIC_CATALOGUE[::-1]])
def test_default_mode_ties_msa_and_the_clades_on_the_first_candidate(catalogue):
    tied = [tag for tag in catalogue if lang_distance("arb-x-zzz", tag) == 0]
    assert tied == [tag for tag in catalogue if tag != "ar-EG"]
    assert closest_lang("arb-x-zzz", catalogue) == tied[0]
