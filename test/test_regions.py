"""The default region of a tag that names none."""
import json
from pathlib import Path

import pytest
from langcodes import Language

import linguatag.matching as matching
import linguatag.standardize as standardize
from linguatag import (OVERRIDES, closest_lang, default_region, lang_distance,
                       with_default_region)

TABLE = json.loads((Path(matching.__file__).parent / "data" / "likely_regions.json")
                   .read_text(encoding="utf-8"))["regions"]


@pytest.fixture
def no_langcodes(monkeypatch):
    """Both standardization and distance as they run without langcodes."""
    import builtins
    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "langcodes" or name.startswith("langcodes."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    standardize.standardize_lang.cache_clear()
    matching._parseable_prefix.cache_clear()
    monkeypatch.setattr(builtins, "__import__", refuse)
    yield
    standardize.standardize_lang.cache_clear()
    matching._parseable_prefix.cache_clear()


@pytest.mark.parametrize("language,region", [
    ("en", "GB"), ("pt", "PT"), ("ur", "IN"), ("yue", "CN"), ("ar", "001")])
def test_an_override_sets_the_default(language, region):
    assert default_region(language) == region


def test_every_override_differs_from_cldr():
    """An override that CLDR already gives says nothing."""
    for language, (_, region) in OVERRIDES.items():
        assert Language.get(language).maximize().territory != region, language
        assert TABLE[language] != region


def test_every_override_script_is_the_one_its_region_writes():
    for language, (script, region) in OVERRIDES.items():
        assert Language.get(f"{language}-{region}").maximize().script == script, language


@pytest.mark.parametrize("tag,region", [
    ("yue-Hant", "HK"), ("yue-Hans", "CN"), ("en-Dsrt", "US"), ("en-Latn", "GB"),
    ("pt-Latn", "PT"), ("ar-Arab", "001")])
def test_an_override_applies_only_in_its_own_script(tag, region):
    assert default_region(tag) == region


def test_cantonese_defaults_to_simplified_script():
    assert with_default_region("yue") == "yue-CN"
    assert Language.get("yue-CN").maximize().script == "Hans"
    assert default_region("yue-Hant") == "HK"


def test_bare_arabic_is_modern_standard_arabic():
    assert with_default_region("ar") == "ar-001"
    assert lang_distance("ar", "ar-001") == 0
    assert lang_distance("ar", "ar-EG") > 0


@pytest.mark.parametrize("language", ["es", "fr", "de", "it", "zh", "ja", "bn", "yi"])
def test_without_an_override_the_cldr_region_stands(language):
    assert language not in OVERRIDES
    assert default_region(language) == Language.get(language).maximize().territory


def test_the_table_is_the_cldr_likely_region_of_every_tag_without_one():
    assert len(TABLE) == 746
    for tag, region in TABLE.items():
        assert "-" not in tag or len(tag.split("-")[1]) == 4, tag
        assert Language.get(tag).maximize().territory == region, tag
    assert "ZZ" not in TABLE.values()
    assert TABLE["yi"] == "001"


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


def test_an_unknown_language_has_no_region():
    assert default_region("qaa") is None
    assert with_default_region("qaa") == "qaa"


@pytest.mark.parametrize("tag,region", [
    ("eng", "GB"), ("por", "PT"), ("urd", "IN"), ("iw", "IL"), ("mo", "RO"),
    ("EN", "GB"), ("zh_hant", "TW"), ("zh-yue", "CN")])
def test_a_tag_is_standardized_before_the_lookup(tag, region):
    assert default_region(tag) == region


@pytest.mark.parametrize("tag,expected", [
    ("en", "en-GB"),
    ("pt", "pt-PT"),
    ("es", "es-ES"),
    ("en_us", "en-US"),
    ("EN_gb", "en-GB"),
    ("zh-Hant", "zh-Hant-TW"),
    ("zh_hant", "zh-Hant-TW"),
    ("gl-x-central", "gl-ES-x-central"),
    ("pt-BR", "pt-BR"),
    ("ext-PT-x-barrancos", "ext-PT-x-barrancos"),
    ("sl-rozaj", "sl-SI-rozaj"),
    ("x-klingon", "x-klingon"),
    ("", ""),
])
def test_with_default_region(tag, expected):
    assert with_default_region(tag) == expected


@pytest.mark.parametrize("tag", ["zh-yue", "zh-min-nan", "sgn-ase"])
def test_an_extended_form_never_gets_a_region_inside_it(tag, no_langcodes):
    """Without langcodes `zh-yue` stays as written; `zh-CN-yue` is wrong."""
    assert with_default_region(tag) == tag
    assert default_region(tag) is None


def test_without_langcodes_the_case_follows_bcp47(no_langcodes):
    assert with_default_region("EN_us") == "en-US"
    assert with_default_region("zh_hant") == "zh-Hant-TW"
    assert with_default_region("ext-pt-X-Barrancos") == "ext-PT-x-barrancos"
    assert with_default_region("en-x-GB") == "en-GB-x-gb"
    assert with_default_region("en-u-CA-gregory") == "en-GB-u-ca-gregory"


@pytest.mark.parametrize("langcodes_present", [True, False])
def test_a_bare_tag_is_its_default_region_when_measured(langcodes_present, monkeypatch):
    if not langcodes_present:
        monkeypatch.setattr(matching, "_langcodes_distance", lambda a, b: None)
    assert lang_distance("en", "en-GB") == 0
    assert lang_distance("en", "en-US") > 0
    assert lang_distance("ur", "ur-IN") == 0
    assert lang_distance("ur", "ur-PK") > 0
    assert lang_distance("yue", "yue-CN") == 0
    assert closest_lang("en", ["en-US", "en-GB"]) == "en-GB"
    assert closest_lang("yue", ["yue-HK", "yue-CN"]) == "yue-CN"


@pytest.mark.parametrize("langcodes_present", [True, False])
def test_a_regional_arabic_request_ties_msa_and_a_foreign_region(langcodes_present, monkeypatch):
    """`ar-MA` is 5 from both `ar-EG` and bare `ar` (`ar-001`), so the order
    of the candidates decides; the request never leaves Arabic."""
    if not langcodes_present:
        monkeypatch.setattr(matching, "_langcodes_distance", lambda a, b: None)
    assert lang_distance("ar-MA", "ar-EG") == lang_distance("ar-MA", "ar") == 5
    assert closest_lang("ar-MA", ["ar-EG", "ar"]) == "ar-EG"
    assert closest_lang("ar-MA", ["ar", "ar-EG"]) == "ar"


def test_a_bare_request_still_reaches_another_region():
    assert closest_lang("en", ["en-US"]) == "en-US"
    assert closest_lang("ur", ["ur-PK"]) == "ur-PK"


def test_a_regional_request_is_not_pulled_to_the_default():
    assert closest_lang("en-US", ["en-GB", "en-US"]) == "en-US"
    assert closest_lang("en-US", ["en", "en-US"]) == "en-US"
