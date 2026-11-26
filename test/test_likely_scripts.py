"""The likely script of a language whose langcodes 3.5.1 entry differs from CLDR 49."""
import json
from pathlib import Path

import pytest

import linguatag._matching as matching
from linguatag import (DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang, default_region,
                       lang_distance, with_default_region)

LIKELY = json.loads((Path(matching.__file__).parent / "data" / "likely_subtags.json")
                    .read_text(encoding="utf-8"))["likely"]


# CLDR 49 likelySubtags.xml (unicode-org/cldr, tag release-49), every entry of
# each Arabic variety that langcodes 3.5.1 expands to Latin script. CLDR
# writes each one in Arabic script, and Hassaniyya in Senegal in Latin script.
CLDR_49_ARABIC = {
    "aao": "aao_Arab_DZ", "abh": "abh_Arab_TJ", "abv": "abv_Arab_BH",
    "acm": "acm_Arab_IQ", "acq": "acq_Arab_YE", "acw": "acw_Arab_SA",
    "acx": "acx_Arab_OM", "adf": "adf_Arab_OM", "aec": "aec_Arab_EG",
    "afb": "afb_Arab_KW", "auz": "auz_Arab_UZ", "ayh": "ayh_Arab_YE",
    "ayl": "ayl_Arab_LY", "ayn": "ayn_Arab_YE", "ayp": "ayp_Arab_IQ",
    "mey": "mey_Arab_DZ", "mey_SN": "mey_Latn_SN", "mey_Latn": "mey_Latn_SN",
    "ssh": "ssh_Arab_AE",
}


# CLDR 49 likelySubtags.xml (unicode-org/cldr, tag release-49), the one entry
# of each language:
#   <likelySubtag from="hyw" to="hyw_Armn_AM" origin="sil1"/>
#   <likelySubtag from="lzh" to="lzh_Hant_CN"/>
# langcodes 3.5.1 expands `hyw` to `hyw-Latn-US` and `lzh` to `lzh-Hans-CN`.
CLDR_49_OTHER = {"hyw": "hyw_Armn_AM", "lzh": "lzh_Hant_CN"}
CLDR_49 = {**CLDR_49_ARABIC, **CLDR_49_OTHER}


def test_the_data_holds_every_cldr_entry_of_the_arabic_varieties_hyw_and_lzh():
    for source, likely in CLDR_49.items():
        assert LIKELY[source.replace("_", "-")] == likely.replace("_", "-")


@pytest.mark.parametrize("source,likely", CLDR_49.items())
def test_a_language_is_measured_in_its_cldr_script_and_region(
        source, likely):
    tag, likely = source.replace("_", "-"), likely.replace("_", "-")
    assert lang_distance(tag, likely) == 0
    assert lang_distance(likely, tag) == 0
    assert closest_lang(tag, ["ar", likely]) == likely


@pytest.mark.parametrize("language", [s for s in CLDR_49_ARABIC if "_" not in s])
def test_an_arabic_variety_in_latin_script_is_another_script(language):
    assert lang_distance(language, f"{language}-Latn") > DEFAULT_MAX_LANGUAGE_DISTANCE
    assert lang_distance(f"{language}-Arab", f"{language}-Latn") == lang_distance(
        language, f"{language}-Latn")


def test_hassaniyya_is_in_arabic_script():
    assert lang_distance("mey", "mey-Arab") == 0
    assert closest_lang("mey", ["ar", "mey-Arab"]) == "mey-Arab"
    assert closest_lang("mey-MR", ["arb", "mey-Arab-MR"]) == "mey-Arab-MR"
    assert closest_lang("mey-Arab-MR", ["ar", "mey-MR"]) == "mey-MR"


def test_hassaniyya_in_senegal_is_in_latin_script():
    """CLDR 49: `mey_SN` is `mey_Latn_SN`, so Modern Standard Arabic does not
    serve it, as it serves no other Latin-script request."""
    assert lang_distance("mey-SN", "ar") > DEFAULT_MAX_LANGUAGE_DISTANCE
    assert lang_distance("mey-Latn", "mey-SN") == 0
    assert closest_lang("mey-SN", ["ar", "mey-Arab-SN"]) is None


@pytest.mark.parametrize("tag,lect", [
    ("ayl-Arab-LY", "ayl"), ("ayp-Arab-IQ", "ayp"), ("ayp-Arab-TR", "ayp"),
    ("acm-Arab-IQ", "acm-IQ"), ("mey-Arab-MR", "mey-MR")])
def test_an_arabic_variety_in_arabic_script_keeps_its_own_language(tag, lect):
    assert closest_lang(tag, ["ar", "ar-001", lect]) == lect


@pytest.mark.parametrize("language,likely", CLDR_49_OTHER.items())
def test_the_default_region_is_the_cldr_49_region(language, likely):
    _, script, region = likely.split("_")
    assert default_region(language) == region
    assert default_region(f"{language}-{script}") == region
    assert with_default_region(language) == f"{language}-{region}"


@pytest.mark.parametrize("request_tag", ["hyw", "hyw-Armn", "hyw-AM", "hyw-Armn-AM"])
@pytest.mark.parametrize("resource", ["hyw", "hyw-AM", "hyw-Armn"])
def test_western_armenian_in_armenian_script_matches_an_armenian_resource(request_tag,
                                                                          resource):
    """CLDR 49 writes `hyw` in Armenian script, so `hyw` and `hyw-AM` name
    an Armenian-script resource."""
    assert lang_distance(request_tag, resource) == 0
    assert closest_lang(request_tag, [resource]) == resource


@pytest.mark.parametrize("latin", ["hyw-Latn", "hyw-Latn-AM", "hyw-Latn-US"])
@pytest.mark.parametrize("resource", ["hyw", "hyw-AM", "hyw-Armn", "hyw-Armn-AM"])
def test_western_armenian_in_latin_script_matches_no_armenian_resource(latin, resource):
    assert lang_distance(latin, resource) > DEFAULT_MAX_LANGUAGE_DISTANCE
    assert lang_distance(resource, latin) > DEFAULT_MAX_LANGUAGE_DISTANCE
    assert closest_lang(latin, [resource]) is None
    assert closest_lang(resource, [latin]) is None


# CLDR 49 languageInfo.xml gives
# `<languageMatch desired="lzh" supported="zh" distance="10" oneway="true"/>`
# and, for two different regions,
# `<languageMatch desired="*_*_*" supported="*_*_*" distance="4"/>`. So
# Literary Chinese, in Traditional script in China, is 10 from Traditional
# Chinese in China and 14 from Traditional Chinese in Taiwan.
@pytest.mark.parametrize("literary", ["lzh", "lzh-CN", "lzh-Hant", "lzh-Hant-CN", "zh-lzh"])
def test_literary_chinese_is_traditional_chinese_in_china(literary):
    assert lang_distance(literary, "zh-Hant-CN") == 10
    assert closest_lang(literary, ["cmn", "zh-Hans", "zh-Hant", "zh-Hant-CN"]) == "zh-Hant-CN"
    assert lang_distance(literary, "zh-Hant") == 14
    assert closest_lang(literary, ["cmn", "zh-Hans", "zh-Hant"]) is None
    assert closest_lang(literary, ["cmn", "zh-Hans", "zh-Hant"], max_distance=14) == "zh-Hant"


@pytest.mark.parametrize("literary", ["lzh-TW", "lzh-Hant-TW"])
@pytest.mark.parametrize("traditional", ["zh-Hant", "zh-TW", "zh-Hant-TW"])
def test_literary_chinese_in_taiwan_finds_traditional_chinese(literary, traditional):
    assert lang_distance(literary, traditional) == 10
    assert closest_lang(literary, ["cmn", "zh-Hans", traditional]) == traditional


@pytest.mark.parametrize("literary", ["lzh", "lzh-CN", "lzh-TW", "lzh-Hant"])
@pytest.mark.parametrize("simplified", ["cmn", "zh", "zh-Hans", "zh-CN"])
def test_literary_chinese_in_traditional_script_matches_no_simplified_resource(literary,
                                                                               simplified):
    assert lang_distance(literary, simplified) > DEFAULT_MAX_LANGUAGE_DISTANCE
    assert closest_lang(literary, [simplified]) is None
