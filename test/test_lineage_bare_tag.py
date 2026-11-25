"""A bare tag whose data key carries its default region, such as gl for gl-ES."""
import linguatag as L


def test_bare_tag_reads_default_region_node():
    # orthography2ipa's gl-ES spec names this family.
    assert L.family("gl") == "Indo-European > Italic > Romance > Ibero-Romance"
    assert L.parent("gl") == L.parent("gl-ES")


def test_bare_tag_reads_default_region_place():
    assert L.geographic_distance("gl", "gl-ES") == 0.0
    assert L.ancestry_similarity("gl", "gl-ES") == 1.0
