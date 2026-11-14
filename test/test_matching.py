"""Standardization, distance and closest match."""
from importlib.resources import files

import pytest

import linguatag.matching as language
from linguatag import (closest_lang, is_arabic_variety, lang_distance, lang_matches,
                       standardize_lang)


# --- standardize_lang --------------------------------------------------------

def test_standardize_normalizes_underscores_and_case():
    assert standardize_lang("en_us").lower() == "en-us"


def test_standardize_keeps_tagalog_as_tl():
    """langcodes folds `tl` into `fil`; OVOS keeps it distinct."""
    assert standardize_lang("tl") == "tl"
    assert standardize_lang("tgl") == "tl"


def _registry_extlangs():
    """(Prefix, Subtag, Preferred-Value) of every extlang record in the IANA
    registry copy that langcodes ships, read independently of linguatag."""
    text = (files("langcodes") / "data" / "language-subtag-registry.txt").read_text("utf-8")
    records = (dict(line.split(": ", 1) for line in block.splitlines()
                    if ": " in line and not line.startswith(" "))
               for block in text.split("\n%%\n"))
    return [(r["Prefix"], r["Subtag"], r["Preferred-Value"])
            for r in records if r.get("Type") == "extlang"]


@pytest.mark.parametrize("prefix,subtag,preferred", _registry_extlangs())
def test_an_extlang_tag_is_its_preferred_value(prefix, subtag, preferred):
    """RFC 5646 section 3.1.7: `zh-yue-Hant-HK` and `yue-Hant-HK` "ought to be
    treated as if they were the same tag"."""
    tag = f"{prefix}-{subtag}"
    assert standardize_lang(tag) == standardize_lang(preferred)
    assert lang_distance(tag, preferred) == 0
    assert lang_distance(preferred, tag) == 0
    assert closest_lang(preferred, [prefix, tag]) == tag


def _registry_deprecated_languages():
    """(Subtag, Preferred-Value) of every deprecated language record in the
    IANA registry copy that langcodes ships, read independently of linguatag."""
    text = (files("langcodes") / "data" / "language-subtag-registry.txt").read_text("utf-8")
    records = (dict(line.split(": ", 1) for line in block.splitlines()
                    if ": " in line and not line.startswith(" "))
               for block in text.split("\n%%\n"))
    return [(r["Subtag"], r["Preferred-Value"]) for r in records
            if r.get("Type") == "language" and "Deprecated" in r and "Preferred-Value" in r]


@pytest.mark.parametrize("subtag,preferred", _registry_deprecated_languages())
def test_a_deprecated_language_is_its_preferred_value(subtag, preferred):
    """RFC 5646 section 4.5: a deprecated subtag is replaced by its
    Preferred-Value in the canonical form."""
    assert standardize_lang(subtag) == standardize_lang(preferred)
    assert lang_distance(subtag, preferred) == 0


# IANA Language Subtag Registry, File-Date 2026-09-17. The langcodes copy
# predates these records:
#   Subtag: ajp  Description: South Levantine Arabic  Deprecated: 2023-03-17
#   Preferred-Value: apc  (apc: "Levantine Arabic", Macrolanguage: ar)
#   Subtag: ajt  Description: Judeo-Tunisian Arabic  Deprecated: 2023-03-17
#   Preferred-Value: aeb
@pytest.mark.parametrize("tag,canonical", [
    ("ajp", "apc"),
    ("ajp-JO", "apc-JO"),
    ("AJP_jo", "apc-JO"),
    ("ar-ajp", "apc"),  # the extlang record still names ajp
    ("ajt", "aeb"),
])
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_a_deprecation_newer_than_langcodes_is_applied(tag, canonical, with_langcodes, request):
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    assert standardize_lang(tag) == canonical


def test_a_south_levantine_request_finds_a_levantine_entry():
    assert lang_distance("ajp", "apc") == 0
    assert closest_lang("ajp-JO", ["ar", "apc"]) == "apc"


@pytest.mark.parametrize("tag,canonical", [
    ("zh-hak", "hak"),  # the RFC 5646 section 4.5 example
    ("zh-yue-Hant-HK", "yue-Hant-HK"),  # the RFC 5646 section 3.1.7 example
    ("zh-nan-TW", "nan-TW"),
    ("ar-arz-EG", "arz-EG"),
    ("sgn-ase-US", "ase-US"),
    ("ZH_HAK_tw", "hak-TW"),
    ("zh-hak-x-sixian", "hak-x-sixian"),
])
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_standardize_replaces_an_extlang_and_keeps_the_other_subtags(
        tag, canonical, with_langcodes, request):
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    assert standardize_lang(tag) == canonical


@pytest.mark.parametrize("tag", ["en-hak", "zh-x-hak", "ar-hak", "zh-arz"])
def test_an_extlang_under_another_prefix_is_not_replaced(tag):
    """IANA registers `hak` with Prefix `zh` and `arz` with Prefix `ar` only."""
    assert standardize_lang(tag).lower() == tag.lower()


def test_an_extlang_tag_is_not_read_as_its_prefix():
    assert closest_lang("hak", ["zh", "zh-hak"]) == "zh-hak"
    assert closest_lang("arz-EG", ["ar-SA", "ar-arz-EG"]) == "ar-arz-EG"
    assert closest_lang("zh-hak", ["cmn"]) is None


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

MACROLANGUAGE_PAIRS = [("vro", "et"), ("ltg", "lv")]
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
                   "afb", "aeb", "ajp", "ssh", "arq", "pga-Arab", "acy-Arab",
                   "mey", "mey-MR", "mey-Arab-MR"]


@pytest.mark.parametrize("tag", ARABIC_REQUESTS)
@pytest.mark.parametrize("langcodes_present", [True, False])
def test_arabic_request_falls_back_to_msa(tag, langcodes_present, monkeypatch):
    if not langcodes_present:
        monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    assert lang_distance(tag, "arb") <= 5
    assert closest_lang(tag, ["arb", "en-US"], max_distance=5) == "arb"


@pytest.mark.parametrize("tag", ["pga", "pga-SS", "acy", "acy-CY", "pga-Latn", "mey-Latn"])
@pytest.mark.parametrize("langcodes_present", [True, False])
def test_a_latin_script_arabic_language_does_not_fall_back_to_msa(
        tag, langcodes_present, monkeypatch):
    """CLDR likely subtags write Juba Arabic (pga_Latn_SS) and Cypriot
    Maronite Arabic (acy_Latn_CY) in Latin script."""
    if not langcodes_present:
        monkeypatch.setattr(language, "_langcodes_distance", lambda a, b: None)
    assert lang_distance(tag, "arb") > language.DEFAULT_MAX_LANGUAGE_DISTANCE
    assert closest_lang(tag, ["arb", "ar", "ar-001"]) is None


def test_arabic_variety_file_beats_msa():
    assert closest_lang("arz", ["arb", "arz"]) == "arz"
    assert closest_lang("ar-MA", ["arb", "ar-MA"]) == "ar-MA"


def test_msa_request_does_not_fall_back_to_a_variety():
    assert closest_lang("arb", ["arz"], max_distance=5) is None
    assert closest_lang("arb", ["mey-MR"], max_distance=5) is None


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
@pytest.mark.parametrize("variety", ["arz", "arz-EG", "ary", "mey", "mey-MR"])
def test_arabic_fallback_distance_is_exactly_five(msa, variety):
    """Bare `ar` has a default region; it still counts as MSA here."""
    assert lang_distance(variety, msa) == 5


def test_arabizi_is_not_pulled_to_msa(monkeypatch):
    capped = lang_distance("ar-Latn", "ar")
    monkeypatch.setattr(language, "_ARABIC_FALLBACK_DISTANCE", 0)
    assert lang_distance("ar-Latn", "ar") == capped
    assert lang_distance("arz-Arab", "arb") == 0


# --- Which tags name Arabic ---------------------------------------------------

# The IANA language subtags with `Macrolanguage: ar` (registry File-Date
# 2026-09-17), and the macrolanguage itself under its ISO 639-1 and 639-2 codes.
ARABIC_MACROLANGUAGE = ["ar", "ara"] + """aao abh abv acm acq acw acx acy adf aeb aec
    afb ajp apc apd arb arq ars ary arz auz avl ayh ayl ayn ayp bbz pga shu ssh""".split()


@pytest.mark.parametrize("code", ARABIC_MACROLANGUAGE + ["mey"])
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_an_arabic_language_is_an_arabic_variety_in_any_script(code, with_langcodes, request):
    """Hassaniyya (`mey`) is outside the macrolanguage in IANA, and Arabic in
    Glottolog 5.4 (languoid hass1238)."""
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    for suffix in ("", "-Arab", "-Latn", "-EG", "-MR", "-Arab-MR", "-Latn-001", "-x-buckwalt"):
        assert is_arabic_variety(code + suffix), code + suffix


@pytest.mark.parametrize("tag", ["ar-Latn-x-buckwalt", "AR_latn", "acy", "acy-CY",
                                 "pga", "pga-SS", "mey-Latn", "ar-SA-HamedNeural"])
def test_a_latin_script_or_voice_id_tag_is_an_arabic_variety(tag):
    assert is_arabic_variety(tag)


@pytest.mark.parametrize("tag", ["und", "und-Arab", "fa", "fa-Arab-IR", "ur", "ps", "ug",
                                 "ckb", "ks-Arab", "arc", "arn", "en", "x-ar"])
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_a_language_that_is_not_arabic_is_not_an_arabic_variety(tag, with_langcodes,
                                                                request):
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    assert not is_arabic_variety(tag)


@pytest.mark.parametrize("malformed", ["ar-", "ar_", "-ar", "ar--EG", ""])
def test_a_tag_with_an_empty_subtag_is_not_an_arabic_variety(malformed):
    assert not is_arabic_variety(malformed)


# --- Cantonese and Mandarin ---------------------------------------------------

@pytest.mark.parametrize("cantonese,mandarin", [
    ("yue", "cmn"), ("yue", "zh-CN"), ("yue-CN", "zh"), ("yue-HK", "cmn-HK"),
    ("yue-HK", "cmn"), ("zh-yue", "cmn-CN")])
def test_cantonese_never_matches_mandarin(cantonese, mandarin):
    assert lang_distance(cantonese, mandarin) >= 100
    assert lang_distance(mandarin, cantonese) >= 100
    assert closest_lang(cantonese, [mandarin]) is None
    assert closest_lang(mandarin, [cantonese]) is None


SINITIC_REQUESTS = [f"{language}{suffix}" for language in ("hak", "nan", "wuu", "gan", "hsn")
                    for suffix in ("", "-CN", "-Hans", "-Latn")]


@pytest.mark.parametrize("mandarin", ["cmn", "zh", "zh-Hans", "zh-CN"])
@pytest.mark.parametrize("sinitic", SINITIC_REQUESTS)
def test_a_sinitic_language_never_matches_mandarin(sinitic, mandarin):
    """Hakka, Min Nan, Wu, Gan and Xiang are separate languages of the `zh`
    macrolanguage, as Cantonese is."""
    assert lang_distance(sinitic, mandarin) >= 100
    assert lang_distance(mandarin, sinitic) >= 100
    assert closest_lang(sinitic, [mandarin]) is None
    assert closest_lang(mandarin, [sinitic]) is None


@pytest.mark.parametrize("sinitic", ["hak-Latn", "nan-Latn", "wuu-Latn", "gan-Latn", "hsn-Latn"])
def test_a_latin_script_sinitic_language_never_matches_pinyin(sinitic):
    assert closest_lang(sinitic, ["cmn-Latn", "cmn-latn-pinyin"]) is None


@pytest.mark.parametrize("chinese", ["zh", "zh-Hans", "zh-CN"])
def test_mandarin_is_its_own_macrolanguage_tag(chinese):
    assert lang_distance("cmn", chinese) == 0
    assert lang_distance(chinese, "cmn") == 0


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


@pytest.mark.parametrize("malformed", ["ar-", "AR-", "ar_", "-ar", "_ar", "ar--EG", "ar-EG-", ""])
@pytest.mark.parametrize("with_langcodes", [True, False])
def test_a_tag_with_an_empty_subtag_matches_nothing(malformed, with_langcodes, request):
    if not with_langcodes:
        request.getfixturevalue("no_langcodes")
    for tag in ("ar", "ar-EG", "arb", malformed):
        assert lang_distance(malformed, tag) > 10
        assert lang_distance(tag, malformed) > 10
        assert lang_distance(malformed, tag, lects="standard") > 10
    assert closest_lang(malformed, ["ar", "ar-EG", "arz"]) is None
    assert closest_lang("ar", [malformed]) is None
