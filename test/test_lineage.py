"""Genealogy, place and period functions.

``data/metric_pairs.json`` holds the values that orthography2ipa returns for a
fixed sample of pairs (``scripts/freeze_metric_fixture.py``). It is an
independent implementation of the same arithmetic, so a linguatag value that
differs from it is a defect in one of the two. These tests never import
orthography2ipa.
"""
import json
from pathlib import Path

import pytest

import linguatag
from linguatag import (ancestors, ancestry_similarity, catalog_ids, family, family_path,
                       geographic_distance, parent, script_distance_by_name,
                       temporal_distance)

FIXTURE = json.loads((Path(__file__).parent / "data" / "metric_pairs.json").read_text(encoding="utf-8"))
METRICS = FIXTURE["metrics"]

CALLS = {
    "ancestry_similarity": ancestry_similarity,
    "ancestry_similarity_temporal": ancestry_similarity,
    "ancestry_similarity_depth_1": ancestry_similarity,
    "geographic_distance": geographic_distance,
    "geographic_distance_km": geographic_distance,
    "temporal_distance": temporal_distance,
    "temporal_distance_1500": temporal_distance,
    "script_distance_by_name": script_distance_by_name,
}


def test_the_fixture_names_its_orthography2ipa_version():
    assert FIXTURE["orthography2ipa"]
    assert set(CALLS) == set(METRICS)


#: Tags whose period has a cited correction (times.json "sources", linguatag #99).
#: The frozen o2i values do not hold for them.
CITED_PERIODS = set(json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "times.json")
                               .read_text(encoding="utf-8"))["sources"])


def _cited(name: str, tag: str) -> bool:
    if not name.startswith(("temporal", "ancestry_similarity_temporal")):
        return False
    return tag in CITED_PERIODS or any(a in CITED_PERIODS for a in ancestors(tag))


@pytest.mark.parametrize("name", sorted(METRICS))
def test_a_metric_equals_the_orthography2ipa_value_on_every_sampled_pair(name):
    metric = METRICS[name]
    assert len(metric["rows"]) >= 441
    kept = [row for row in metric["rows"] if not (_cited(name, row[0]) or _cited(name, row[1]))]
    assert len(metric["rows"]) - len(kept) <= 60
    for a, b, expected in kept:
        assert CALLS[name](a, b, **metric["kwargs"]) == expected, (name, a, b)


@pytest.mark.parametrize("tag, period", [
    ("mwl", [1600, None]), ("ca-x-valencia", [1343, None]), ("aat", [1350, None]),
    ("aae", [1450, None]), ("an-x-cheso", [1200, None]), ("acm-IQ", None), ("pt-BR", None),
])
def test_a_cited_period(tag, period):
    years = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "times.json").read_text(encoding="utf-8"))
    assert years["years"].get(tag) == period
    assert years["sources"][tag]


@pytest.mark.parametrize("name", ["ancestry_similarity", "geographic_distance", "temporal_distance"])
def test_every_moved_metric_is_sampled_on_at_least_500_pairs(name):
    assert len(METRICS[name]["rows"]) >= 500


def test_the_sample_is_not_trivial():
    values = [row[2] for row in METRICS["ancestry_similarity"]["rows"]]
    assert sum(0 < v < 1 for v in values) > 100
    assert sum(v == 1.0 for v in values) > 10
    assert any(row[2] is None for row in METRICS["geographic_distance"]["rows"])
    assert any(row[2] is None for row in METRICS["temporal_distance"]["rows"])


# The chains below are the `inherits` values of the orthography2ipa spec files,
# read by hand: pt-PT-x-porto to pt-PT to pt-PT-x-medieval, and ars-SA-x-qassim
# to ars-SA to ar-x-peninsul to arb to xpa. `ar` is a sibling of `arb` under xpa.
def test_a_portuguese_lect_runs_up_to_portuguese():
    assert parent("pt-PT-x-porto") == "pt-PT"
    assert parent("pt-PT") == "pt-PT-x-medieval"
    assert ancestors("pt-PT-x-porto")[:2] == ["pt-PT", "pt-PT-x-medieval"]
    assert family("pt-PT-x-porto").startswith("Indo-European > Italic > Romance")


def test_an_arabic_lect_runs_up_to_arabic():
    assert ancestors("ars-SA-x-qassim")[:4] == ["ars-SA", "ar-x-peninsul", "arb", "xpa"]
    assert parent("ar") == "xpa"
    assert family("ars-SA-x-qassim").startswith("Afro-Asiatic")


def test_a_chain_ends_at_a_tag_with_no_parent_and_a_tag_is_standardized():
    top = ancestors("pt-PT-x-porto")[-1]
    assert parent(top) is None
    assert parent("PT-pt-X-PORTO") == "pt-PT"


def test_an_unknown_tag_has_no_genealogy():
    assert parent("qqq-x-nothing") is None
    assert ancestors("qqq-x-nothing") == []
    assert family("qqq-x-nothing") == ""
    assert family_path("qqq-x-nothing") == ()
    assert ancestry_similarity("qqq-x-nothing", "pt-PT") == 0.0
    assert geographic_distance("qqq-x-nothing", "pt-PT") is None
    assert temporal_distance("qqq-x-nothing", "pt-PT") is None


def test_the_family_path_joins_to_the_family():
    path = family_path("pt-PT-x-porto")
    assert path[:3] == ("Indo-European", "Italic", "Romance")
    assert family("pt-PT-x-porto") == " > ".join(path)


def test_every_data_file_names_its_source_commit():
    data = Path(linguatag.__file__).parent / "data"
    for name in ("genealogy", "places", "times", "lects", "scripts"):
        source = json.loads((data / f"{name}.json").read_text(encoding="utf-8"))["source"]
        assert source.startswith("TigreGotico/orthography2ipa@") and len(source) == 28 + 40


def test_a_chain_terminates_on_a_cycle(monkeypatch):
    import linguatag._lineage as lineage
    monkeypatch.setattr(lineage, "_nodes", lambda: {"aa": {"parent": "bb"}, "bb": {"parent": "aa"}})
    assert ancestors("aa") == ["bb", "aa"]


def test_lects_hold_the_private_use_tags_of_the_genealogy_with_empty_coverage():
    lects = linguatag._bcp47._raw_data("lects.json")["lects"]
    nodes = linguatag._bcp47._raw_data("genealogy.json")["nodes"]
    assert len(lects) == 190
    assert all(tag in nodes and "-x-" in tag for tag in lects)
    assert all(set(entry) == {"name", "regions", "islands", "cities"} for entry in lects.values())
    assert all(not (e["regions"] or e["islands"] or e["cities"]) for e in lects.values())


@pytest.mark.parametrize("tag, ids", [
    # Glottolog 5.4 Indo-European tree: Brazilian Portuguese [braz1246], Valencià [vale1252].
    ("pt-BR", {"glottolog_code": "braz1246", "wikidata_qid": "Q750553"}),
    ("ca-x-valencia", {"glottolog_code": "vale1252", "wikidata_qid": "Q32641"}),
    # Glottolog has no node for Cheso (Aragonese has only four dialect children).
    ("an-x-cheso", {"glottolog_code": None, "wikidata_qid": "Q3573993"}),
    ("gl", {"glottolog_code": "gali1258", "wikidata_qid": "Q9307"}),
    ("qqq-x-nothing", {}),
])
def test_catalog_ids(tag, ids):
    assert catalog_ids(tag) == ids
