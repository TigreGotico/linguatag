"""The default region of a tag that names none."""
import json
from pathlib import Path

import pytest
from langcodes import Language

import linguatag.matching as matching
from linguatag import (MOTHERLAND, closest_lang, default_region, lang_distance,
                       with_default_region)

TABLE = json.loads((Path(matching.__file__).parent / "data" / "likely_regions.json")
                   .read_text(encoding="utf-8"))["regions"]


@pytest.mark.parametrize("language,region", [("en", "GB"), ("pt", "PT"), ("ur", "IN")])
def test_a_bare_tag_defaults_to_its_motherland(language, region):
    assert default_region(language) == region


def test_every_override_differs_from_cldr():
    """An override that CLDR already gives says nothing."""
    for language, region in MOTHERLAND.items():
        assert Language.get(language).maximize().territory != region, language
        assert TABLE[language] != region


@pytest.mark.parametrize("language", ["es", "fr", "de", "it", "zh", "ja", "ar", "yue", "bn"])
def test_without_an_override_the_cldr_region_stands(language):
    assert language not in MOTHERLAND
    assert default_region(language) == Language.get(language).maximize().territory


def test_the_table_is_the_cldr_likely_region_of_every_tag_without_one():
    assert len(TABLE) == 739
    for tag, region in TABLE.items():
        assert "-" not in tag or len(tag.split("-")[1]) == 4, tag
        assert Language.get(tag).maximize().territory == region, tag
    assert not {"ZZ", "001"} & set(TABLE.values())


def test_a_tag_with_a_region_keeps_it():
    assert default_region("pt-BR") == "BR"
    assert default_region("en_us") == "US"
    assert default_region("es-419") == "419"
    assert default_region("sr-Latn-RS") == "RS"


def test_a_script_uses_its_own_entry_before_its_language():
    assert default_region("zh-Hant") == "TW"
    assert default_region("zh") == "CN"
    assert "sr-Latn" not in TABLE
    assert default_region("sr-Latn") == "RS"


def test_a_language_with_no_region_has_none():
    assert default_region("yi") is None
    assert default_region("qaa") is None


def test_case_and_underscores_do_not_matter():
    assert default_region("EN") == "GB"
    assert default_region("zh_hant") == "TW"


@pytest.mark.parametrize("tag,expected", [
    ("en", "en-GB"),
    ("pt", "pt-PT"),
    ("es", "es-ES"),
    ("zh-Hant", "zh-Hant-TW"),
    ("gl-x-central", "gl-ES-x-central"),
    ("pt-BR", "pt-BR"),
    ("ext-PT-x-barrancos", "ext-PT-x-barrancos"),
    ("yi", "yi"),
    ("x-klingon", "x-klingon"),
    ("", ""),
])
def test_with_default_region(tag, expected):
    assert with_default_region(tag) == expected


@pytest.mark.parametrize("langcodes_present", [True, False])
def test_a_bare_tag_is_its_motherland_when_measured(langcodes_present, monkeypatch):
    if not langcodes_present:
        monkeypatch.setattr(matching, "_langcodes_distance", lambda a, b: None)
    assert lang_distance("en", "en-GB") == 0
    assert lang_distance("en", "en-US") > 0
    assert lang_distance("ur", "ur-IN") == 0
    assert lang_distance("ur", "ur-PK") > 0
    assert closest_lang("en", ["en-US", "en-GB"]) == "en-GB"


def test_a_bare_request_still_reaches_another_region():
    assert closest_lang("en", ["en-US"]) == "en-US"
    assert closest_lang("ur", ["ur-PK"]) == "ur-PK"


def test_a_regional_request_is_not_pulled_to_the_motherland():
    assert closest_lang("en-US", ["en-GB", "en-US"]) == "en-US"
    assert closest_lang("en-US", ["en", "en-US"]) == "en-US"
