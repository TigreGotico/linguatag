"""A bare tag whose data key carries its default region, such as gl for gl-ES."""
import linguatag as L


def test_bare_tag_reads_default_region_node():
    # orthography2ipa's gl-ES spec names this family.
    assert L.family("gl") == "Indo-European > Italic > Romance > Ibero-Romance"
    assert L.parent("gl") == L.parent("gl-ES")


def test_bare_tag_reads_default_region_place():
    assert L.geographic_distance("gl", "gl-ES") == 0.0
    assert L.ancestry_similarity("gl", "gl-ES") == 1.0


def test_a_region_with_no_node_reads_the_language():
    # bn-IN, it-CH and da-GL have no node; bn, it and da do (Glottolog beng1280, ital1282, dani1285).
    assert L.catalog_ids("bn-IN") == {"glottolog_code": "beng1280", "wikidata_qid": "Q9610"}
    assert L.catalog_ids("it-CH")["glottolog_code"] == "ital1282"
    assert L.family("da-GL") == L.family("da")


def test_a_region_with_its_own_node_keeps_it():
    assert L.catalog_ids("pt-BR") == {"glottolog_code": "braz1246", "wikidata_qid": "Q750553"}


def test_an_unknown_lect_does_not_read_the_language():
    assert L.family("pt-PT-x-nothing") == ""
