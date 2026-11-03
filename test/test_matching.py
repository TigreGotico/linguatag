"""Standardization, distance and closest match."""
import pytest

import linguatag.matching as language
from linguatag import closest_lang, lang_distance, lang_matches, standardize_lang


# --- standardize_lang --------------------------------------------------------

def test_standardize_normalizes_underscores_and_case():
    assert standardize_lang("en_us").lower() == "en-us"


def test_standardize_keeps_tagalog_as_tl():
    """langcodes folds `tl` into `fil`; OVOS keeps it distinct."""
    assert standardize_lang("tl") == "tl"
    assert standardize_lang("tgl") == "tl"


# --- lang_distance -----------------------------------------------------------

def test_distance_is_zero_for_identical_tags():
    assert lang_distance("en-US", "en_us") == 0


def test_distance_is_large_for_different_languages():
    assert lang_distance("en-US", "fr-FR") >= 10


def test_distance_measures_a_bare_tag_from_its_norm_region():
    """`pt` is identical to `pt-PT` and merely regional to `pt-BR`."""
    assert lang_distance("pt", "pt-PT") == 0
    assert lang_distance("pt", "pt-BR") > 0


# --- closest_lang ------------------------------------------------------------

def test_closest_lang_exact_match():
    assert closest_lang("en-US", ["pt-BR", "en-US", "de-DE"]) == "en-US"


def test_closest_lang_exact_match_after_standardization():
    assert closest_lang("en_US", ["en-US"]) == "en-US"


def test_closest_lang_returns_the_original_string():
    """The returned value is the entry from `available`, verbatim."""
    assert closest_lang("EN-us", ["en-US"]) == "en-US"


def test_closest_lang_no_match_returns_none():
    assert closest_lang("zz-ZZ", ["en-US", "pt-BR"]) is None


def test_closest_lang_disabled_with_zero_distance():
    assert closest_lang("en-AU", ["en-US"], max_distance=0) is None


def test_closest_lang_regional_fallback():
    assert closest_lang("en-AU", ["pt-BR", "en-US"]) == "en-US"


def test_closest_lang_skips_a_distant_language():
    # fr-FR is a different language and beyond the distance cap; en-GB is near.
    assert closest_lang("en-AU", ["fr-FR", "en-GB"]) == "en-GB"


def test_closest_lang_prefers_the_norm_region_for_a_bare_tag():
    """langcodes makes bare `pt` closest to pt-BR; the norm region pt-PT wins."""
    assert closest_lang("pt", ["pt-BR", "pt-PT"]) == "pt-PT"
    assert closest_lang("pt", ["pt-PT", "pt-BR"]) == "pt-PT"  # order-independent


def test_explicit_region_is_respected_over_the_norm_preference():
    assert closest_lang("pt-BR", ["pt-PT", "pt-BR"]) == "pt-BR"


def test_bare_tag_falls_back_when_norm_region_absent():
    assert closest_lang("pt", ["pt-BR"]) == "pt-BR"


# --- the langcodes-absent path ----------------------------------------------

def test_distance_without_langcodes_shares_primary_subtag(monkeypatch):
    """With no langcodes distance, a shared primary subtag still resolves."""
    monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    assert closest_lang("en-AU", ["pt-BR", "en-GB", "fr-FR"]) == "en-GB"


def test_distance_without_langcodes_prefers_the_generic_tag(monkeypatch):
    """`qaa` has no default region, so the bare tag stays generic. A bare tag
    with one (`en` is `en-GB`) is measured as that region instead."""
    monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    assert closest_lang("qaa-US", ["qaa-IL", "qaa"]) == "qaa"


def test_distance_without_langcodes_no_shared_subtag(monkeypatch):
    monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    assert closest_lang("en-AU", ["pt-BR", "fr-FR"]) is None


# --- edge cases --------------------------------------------------------------

def test_closest_lang_empty_available_is_none():
    assert closest_lang("en-US", []) is None


def test_standardize_lang_empty_string():
    assert standardize_lang("") == ""


def test_lang_distance_is_symmetric_enough_for_identity():
    assert lang_distance("en-US", "en-US") == 0
    assert lang_distance("EN_us", "en-US") == 0


def test_lang_distance_regional_versus_different_language():
    assert lang_distance("de-DE", "de-AT") < 10    # a usable regional match
    assert lang_distance("de-DE", "nl-NL") >= 10   # a different language


def test_closest_lang_regioned_request_falls_back_to_a_sibling(tmp_path):
    assert closest_lang("pt-MZ", ["en-US", "pt-BR"]) == "pt-BR"


# --- lang_matches ------------------------------------------------------------

def test_lang_matches_identical_tags():
    assert lang_matches("en-US", "en_us") is True


def test_lang_matches_different_languages():
    assert lang_matches("en-US", "fr-FR") is False


def test_lang_matches_regional_sibling_within_default_threshold():
    assert lang_matches("de-DE", "de-AT") is True


def test_lang_matches_exact_only_when_max_distance_zero():
    from linguatag import lang_matches as lm
    assert lm("en-US", "en-US", max_distance=0) is True
    assert lm("en-US", "en-GB", max_distance=0) is False


# --- the distance-10 boundary ------------------------------------------------

MACROLANGUAGE_PAIRS = [("wuu", "zh")]
REGIONAL_PAIRS = [("ar-SA", "ar", 4), ("en-AU", "en-GB", 3), ("pt-BR", "pt-PT", 5)]
UNRELATED_PAIRS = [("en", "zh", 134), ("es", "fr", 84),
                   ("fr-CH", "de-CH", 80), ("af", "nl", 24)]


@pytest.mark.parametrize("member,macro", MACROLANGUAGE_PAIRS)
def test_macrolanguage_distance_is_exactly_ten(member, macro):
    assert lang_distance(member, macro) == 10


@pytest.mark.parametrize("member,macro", MACROLANGUAGE_PAIRS)
def test_macrolanguage_resolves_at_the_default_threshold(member, macro):
    assert lang_matches(member, macro) is True
    assert closest_lang(member, [macro]) == macro


@pytest.mark.parametrize("desired,supported,distance", REGIONAL_PAIRS)
def test_regional_pair_resolves(desired, supported, distance):
    assert lang_distance(desired, supported) == distance
    assert lang_matches(desired, supported) is True
    assert closest_lang(desired, [supported]) == supported


@pytest.mark.parametrize("desired,supported,distance", UNRELATED_PAIRS)
def test_unrelated_pair_never_resolves(desired, supported, distance):
    assert lang_distance(desired, supported) == distance
    assert lang_matches(desired, supported) is False
    assert closest_lang(desired, [supported]) is None


def test_threshold_is_inclusive_on_both_sides():
    """A distance equal to the bound resolves; one above it does not."""
    assert lang_matches("en-US", "en-GB", max_distance=5) is True
    assert lang_matches("en-US", "en-GB", max_distance=4) is False
    assert closest_lang("en-US", ["en-GB"], max_distance=5) == "en-GB"
    assert closest_lang("en-US", ["en-GB"], max_distance=4) is None


# --- Arabic varieties fall back to Modern Standard Arabic ---------------------

ARABIC_REQUESTS = ["ar", "ar-SA", "ar-EG", "ar-MA", "arz", "apc", "ary", "acm",
                   "afb", "aeb", "ajp", "pga", "ssh", "arq"]


@pytest.mark.parametrize("tag", ARABIC_REQUESTS)
@pytest.mark.parametrize("langcodes_present", [True, False])
def test_arabic_request_falls_back_to_msa(tag, langcodes_present, monkeypatch):
    if not langcodes_present:
        monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    assert lang_distance(tag, "arb") <= 5
    assert closest_lang(tag, ["arb", "en-US"], max_distance=5) == "arb"


def test_arabic_variety_file_beats_msa():
    assert closest_lang("arz", ["arb", "arz"]) == "arz"
    assert closest_lang("ar-MA", ["arb", "ar-MA"]) == "ar-MA"


def test_msa_request_does_not_fall_back_to_a_variety():
    assert closest_lang("arb", ["arz"], max_distance=5) is None


def test_arabic_does_not_reach_other_languages():
    assert closest_lang("arz", ["en-US", "zh-CN"]) is None
    assert closest_lang("en-US", ["arb"]) is None


def test_cantonese_does_not_reach_mandarin():
    assert closest_lang("yue", ["zh-CN"], max_distance=5) is None
    assert closest_lang("yue", ["zh-CN"]) is None


def test_arabic_variety_prefers_its_own_region_over_another():
    assert closest_lang("ary", ["ar-EG", "ar-MA"]) == "ar-MA"
    assert closest_lang("arz", ["ar-MA", "ar-EG"]) == "ar-EG"


def test_arabic_variety_prefers_msa_over_a_foreign_region():
    assert closest_lang("ary", ["ar-EG", "arb"]) == "arb"
    assert closest_lang("apc", ["ar-SA", "arb"]) == "arb"


@pytest.mark.parametrize("msa", ["arb", "ar"])
@pytest.mark.parametrize("variety", ["arz", "arz-EG", "ary"])
def test_arabic_fallback_distance_is_exactly_five(msa, variety):
    """Bare `ar` has a default region; it still counts as MSA here."""
    assert lang_distance(variety, msa) == 5


def test_arabizi_is_not_pulled_to_msa(monkeypatch):
    capped = lang_distance("ar-Latn", "ar")
    monkeypatch.setattr(language, "_ARABIC_FALLBACK_DISTANCE", 0)
    assert lang_distance("ar-Latn", "ar") == capped
    assert lang_distance("arz-Arab", "arb") == 0


# --- Cantonese and Mandarin ---------------------------------------------------

@pytest.mark.parametrize("cantonese,mandarin", [
    ("yue", "cmn"), ("yue", "zh-CN"), ("yue-CN", "zh"), ("yue-HK", "cmn-HK"),
    ("yue-HK", "cmn"), ("zh-yue", "cmn-CN")])
def test_cantonese_never_matches_mandarin(cantonese, mandarin):
    assert lang_distance(cantonese, mandarin) >= 100
    assert lang_distance(mandarin, cantonese) >= 100
    assert closest_lang(cantonese, [mandarin]) is None
    assert closest_lang(mandarin, [cantonese]) is None


def test_a_cantonese_request_never_lands_on_mandarin_over_cantonese():
    assert closest_lang("yue", ["cmn", "yue-HK"]) != "cmn"
    assert closest_lang("yue-HK", ["cmn-HK", "zh-HK"]) == "zh-HK"


def test_traditional_chinese_keeps_its_cantonese_match():
    """A `zh-HK` resource is often Cantonese; langcodes measures it at 10."""
    assert lang_distance("yue-HK", "zh-HK") == 10
    assert closest_lang("yue-HK", ["zh-HK"]) == "zh-HK"


# --- the spellings of Modern Standard Arabic ---------------------------------

@pytest.mark.parametrize("langcodes_present", [True, False])
def test_the_spellings_of_msa_are_identical(langcodes_present, monkeypatch):
    if not langcodes_present:
        monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    for a, b in [("ar", "arb"), ("arb", "ar"), ("ar-001", "arb"), ("ar", "ar-001")]:
        assert lang_distance(a, b) == 0, (a, b)
    assert closest_lang("ar", ["ar-SA", "arb"]) == "arb"
    assert closest_lang("arb", ["ar-SA", "ar"]) == "ar"


@pytest.mark.parametrize("voice", ["zh-CN-XiaoxiaoNeural", "zh-TW-HsiaoChenNeural",
                                   "zh-CN-cantonese", "zh_CN-huayan-medium"])
def test_cantonese_never_matches_a_mandarin_voice_id(voice):
    """A voice id langcodes cannot parse is measured as its parseable prefix,
    and the Cantonese rule reads the same prefix."""
    assert lang_distance("yue", voice) > language.DEFAULT_MAX_LANGUAGE_DISTANCE
    assert closest_lang("yue", [voice]) is None


# --- tags langcodes cannot parse ----------------------------------------------

@pytest.mark.parametrize("request_tag,voice,distance", [
    ("yue", "yue-CN-XiaoMinNeural", 0),
    ("yue", "yue-voicename", 0),
    ("yue-HK", "zh-HK-HiuMaanNeural", 10),
    ("en-US", "en-US-JennyNeural", 0),
    ("en", "en-GB-SoniaNeural", 0),
    ("pt", "pt-BR-FranciscaNeural", 5),
])
def test_an_unparseable_id_is_measured_as_its_parseable_prefix(request_tag, voice, distance):
    assert lang_distance(request_tag, voice) == distance
    assert closest_lang(request_tag, [voice]) == voice


def test_the_prefix_keeps_its_region():
    """`en` is `en-GB`: a British voice id wins over an American one."""
    assert closest_lang("en", ["en-US-JennyNeural", "en-GB-SoniaNeural"]) == "en-GB-SoniaNeural"
    assert closest_lang("yue-HK", ["zh-CN-XiaoxiaoNeural", "zh-HK-HiuMaanNeural"]) \
        == "zh-HK-HiuMaanNeural"


def test_an_unparseable_request_is_measured_the_same_way():
    assert lang_distance("zh-HK-HiuMaanNeural", "yue-HK") == lang_distance("zh-HK", "yue-HK")
