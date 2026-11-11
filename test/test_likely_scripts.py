"""The likely script of an Arabic variety, from CLDR likely subtags."""
import json
from pathlib import Path

import pytest

import linguatag.matching as matching
from linguatag import DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang, lang_distance

DATA = json.loads((Path(matching.__file__).parent / "data" / "likely_regions.json")
                  .read_text(encoding="utf-8"))


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


def test_the_tables_hold_every_cldr_entry_of_the_arabic_varieties():
    scripts, regions = {}, {}
    for source, likely in CLDR_49_ARABIC.items():
        _, script, region = likely.split("_")
        _, *named = source.split("_")
        tag = source.replace("_", "-")
        if not named or len(named[0]) == 2:
            scripts[tag] = script
        if not named or len(named[0]) == 4:
            regions[tag] = region
    assert DATA["scripts"] == scripts
    assert {tag: DATA["regions"].get(tag) for tag in regions} == regions


@pytest.mark.parametrize("source,likely", CLDR_49_ARABIC.items())
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_an_arabic_variety_is_measured_in_its_cldr_script_and_region(
        source, likely, with_langcodes, request):
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
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
