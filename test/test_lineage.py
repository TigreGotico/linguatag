"""Genealogy, place and period functions.

Each expected value comes from the cited data and the formula in the docstring
of the function, worked out by hand.
"""
import json
import math
from pathlib import Path

import pytest

import linguatag
from linguatag import (ancestors, ancestry_similarity, catalog_ids, family, family_path,
                       geographic_distance, parent, script_distance_by_name,
                       temporal_distance)


@pytest.mark.parametrize("a, b, expected", [
    # pt-PT and pt-BR share pt-PT-x-medieval: weights 1.0 and 0.85.
    ("pt-PT", "pt-BR", 0.85),
    # gl-ES hangs from roa-x-galaico-pt with 0.75; pt-PT reaches it through
    # pt-PT-x-medieval with 1.0 * 1.0.
    ("pt-PT", "gl", 0.75),
    ("pt-BR", "gl", 0.85 * 0.75),
    ("pt-PT", "pt-PT", 1.0),
])
def test_ancestry_similarity_multiplies_the_cited_weights(a, b, expected):
    assert ancestry_similarity(a, b) == pytest.approx(expected)


@pytest.mark.parametrize("near, far", [
    # Catalan and Spanish share Latin; Catalan and English share only Proto-Indo-European.
    (("ca", "es"), ("ca", "en")),
    (("pt", "es"), ("pt", "de")),
    (("en", "de"), ("en", "hi")),
])
def test_a_shared_branch_is_nearer_than_a_shared_family(near, far):
    assert ancestry_similarity(*near) > ancestry_similarity(*far)


@pytest.mark.parametrize("a, b, expected", [
    # Start years (times.json sources): mwl 1609, aae 1450, ca-x-valencia 1343,
    # all still spoken, so each period ends at the reference year 2025.
    ("mwl", "aae", 1 - (2025 - 1609) / (2025 - 1450)),
    ("mwl", "ca-x-valencia", 1 - (2025 - 1609) / (2025 - 1343)),
    ("aae", "ca-x-valencia", 1 - (2025 - 1450) / (2025 - 1343)),
    # Etruscan -700 to 100 and Latin -100 to 600 share 200 of 1300 years.
    ("ett", "la", 1 - 200 / 1300),
])
def test_temporal_distance_is_one_minus_the_shared_share(a, b, expected):
    assert temporal_distance(a, b) == pytest.approx(expected)


def test_temporal_distance_before_a_start_year_is_one():
    # With reference year 1500, mwl (1609) has not started: no shared years.
    assert temporal_distance("mwl", "aae", reference_year=1500) == 1.0


def test_geographic_distance_by_the_spherical_law_of_cosines():
    # A second formula for the great circle, on the points of places.json.
    places = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "places.json")
                        .read_text(encoding="utf-8"))["places"]
    (lat1, lon1), (lat2, lon2) = (map(math.radians, places[t]) for t in ("pt-PT", "es-ES"))
    angle = math.acos(math.sin(lat1) * math.sin(lat2)
                      + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    assert geographic_distance("pt-PT", "es-ES", normalize=False) == pytest.approx(6371.0088 * angle)
    assert geographic_distance("pt-PT", "es-ES") == pytest.approx(angle / math.pi)
    assert geographic_distance("pt-PT", "pt-PT") == 0.0


def test_script_distance_of_latin_and_cyrillic():
    # The two differ only in their ancestor scripts: they share Greek and
    # Phoenician of Etruscan, Greek and Phoenician, so 0.25 * (1 - 2/3).
    assert script_distance_by_name("Latin", "Cyrillic") == pytest.approx(0.25 / 3)
    assert script_distance_by_name("Latin", "Latin") == 0.0


@pytest.mark.parametrize("tag, period", [
    ("mwl", [1609, None]), ("ca-x-valencia", [1343, None]), ("aat", [1350, None]),
    ("aae", [1450, None]), ("an-x-cheso", [1200, None]), ("acm-IQ", None), ("pt-BR", None),
    ("pt-PT", [1214, None]), ("es", [900, None]), ("fr", [842, None]), ("it", [960, None]), ("de", [790, None]),
    ("nl", [510, None]), ("da", [1241, None]), ("bn", [950, None]), ("hi", [1803, None]), ("mwr", [1400, None]),
    ("kab", [1857, None]), ("es-CO", [1867, None]),
])
def test_a_cited_period(tag, period):
    years = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "times.json").read_text(encoding="utf-8"))
    assert years["years"].get(tag) == period
    assert years["sources"][tag]


@pytest.mark.parametrize("tag, parent, cited", [
    ("pt-PT-x-braga", "pt-PT-x-minho", "minhoto central"), ("ca-x-balear", "ca-x-medieval", "Recasens"),
    ("pt-UY", "pt-BR", "sul-rio-grandense"), ("ar-IQ-x-qeltu", "ayp", "tigr1278"), ("ayp", "ar-x-mashriqi", "east2729"),
    ("pt-AO", "pt-PT", "norma padrão europeia"), ("pt-MZ", "pt-PT", "a norma de referência em Moçambique"),
    ("pt-PT-x-alfena", "pt-PT", "Douro Litoral"), ("pt-PT-x-viana", "pt-PT", "Baixo-Minho"),
    ("pt-PT-x-coimbra", "pt-PT", "a montante de Coimbra"), ("pt-PT-x-terceira", "pt-PT", "Terceira Island"),
    ("pt-BR-x-mg", "pt-BR", "sub-falar mineiro"), ("pt-BR-x-ce", "pt-BR", "Ceará (Fortaleza)"),
    ("pt-BR-x-paraiba", "pt-BR", "Paraíba (João Pessoa)"), ("pt-BR-x-recife", "pt-BR", "dialeto recifense"),
    ("mwr", "inc-x-owr", "Çaurasena Apabhraṃça"), ("rwr", "mwr", "macrolanguages"),
    ("ca-x-nord", "ca-x-medieval", "només tenia dos dialectes"), ("ca-x-occident", "ca-x-medieval", "només tenia dos dialectes"),
    ("ar-TR-x-kinderib", "ayp", "Untergruppe der Mardin-Dialekte"), ("pt-BR", "pt-PT-x-medieval", "aportou ao Brasil"),
    ("pt-PT-x-medieval", "roa-x-galaico-pt", "virada do século 14 para o século 15"),
    ("pt-PT", "pt-PT-x-medieval", "Teyssier inova ao considerar"),
    ("dhd", "mwr", "Dhundari"), ("mtr", "mwr", "Mewari"), ("swv", "mwr", "Shekhawati"), ("wry", "mwr", "Merwari"),
])
def test_a_lineage_edge_names_its_source(tag, parent, cited):
    data = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "genealogy.json").read_text(encoding="utf-8"))
    assert data["nodes"][tag]["parent"] == parent
    assert cited in data["sources"][tag]


def test_every_edge_source_belongs_to_a_node():
    data = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "genealogy.json").read_text(encoding="utf-8"))
    assert set(data["sources"]) <= set(data["nodes"])
    assert all(data["sources"].values())


# The chains below are the `inherits` values of the orthography2ipa spec files,
# read by hand: pt-PT-x-porto to pt-PT-x-minho to pt-PT to pt-PT-x-medieval, and ars-SA-x-qassim
# to ars-SA to ar-x-peninsul to arb to xpa. `ar` is a sibling of `arb` under xpa.
def test_a_portuguese_lect_runs_up_to_portuguese():
    assert parent("pt-PT-x-porto") == "pt-PT-x-minho"
    assert parent("pt-PT") == "pt-PT-x-medieval"
    assert ancestors("pt-PT-x-porto")[:3] == ["pt-PT-x-minho", "pt-PT", "pt-PT-x-medieval"]
    assert family("pt-PT-x-porto").startswith("Indo-European > Italic > Romance")


def test_an_arabic_lect_runs_up_to_arabic():
    assert ancestors("ars-SA-x-qassim")[:4] == ["ars-SA", "ar-x-peninsul", "arb", "xpa"]
    assert parent("ar") == "xpa"
    assert family("ars-SA-x-qassim").startswith("Afro-Asiatic")


def test_a_chain_ends_at_a_tag_with_no_parent_and_a_tag_is_standardized():
    top = ancestors("pt-PT-x-porto")[-1]
    assert parent(top) is None
    assert parent("PT-pt-X-PORTO") == "pt-PT-x-minho"


def test_an_unknown_tag_has_no_genealogy():
    assert parent("qqq-x-nothing") is None
    assert ancestors("qqq-x-nothing") == []
    assert family("qqq-x-nothing") == ""
    assert family_path("qqq-x-nothing") == ()
    assert ancestry_similarity("qqq-x-nothing", "pt-PT") == 0.0
    assert geographic_distance("qqq-x-nothing", "pt-PT") is None
    assert temporal_distance("qqq-x-nothing", "pt-PT") is None


def test_an_isolate_has_the_isolate_category():
    assert family("sux") == "Isolate" and family_path("sux") == ()


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
    assert len(lects) == 189
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
    # Glottolog 5.4: Etruscan [etru1241], Sumerian [sume1241]; Wikidata Q35726 is Etruscan, Q36790 Sumerian.
    ("ett", {"glottolog_code": "etru1241", "wikidata_qid": "Q35726"}),
    ("sux", {"glottolog_code": "sume1241", "wikidata_qid": "Q36790"}),
    # ISO 639-3 etr is Edolo, a language of Papua New Guinea, so it has no Etruscan node.
    ("etr", {}),
    # Wikidata Q56312 is the Marwari macrolanguage (P220 mwr); Glottolog has no node for it.
    ("mwr", {"glottolog_code": None, "wikidata_qid": "Q56312"}),
    ("qqq-x-nothing", {}),
])
def test_catalog_ids(tag, ids):
    assert catalog_ids(tag) == ids


@pytest.mark.parametrize("tag, base", [
    ("ks-Arab", "ks"), ("sr-Latn-RS", "sr-RS"), ("sr-Cyrl", "sr"), ("pa-Arab", "pa"),
])
def test_a_script_subtag_reads_the_node_of_its_language(tag, base):
    assert catalog_ids(tag) == catalog_ids(base) != {}
    assert parent(tag) == parent(base)


@pytest.mark.parametrize("tag, ids", [
    ("ajt", {"glottolog_code": "tuni1259", "wikidata_qid": "Q56240"}),
    ("aeb-x-judeo", {"glottolog_code": "jude1263", "wikidata_qid": "Q56597"}),
    ("cnr", {"glottolog_code": "mont1282", "wikidata_qid": "Q8821"}),
    ("oji", {"glottolog_code": "ojib1241", "wikidata_qid": "Q33875"}),
    ("swc", {"glottolog_code": "cong1236"}),
    ("yol", {"glottolog_code": "midd1317", "wikidata_qid": "Q36395"}),
    ("enm-x-yola", {"glottolog_code": "yola1237", "wikidata_qid": "Q56395"}),
])
def test_a_deprecated_code_reads_the_ids_of_its_preferred_tag(tag, ids):
    assert catalog_ids(tag) == ids


def test_tunisian_arabic_is_not_the_judeo_tunisian_node():
    assert parent("aeb") == "ar-x-maghrebi"
    assert parent("aeb-x-judeo") == "aeb-TN"


@pytest.mark.parametrize("tag", ["pt-PT-x-braga", "pt-PT-x-porto"])
def test_braga_and_porto_are_minhoto_varieties(tag):
    # Paiva Boléo & Santos Silva 1959, via Cintra 1971: Braga is inside minhoto
    # central and Porto inside baixo-minhoto, both inside the Minhoto dialect.
    assert parent(tag) == "pt-PT-x-minho"


@pytest.mark.parametrize("tag, stage", [
    ("hi", "psu-x-apabhram"), ("bn", "inc-x-magadhi-apabhram"), ("mwr", "inc-x-owr"), ("gu", "inc-x-owr"),
    ("as", "inc-x-magadhi-apabhram"), ("or", "inc-x-magadhi-apabhram"),
    ("mr", "pmh"), ("pa", "inc-x-takka"),
])
def test_an_indo_aryan_language_descends_through_a_middle_stage(tag, stage):
    assert parent(tag) == stage
    assert "sa" in ancestors(tag)


def test_two_indo_aryan_languages_are_nearer_than_two_branches():
    assert ancestry_similarity("hi", "bn") > 2 * ancestry_similarity("hi", "en")


@pytest.mark.parametrize("tag", ["dhd", "mtr", "swv", "wry"])
def test_a_marwari_member_is_indo_aryan(tag):
    assert parent(tag) == "mwr"
    assert family_path(tag) == ("Indo-European", "Indo-Iranian", "Indo-Aryan")


@pytest.mark.parametrize("other", ["as", "or"])
def test_a_magadhi_language_is_nearer_to_bengali_than_hindi_is(other):
    assert ancestry_similarity("bn", other) > ancestry_similarity("bn", "hi")


def test_pmh_is_maharastri_prakrit():
    data = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "genealogy.json").read_text(encoding="utf-8"))
    assert "Māhārāṣṭri Prākrit" in data["sources"]["pmh"]
    assert parent("bn") == "inc-x-magadhi-apabhram"


@pytest.mark.parametrize("other", ["pa", "mr"])
def test_an_inner_indo_aryan_language_is_nearer_to_hindi_than_english_is(other):
    assert ancestry_similarity("hi", other) > 2 * ancestry_similarity("hi", "en")


def test_a_retired_variety_has_no_node():
    # ISO 639-3 retired bbz in 2020, and Glottolog retired baba1273 as non-existent.
    assert parent("ar-TD-x-babalia") is None
    assert family("ar-TD-x-babalia") == ""


def test_every_lineage_edge_has_a_source():
    data = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "genealogy.json").read_text(encoding="utf-8"))
    assert not [tag for tag, source in data["sources"].items() if source.startswith("NOT FOUND")]


def test_one_node_holds_north_mesopotamian_arabic():
    nodes = json.loads((Path(__file__).parent.parent / "linguatag" / "data" / "genealogy.json").read_text(encoding="utf-8"))["nodes"]
    assert [tag for tag, node in nodes.items() if node.get("glottolog_code") == "nort3142"] == ["ayp"]
