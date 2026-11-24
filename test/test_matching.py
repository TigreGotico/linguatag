"""Standardization, distance and closest match."""
import json
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


def _registry(kind):
    """The IANA Language Subtag Registry records of one type, File-Date
    2026-11-18, as ``linguatag/data/subtags.json`` holds them."""
    return json.loads((files("linguatag") / "data" / "subtags.json").read_text("utf-8"))[kind]


def _registry_extlangs():
    """(Prefix, Subtag, Preferred-Value) of every extlang record."""
    return [(record["prefix"][0], subtag, record["preferred"])
            for subtag, record in _registry("extlang").items()]


@pytest.mark.parametrize("prefix,subtag,preferred", _registry_extlangs())
def test_an_extlang_tag_is_its_preferred_value(prefix, subtag, preferred):
    """RFC 5646 section 3.1.7: `zh-yue-Hant-HK` and `yue-Hant-HK` "ought to be
    treated as if they were the same tag"."""
    tag = f"{prefix}-{subtag}"
    assert standardize_lang(tag) == standardize_lang(preferred)
    assert lang_distance(tag, preferred) == 0
    assert lang_distance(preferred, tag) == 0
    assert closest_lang(preferred, [prefix, tag]) == tag


def _registry_deprecated(kind):
    """(Subtag, Preferred-Value) of every deprecated record of one type that
    has a Preferred-Value."""
    return [(subtag, record["preferred"]) for subtag, record in _registry(kind).items()
            if "deprecated" in record and "preferred" in record]


@pytest.mark.parametrize("subtag,preferred", _registry_deprecated("language"))
def test_a_deprecated_language_is_its_preferred_value(subtag, preferred):
    """RFC 5646 section 4.5: a deprecated subtag is replaced by its
    Preferred-Value in the canonical form."""
    assert standardize_lang(subtag) == standardize_lang(preferred)
    assert lang_distance(subtag, preferred) == 0


@pytest.mark.parametrize("target,available,expected", [
    ("apc", ["ajp", "apc"], "apc"),
    ("apc-SY", ["ajp", "apc"], "apc"),
    ("enm", ["yol", "enm"], "enm"),
    ("ajp_Arab", ["apc_Arab", "ajp_Arab"], "ajp_Arab"),
    ("ajp", ["apc", "ajp"], "ajp"),
    ("ar-ajp", ["apc", "ar-ajp"], "ar-ajp"),
])
def test_a_tie_goes_to_the_code_as_written(target, available, expected):
    """A deprecated code and its Preferred-Value standardize to one string.
    Data sets that keep both apart (NLLB ajp_Arab and apc_Arab) still get
    the entry the request names."""
    assert closest_lang(target, available) == expected


@pytest.mark.parametrize("target,available,expected", [
    ("yol-IE", ["enm", "yol"], "yol"),
    ("he-IL", ["iw", "he"], "he"),
    ("ajp-JO", ["apc", "ajp"], "ajp"),
])
def test_a_tie_between_a_deprecated_code_and_its_preferred_value(target, available, expected):
    assert closest_lang(target, available) == expected


# RFC 5646 section 4.5, step 3: "For extlangs, the original primary language
# subtag is also replaced if there is a primary language subtag in the
# 'Preferred-Value'." The registry marks extlang `ajp` Deprecated 2023-03-17.
@pytest.mark.parametrize("target,available,expected", [
    ("hak", ["zh-hak", "hak"], "hak"),
    ("zh-hak", ["hak", "zh-hak"], "zh-hak"),
    ("yue", ["zh-yue", "yue"], "yue"),
    ("zh-yue", ["yue", "zh-yue"], "zh-yue"),
    ("arz-EG", ["ar-arz-EG", "arz-EG"], "arz-EG"),
    ("ar-arz-EG", ["arz-EG", "ar-arz-EG"], "ar-arz-EG"),
    ("apc", ["ar-ajp", "apc"], "apc"),
])
def test_a_tie_between_an_extlang_form_and_its_preferred_value(target, available, expected):
    assert closest_lang(target, available) == expected


@pytest.mark.parametrize("subtag,preferred", _registry_deprecated("region"))
def test_a_tie_goes_to_the_preferred_value_of_a_deprecated_region(subtag, preferred):
    deprecated, canonical = f"en-{subtag}", f"en-{preferred}"
    assert closest_lang(canonical, [deprecated, canonical]) == canonical
    assert closest_lang(canonical, [canonical, deprecated]) == canonical


# IANA Language Subtag Registry, File-Date 2026-11-18:
#   Type: region  Subtag: BU  Description: Burma  Deprecated: 1989-12-05  Preferred-Value: MM
#   Type: region  Subtag: DD  Description: German Democratic Republic  Deprecated: 1990-10-30
#     Preferred-Value: DE
#   Type: extlang  Subtag: apc  Preferred-Value: apc  Prefix: ar
#   Type: extlang  Subtag: ajp  Deprecated: 2023-03-17  Preferred-Value: ajp  Prefix: ar
#   Type: language  Subtag: ajp  Deprecated: 2023-03-17  Preferred-Value: apc
# So `ar-apc`, `ar-ajp` and `ajp` are `apc`, `my-BU` is `my-MM` and `de-DD` is `de-DE`.
@pytest.mark.parametrize("target,available,expected", [
    ("my-MM", ["my-BU", "my-MM"], "my-MM"),
    ("my-MM", ["my-MM", "my-BU"], "my-MM"),
    ("my-BU", ["my-BU", "my-MM"], "my-MM"),
    ("my-BU", ["my-MM", "my-BU"], "my-MM"),
    ("de-DE", ["de-DD", "de-DE"], "de-DE"),
    ("de-DE", ["de-DE", "de-DD"], "de-DE"),
    ("ar-apc", ["ajp", "apc"], "apc"),
    ("ar-apc", ["apc", "ajp"], "apc"),
    ("ar-ajp", ["ajp", "apc"], "apc"),
    ("ar-ajp", ["apc", "ajp"], "apc"),
    ("ajp", ["ar-ajp", "apc"], "apc"),
])
def test_a_tie_goes_to_the_preferred_value_over_a_deprecated_subtag(target, available, expected):
    assert closest_lang(target, available) == expected


# None of these candidates has a Preferred-Value: `ak`, `tw` and `my` are
# language subtags, `aka` is no subtag, `MM` is a region subtag, and the region
# record of `SU` (Deprecated: 1992-08-30) has no Preferred-Value. `dd` after
# the private-use singleton `x` is no region subtag. The tie goes to the code
# the request names, or else to the first candidate.
@pytest.mark.parametrize("target,available,expected", [
    ("my-MM", ["my-MM"], "my-MM"),
    ("ak", ["aka", "ak"], "aka"),
    ("ak", ["ak", "aka"], "ak"),
    ("ak-GH", ["tw", "aka"], "tw"),
    ("ak-GH", ["aka", "tw"], "aka"),
    ("ru-RU", ["ru-SU", "ru-RU"], "ru-SU"),
    ("ru-RU", ["ru-RU", "ru-SU"], "ru-RU"),
    ("en", ["en-x-dd", "en-GB"], "en-x-dd"),
])
def test_a_tie_without_a_preferred_value_keeps_its_order(target, available, expected):
    assert closest_lang(target, available) == expected


# IANA Language Subtag Registry, File-Date 2026-11-18: `aka`, `fra`, `tur` and
# `fas` are no language subtags; the subtags are `ak`, `fr`, `tr` and `fa`.
# `fat` (Fanti) and `pes` (Iranian Persian) are member languages of the `ak`
# and `fa` macrolanguages. `rev` and `red` are no registered variants.
@pytest.mark.parametrize("target,available,expected", [
    ("ak-GH", ["aka", "fat"], "aka"),
    ("fa-IR", ["fas", "pes"], "fas"),
    ("fr-FR", ["fra-Latn", "fra-Latn-rev"], "fra-Latn"),
    ("tr-TR", ["tur-Latn", "tur-Latn-red"], "tur-Latn"),
])
def test_an_iso_639_alias_does_not_lose_a_tie(target, available, expected):
    """An ISO 639-2 or 639-3 code that langcodes reads as a language subtag is
    not a deprecated subtag, so it does not lose a tie to another language or
    to a tag that langcodes cannot read."""
    assert closest_lang(target, available) == expected


# IANA Language Subtag Registry, File-Date 2026-11-18. The langcodes copy
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
def test_a_deprecation_newer_than_langcodes_is_applied(tag, canonical):
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
def test_standardize_replaces_an_extlang_and_keeps_the_other_subtags(
        tag, canonical):
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


def test_no_shared_language_is_no_match():
    assert closest_lang("en-AU", ["pt-BR", "fr-FR"]) is None


# --- edge cases --------------------------------------------------------------

def test_closest_lang_empty_available_is_none():
    assert closest_lang("en-US", []) is None


def test_standardize_lang_empty_string():
    assert standardize_lang("") == ""


def test_lang_distance_is_symmetric_enough_for_identity():
    assert lang_distance("en-US", "en-US") == 0
    assert lang_distance("EN_us", "en-US") == 0


# RFC 5646 section 4.1: "The 'und' (Undetermined) primary language subtag
# identifies linguistic content whose language is not determined." Section 4.6:
# "Private use subtags have no meaning outside the private agreement between the
# parties that intend to use or exchange language tags that employ them."
_NO_LANGUAGE = ["und", "und-x-foo", "x-foo", "x-clade-abkh1242"]
_UND_WITH_LOCATION = ["und-US", "und-Latn", "und-Latn-US", "und-ZZ", "und-Zzzz", "und-PT"]
# The exact set of tags that become a bare ``und``. Stated here, not derived
# from the code under test, so the test pins the rule independently.
_COLLAPSES_TO_UND = {
    "und", "und-us", "und-latn", "und-latn-us", "und-zz", "und-zzzz", "und-pt"}


@pytest.mark.parametrize("tag", _NO_LANGUAGE + _UND_WITH_LOCATION)
@pytest.mark.parametrize("other", _NO_LANGUAGE + _UND_WITH_LOCATION + [
    "und-x-bar", "x-bar", "x-clade", "en", "en-US",
    "pt", "ab", "zxx", "mul", "qaa", "i-enochian"])
def test_a_tag_that_names_no_language_matches_only_another_no_language_tag(tag, other):
    same = tag.lower() == other.lower() or (
        tag.lower() in _COLLAPSES_TO_UND and other.lower() in _COLLAPSES_TO_UND)
    expected = 0 if same else 100
    assert lang_distance(tag, other) == expected
    assert lang_distance(other, tag) == expected
    assert lang_distance(tag, other, lects="dialect") == expected


def test_closest_lang_finds_nothing_for_a_private_use_tag():
    available = ["pt", "en", "x-clade-abkh1242", "ab", "und-US", "und-x-foo"]
    assert closest_lang("und", available) == "und-US"
    assert closest_lang("x-foo", available) is None
    assert closest_lang("x-CLADE-abkh1242", ["und", "x-foo", "x-clade-abkh1242"]) \
        == "x-clade-abkh1242"


@pytest.mark.parametrize("tag", ["und-US", "und-ZZ", "und-Zzzz", " und ", "UND"])
def test_every_spelling_of_und_finds_a_bare_und(tag):
    assert closest_lang(tag, ["en-US", "pt-PT", "x-clade-abkh1242", "und"]) == "und"


def test_und_with_a_script_or_a_region_keeps_its_distance_from_languages():
    assert lang_distance("und-Latn", "en") == 100
    assert lang_distance("und-Latn-US", "en") == 100
    assert lang_distance("und-US", "und-Latn") == 0


# RFC 5646 section 2.1: an extension (singleton ``u``, ``t`` or ``a``), a
# variant or a private-use subtag is not a script or a region. Each keeps the
# distance that the base gives it.
@pytest.mark.parametrize("tag", [
    "und-u-co-phonebk", "und-t-en", "und-1995", "und-a-foo",
    "und-lvx-foo", "und-abcde"])
def test_an_extension_or_variant_stays_distinct_from_a_bare_und(tag):
    assert lang_distance(tag, "und") == 100
    assert lang_distance("und", tag) == 100
    assert lang_distance(tag, "en") == 134
    assert lang_distance("en", tag) == 134
    assert closest_lang(tag, ["und", "en"]) is None


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
# CLDR 49 languageInfo.xml. `ar` is measured as `ar-001`, and `001` holds
# regions inside and outside `<matchVariable id="$maghreb"
# value="MA+DZ+TN+LY+MR+EH"/>`, so the largest of `ar_*_$!maghreb` 4 and
# `ar_*_*` 5 applies. `en_*_$!enUS` against `en_*_GB` is 3, and `pt_*_$americas`
# against `pt_*_$!americas` falls to `pt_*_*` 5.
REGIONAL_PAIRS = [("ar-SA", "ar", 5), ("en-AU", "en-GB", 3), ("pt-BR", "pt-PT", 5)]
# `*` 80, `*_*` 50 and `*_*_*` 4. CLDR 49 names `af` only in `<languageMatch
# desired="af" supported="en" distance="20" oneway="true"/>`, so `af` is 80
# from `nl`, and 4 more for ZA against NL.
UNRELATED_PAIRS = [("en", "zh", 134), ("es", "fr", 84),
                   ("fr-CH", "de-CH", 80), ("af", "nl", 84)]


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
def test_arabic_request_falls_back_to_msa(tag):
    assert lang_distance(tag, "arb") <= 5
    assert closest_lang(tag, ["arb", "en-US"], max_distance=5) == "arb"


@pytest.mark.parametrize("tag", ["pga", "pga-SS", "acy", "acy-CY", "pga-Latn", "mey-Latn"])
def test_a_latin_script_arabic_language_does_not_fall_back_to_msa(tag):
    """CLDR likely subtags write Juba Arabic (pga_Latn_SS) and Cypriot
    Maronite Arabic (acy_Latn_CY) in Latin script."""
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


# --- macrolanguage aliases that CLDR has removed ------------------------------

# CLDR 48 supplementalMetadata.xml, removed in CLDR 49 (CLDR-19720):
#   <languageAlias type="fat" replacement="ak" reason="macrolanguage"/> <!-- Fanti ⇒ Akan -->
# CLDR 47 supplementalMetadata.xml, removed in CLDR 48:
#   <languageAlias type="mnk" replacement="man" reason="macrolanguage"/> <!-- Mandinka ⇒ Mandingo -->
# CLDR 49 languageInfo.xml has no languageMatch for fat or mnk, so this applies:
#   <languageMatch desired="*" supported="*" distance="80"/>
CLDR_ANY_LANGUAGE_DISTANCE = 80
FORMER_ALIAS_PAIRS = [("ak-GH", "fat"), ("ak", "fat"), ("fat", "ak"), ("fat-GH", "ak-GH"),
                      ("aka", "fat"), ("fat", "tw"), ("tw", "fat"),
                      ("man", "mnk"), ("mnk", "man"), ("mnk-GM", "man-GM")]


@pytest.mark.parametrize("desired,supported", FORMER_ALIAS_PAIRS)
def test_a_former_macrolanguage_alias_is_another_language(desired, supported):
    assert lang_distance(desired, supported) >= CLDR_ANY_LANGUAGE_DISTANCE
    assert lang_matches(desired, supported) is False


@pytest.mark.parametrize("target,available,expected", [
    ("ak-GH", ["fat", "aka"], "aka"),
    ("ak-GH", ["aka", "fat"], "aka"),
    ("ak-GH", ["fat"], None),
    ("fat", ["ak", "fat"], "fat"),
    ("fat", ["ak"], None),
    ("man", ["mnk", "man"], "man"),
    ("mnk", ["man"], None),
])
def test_a_former_macrolanguage_alias_does_not_tie_with_its_macrolanguage(
        target, available, expected):
    assert closest_lang(target, available) == expected


# CLDR 49 supplementalMetadata.xml keeps:
#   <languageAlias type="tw" replacement="ak" reason="macrolanguage"/> <!-- Twi ⇒ Akan -->
@pytest.mark.parametrize("desired,supported", [("ak-GH", "tw"), ("ak", "tw"), ("tw", "ak"),
                                               ("twi", "ak"), ("cmn", "zh")])
def test_a_current_macrolanguage_alias_is_its_macrolanguage(desired, supported):
    assert lang_distance(desired, supported) == 0


# Two regions of Fanti or Mandinka are one language: the same region distance
# as two regions of Akan or Mandingo.
@pytest.mark.parametrize("desired,supported,same_shape", [
    ("fat-US", "fat-GH", ("ak-US", "ak-GH")),
    ("mnk-SN", "mnk-GM", ("man-SN", "man-GM")),
])
def test_two_regions_of_a_former_macrolanguage_alias_are_one_language(
        desired, supported, same_shape):
    assert lang_distance(desired, supported) == lang_distance(*same_shape)
    assert lang_distance(desired, supported) <= language.DEFAULT_MAX_LANGUAGE_DISTANCE
    assert closest_lang(supported, [desired]) == desired


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
# 2026-11-18), and the macrolanguage itself under its ISO 639-1 and 639-2 codes.
ARABIC_MACROLANGUAGE = ["ar", "ara"] + """aao abh abv acm acq acw acx acy adf aeb aec
    afb ajp apc apd arb arq ars ary arz auz avl ayh ayl ayn ayp bbz pga shu ssh""".split()


@pytest.mark.parametrize("code", ARABIC_MACROLANGUAGE + ["mey"])
def test_an_arabic_language_is_an_arabic_variety_in_any_script(code):
    """Hassaniyya (`mey`) is outside the macrolanguage in IANA, and Arabic in
    Glottolog 5.4 (languoid hass1238)."""
    for suffix in ("", "-Arab", "-Latn", "-EG", "-MR", "-Arab-MR", "-Latn-001", "-x-buckwalt"):
        assert is_arabic_variety(code + suffix), code + suffix


@pytest.mark.parametrize("tag", ["ar-Latn-x-buckwalt", "AR_latn", "acy", "acy-CY",
                                 "pga", "pga-SS", "mey-Latn", "ar-SA-HamedNeural"])
def test_a_latin_script_or_voice_id_tag_is_an_arabic_variety(tag):
    assert is_arabic_variety(tag)


@pytest.mark.parametrize("tag", ["und", "und-Arab", "fa", "fa-Arab-IR", "ur", "ps", "ug",
                                 "ckb", "ks-Arab", "arc", "arn", "en", "x-ar"])
def test_a_language_that_is_not_arabic_is_not_an_arabic_variety(tag):
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


# The other spoken IANA language subtags with `Macrolanguage: zh`, Mandarin
# (`cmn`) and Literary Chinese (`lzh`) left out. CLDR 49 gives each of them
# distance 10 to `zh`, as it gives Cantonese, in a block that is generated
# mechanically from macrolanguage membership:
# `<languageMatch desired="cdo" supported="zh" distance="10" oneway="true"/>`.
# linguatag overrides that distance to 100, because these languages are not
# mutually intelligible with Mandarin.
OTHER_ZH_MEMBERS = ["cdo", "cjy", "cnp", "cpx", "csp", "czh", "czo", "hnm", "luh", "mnp",
                    "sjc"]


@pytest.mark.parametrize("mandarin", ["cmn", "zh", "zh-Hans", "zh-CN"])
@pytest.mark.parametrize("suffix", ["", "-CN", "-Hans", "-Hans-CN", "-Latn"])
@pytest.mark.parametrize("member", OTHER_ZH_MEMBERS)
def test_every_other_member_of_zh_never_matches_mandarin(member, suffix, mandarin):
    """Min Dong, Jinyu, Pu-Xian, Huizhou, Min Zhong, Min Bei, the Ping
    languages, Hainanese, Leizhou and Shaojiang are separate spoken languages
    of the `zh` macrolanguage, as Cantonese is."""
    sinitic = member + suffix
    assert lang_distance(sinitic, mandarin) >= 100
    assert lang_distance(mandarin, sinitic) >= 100
    assert closest_lang(sinitic, [mandarin]) is None
    assert closest_lang(mandarin, [sinitic]) is None


@pytest.mark.parametrize("member", OTHER_ZH_MEMBERS)
def test_a_simplified_member_of_zh_finds_no_chinese_resource(member):
    assert closest_lang(f"{member}-Hans", ["cmn", "zh-Hans", "zh-Hant"]) is None


# Literary Chinese has no speakers, so the Mandarin rule leaves it out and,
# in Simplified script, it keeps the CLDR 49 distance:
# `<languageMatch desired="lzh" supported="zh" distance="10" oneway="true"/>`.
# The other direction falls to `<languageMatch desired="*" supported="*" distance="80"/>`.
@pytest.mark.parametrize("mandarin", ["cmn", "zh", "zh-Hans", "zh-CN"])
@pytest.mark.parametrize("literary", ["lzh-Hans", "lzh-Hans-CN"])
def test_literary_chinese_keeps_the_cldr_distance_to_mandarin(literary, mandarin):
    assert lang_distance(literary, mandarin) == 10
    assert lang_distance(mandarin, literary) == 80
    assert closest_lang(literary, [mandarin]) == mandarin
    assert closest_lang(mandarin, [literary]) is None


@pytest.mark.parametrize("mandarin", ["cmn", "zh", "zh-Hans", "zh-CN"])
def test_literary_chinese_in_latin_script_keeps_the_cldr_distance(mandarin):
    assert lang_distance("lzh-Latn", mandarin) == 60
    assert lang_distance(mandarin, "lzh-Latn") == 130
    assert closest_lang("lzh-Latn", [mandarin]) is None
    assert closest_lang(mandarin, ["lzh-Latn"]) is None


@pytest.mark.parametrize("literary,resource", [("lzh-Hans", "cmn"), ("lzh-TW", "zh-Hant")])
def test_literary_chinese_finds_a_chinese_resource_in_its_script(literary, resource):
    """A Chinese resource in the script and region of a Literary Chinese
    request serves it."""
    assert closest_lang(literary, ["cmn", "zh-Hans", "zh-Hant"]) == resource


# langcodes 3.5.1 carries the CLDR rule for these members. Its registry copy
# (File-Date 2021-08-06) has no `hnm`, `luh` or `sjc`, and it measures `cnp`
# and `csp` at 80 against every `zh` tag.
@pytest.mark.parametrize("member", ["cdo", "cjy", "cpx", "czh", "czo", "lzh", "mnp",
                                    "gan", "hak", "hsn", "nan", "wuu", "yue"])
def test_traditional_chinese_keeps_the_cldr_distance(member):
    """`zh` in Traditional script is outside the Mandarin rule. CLDR 49 gives
    `<languageMatch desired="cdo" supported="zh" distance="10" oneway="true"/>`,
    so the other direction falls to
    `<languageMatch desired="*" supported="*" distance="80"/>`."""
    tag = f"{member}-Hant-TW"
    assert lang_distance(tag, "zh-Hant") == 10
    assert lang_distance("zh-Hant", tag) == 80
    assert closest_lang(tag, ["cmn", "zh-Hans", "zh-Hant"]) == "zh-Hant"


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
    """A `zh-HK` resource is often Cantonese; CLDR 49 measures it at 10."""
    assert lang_distance("yue-HK", "zh-HK") == 10
    assert closest_lang("yue-HK", ["zh-HK"]) == "zh-HK"


# --- the spellings of Modern Standard Arabic ---------------------------------

def test_the_spellings_of_msa_are_identical():
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
def test_a_tag_with_an_empty_subtag_matches_nothing(malformed):
    for tag in ("ar", "ar-EG", "arb", malformed):
        assert lang_distance(malformed, tag) > 10
        assert lang_distance(tag, malformed) > 10
        assert lang_distance(malformed, tag, lects="standard") > 10
    assert closest_lang(malformed, ["ar", "ar-EG", "arz"]) is None
    assert closest_lang("ar", [malformed]) is None
