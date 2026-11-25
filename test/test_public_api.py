"""The tag parser is part of the public API."""
import pytest

import linguatag


def test_parse_tag_reads_the_subtags():
    tag = linguatag.parse_tag("pt_latn_pt")
    assert (tag.language, tag.script, tag.region, tag.whole) == ("pt", "Latn", "PT", None)
    assert isinstance(tag, linguatag.LanguageTag)


def test_parse_tag_reads_a_private_use_tag_whole():
    assert linguatag.parse_tag("x-foo").whole == "x-foo"


def test_parse_tag_refuses_a_malformed_tag():
    with pytest.raises(linguatag.LanguageTagError):
        linguatag.parse_tag("pt--PT")


def test_the_parser_names_are_exported():
    assert {"parse_tag", "LanguageTag", "LanguageTagError"} <= set(linguatag.__all__)
