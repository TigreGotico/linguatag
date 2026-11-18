"""The default region of a tag that names none."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import linguatag.matching as matching
from linguatag import (OVERRIDES, closest_lang, default_region, lang_distance,
                       standardize_lang, with_default_region)

DATA = json.loads((Path(matching.__file__).parent / "data" / "likely_subtags.json")
                  .read_text(encoding="utf-8"))
# CLDR 49 likelySubtags, hyphenated: `"zh-Hant": "zh-Hant-TW"`.
LIKELY = DATA["likely"]


def cldr_49(tag: str) -> list:
    """The `[language, script, region]` that CLDR 49 likely-subtags gives
    `tag`, looked up as UTS #35 section 4.3 says: language_region, then
    language."""
    language, *rest = tag.split("-")
    key = tag if tag in LIKELY else language
    return LIKELY[key].split("-")


@pytest.mark.parametrize("language,region", [
    ("en", "GB"), ("pt", "PT"), ("ur", "IN"), ("yue", "CN"), ("ar", "001")])
def test_an_override_sets_the_default(language, region):
    assert default_region(language) == region


def test_every_override_differs_from_cldr():
    """An override that CLDR already gives says nothing."""
    for language, (_, region) in OVERRIDES.items():
        assert cldr_49(language)[2] != region, language


def test_every_override_script_is_the_one_its_region_writes():
    for language, (script, region) in OVERRIDES.items():
        assert cldr_49(f"{language}-{region}")[1] == script, language


@pytest.mark.parametrize("tag,region", [
    ("yue-Hant", "HK"), ("yue-Hans", "CN"), ("en-Dsrt", "US"), ("en-Latn", "GB"),
    ("pt-Latn", "PT"), ("ar-Arab", "001")])
def test_an_override_applies_only_in_its_own_script(tag, region):
    assert default_region(tag) == region


def test_cantonese_defaults_to_simplified_script():
    assert with_default_region("yue") == "yue-CN"
    assert cldr_49("yue-CN")[1] == "Hans"
    assert default_region("yue-Hant") == "HK"


def test_bare_arabic_is_modern_standard_arabic():
    assert with_default_region("ar") == "ar-001"
    assert lang_distance("ar", "ar-001") == 0
    assert lang_distance("ar", "ar-EG") > 0


@pytest.mark.parametrize("language", ["es", "fr", "de", "it", "zh", "ja", "bn", "yi"])
def test_without_an_override_the_cldr_region_stands(language):
    assert language not in OVERRIDES
    assert default_region(language) == cldr_49(language)[2]


def test_yiddish_takes_the_cldr_49_region():
    # CLDR 49 likelySubtags.json: "yi": "yi-Hebr-UA"; langcodes 3.5.1 gives yi-Hebr-001.
    assert default_region("yi") == "UA"


def test_every_tag_without_a_region_takes_its_cldr_49_region():
    """Each CLDR 49 entry for a language, or a language and a script, gives
    its region, unless an override names the language and its script."""
    assert DATA["source"] == "CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json"
    assert len(LIKELY) == 7868
    checked = 0
    for tag, likely in LIKELY.items():
        language, *rest = tag.split("-")
        if language == "und" or any(len(r) != 4 for r in rest):
            continue
        if standardize_lang(tag) != tag or language in OVERRIDES:
            continue
        assert default_region(tag) == likely.split("-")[2], tag
        checked += 1
    # Every CLDR 49 key of a language, or a language and a script, other
    # than `und`, the five override languages and the deprecated codes `in`,
    # `iw`, `ji`, `jw` and `mo`.
    assert checked == 7314


def test_a_tag_with_a_region_keeps_it():
    assert default_region("pt-BR") == "BR"
    assert default_region("en_us") == "US"
    assert default_region("es-419") == "419"
    assert default_region("sr-Latn-RS") == "RS"


def test_a_script_uses_its_own_entry_before_its_language():
    assert default_region("zh-Hant") == "TW"
    assert default_region("zh") == "CN"
    assert "sr-Latn" not in LIKELY
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
    ("ext-PT-x-barranco", "ext-PT-x-barranco"),
    ("sl-rozaj", "sl-SI-rozaj"),
    ("x-klingon", "x-klingon"),
    ("", ""),
])
def test_with_default_region(tag, expected):
    assert with_default_region(tag) == expected


@pytest.mark.parametrize("with_langcodes", [True, False])
def test_a_grandfathered_form_takes_its_preferred_value(with_langcodes, request):
    """IANA: `Tag: zh-min-nan ... Preferred-Value: nan`; CLDR 49 gives
    `nan` the region CN. `zh-CN-min-nan` would be wrong."""
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    assert with_default_region("zh-min-nan") == "nan-CN"
    assert default_region("zh-min-nan") == "CN"


@pytest.mark.parametrize("tag,expected", [("zh-yue", "yue-CN"), ("sgn-ase", "ase-US")])
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_an_extlang_form_takes_the_region_of_its_preferred_value(
        tag, expected, with_langcodes, request):
    """IANA gives the extlangs `yue` and `ase` the Preferred-Values `yue` and `ase`."""
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    assert with_default_region(tag) == expected


def test_without_langcodes_the_case_follows_bcp47(no_langcodes):
    assert with_default_region("EN_us") == "en-US"
    assert with_default_region("zh_hant") == "zh-Hant-TW"
    assert with_default_region("ext-pt-X-Barranco") == "ext-PT-x-barranco"
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


@pytest.mark.parametrize("target, available, exact", [
    ("pt-PT", ["pt", "pt-BR", "pt-PT"], "pt-PT"),
    ("es-ES", ["es", "es-ES"], "es-ES"),
    ("en", ["en-GB", "en"], "en"),
    ("pt-pt", ["pt", "pt-PT"], "pt-PT"),
    ("pt_PT", ["pt", "pt-PT"], "pt-PT"),
])
def test_an_exact_candidate_wins_a_tie_at_zero(target, available, exact):
    assert lang_distance(target, available[0]) == lang_distance(target, exact) == 0
    assert closest_lang(target, available) == exact
    assert closest_lang(target, available, lects="standard") == exact


def test_a_regional_request_is_not_pulled_to_the_default():
    assert closest_lang("en-US", ["en-GB", "en-US"]) == "en-US"
    assert closest_lang("en-US", ["en", "en-US"]) == "en-US"


_WITHOUT_LANGCODES = """
import builtins, sys
real_import = builtins.__import__
def refuse(name, *args, **kwargs):
    if name == "langcodes" or name.startswith("langcodes."):
        raise ImportError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = refuse
from linguatag import lang_distance
print(lang_distance(sys.argv[1], sys.argv[2]))
"""


@pytest.mark.parametrize("desired,supported", [
    ("an-x-benasque", "an-x-chistau"), ("zh-HK-HiuMaanNeural", "zh-HK")])
def test_a_prefix_found_with_langcodes_is_not_reused_without_it(desired, supported, request):
    lang_distance(desired, supported)
    request.getfixturevalue("no_langcodes")
    expected = subprocess.run([sys.executable, "-c", _WITHOUT_LANGCODES, desired, supported],
                              check=True, capture_output=True, text=True).stdout
    assert lang_distance(desired, supported) == int(expected)
