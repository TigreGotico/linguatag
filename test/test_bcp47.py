"""BCP 47 parsing, canonicalization and Add Likely Subtags, from the CLDR 49 and
IANA data this package carries.

Each expected value quotes its source: RFC 5646, UTS #35 (revision 79, CLDR
49), the CLDR 49 cldr-json supplemental files, or the IANA Language Subtag
Registry (File-Date 2026-11-18).
"""
import copy
import json
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

import linguatag
from linguatag import default_region, is_arabic_variety, likely_script, standardize_lang, with_default_region
from linguatag.bcp47 import LanguageTagError, load_data, maximize, parse, registry, standardize
from linguatag.lects import lect_steps

DATA = Path(linguatag.__file__).parent / "data"


@pytest.mark.parametrize("name, source", [
    ("likely_subtags.json", "CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json"),
    ("aliases.json", "CLDR 49, cldr-json cldr-core/supplemental/aliases.json"),
    ("subtags.json", "IANA Language Subtag Registry, File-Date: 2026-11-18"),
    ("language_subtags.json", "IANA Language Subtag Registry, File-Date: 2026-11-18"),
])
def test_each_data_file_names_its_source(name, source):
    assert json.loads((DATA / name).read_text(encoding="utf-8"))["source"] == source


def test_a_caller_cannot_change_package_data():
    """The loader shares one read-only view, not a dict a caller can edit."""
    data = load_data("lineage.json")
    assert data is load_data("lineage.json")
    with pytest.raises(TypeError):
        data["parents"]["pt-x-central"] = "pt-x-minhoto"
    assert "pt-x-central" not in load_data("lineage.json")["parents"]
    assert lect_steps("pt-x-central", "pt-x-minhoto") == 2


def test_a_caller_cannot_change_a_list_in_package_data():
    data = load_data("language_matching.json")
    with pytest.raises(AttributeError):
        data["paradigm_locales"].append("zz")
    assert "zz" not in load_data("language_matching.json")["paradigm_locales"]


def test_a_caller_cannot_change_a_registry_record():
    with pytest.raises(TypeError):
        registry("extlang")["aao"]["preferred"] = "zz"
    assert registry("extlang")["aao"]["preferred"] == "aao"


def test_a_caller_can_still_copy_and_serialize_package_data():
    data = load_data("lineage.json")
    assert isinstance(data, dict) and isinstance(data["parents"], dict)
    assert json.loads(json.dumps(data)) == json.loads((DATA / "lineage.json").read_text())
    assert pickle.loads(pickle.dumps(data)) == data
    copied = copy.deepcopy(data)
    assert type(copied) is dict
    copied["parents"]["pt-x-central"] = "pt-x-minhoto"
    assert "pt-x-central" not in data["parents"]


# RFC 5646 section 2.1: `language = 2*3ALPHA ["-" extlang] / 4ALPHA / 5*8ALPHA`,
# `variant = 5*8alphanum / (DIGIT 3alphanum)`, `privateuse = "x" 1*("-" (1*8alphanum))`;
# section 2.2.6: "Each singleton subtag MUST appear at most one time in each tag".
@pytest.mark.parametrize("tag", ["", "a", "en--US", "-en", "x", "x-", "en-a-b-foo", "en-u-co-u-ca",
                                 "abcdefghi", "en-US-HiuMaanNeural", "zh-tw-hant", "ar-٠٠١"])
def test_a_tag_that_is_not_well_formed_raises(tag):
    with pytest.raises(LanguageTagError):
        parse(tag)


@pytest.mark.parametrize("tag, expected", [
    ("abcde", "abcde"), ("de-DE-1901", "de-DE-1901"), ("zh-hant-tw", "zh-Hant-TW"),
    ("es_419", "es-419"), ("x-dothraki", "x-dothraki"), ("en-x-Pig-Latin", "en-x-pig-latin"),
    ("i-klingon", "i-klingon"), ("root", "und"),
])
def test_parse_keeps_the_subtags_in_their_bcp47_case(tag, expected):
    assert str(parse(tag)) == expected


# RFC 5646 section 3: the registry "contains a comprehensive list of all of
# the subtags valid in language tags". IANA, File-Date 2026-11-18:
# "Subtag: 1995 ... Description: Uzbek Latin orthography of 1995 ... Prefix: uz
# ... Prefix: uz-Latn", and the same for "Subtag: 2026".
@pytest.mark.parametrize("variant", ["1995", "2026"])
def test_the_uzbek_latin_orthography_variants_are_registered(variant):
    assert registry("variant")[variant] == {"prefix": ("uz", "uz-Latn")}
    for tag in (f"uz-{variant}", f"uz-Latn-{variant}", f"uz-Latn-UZ-{variant}"):
        assert str(parse(tag)) == tag
        assert standardize_lang(tag) == tag


# RFC 5646 section 4.5, step 1: "Extension sequences are ordered into
# case-insensitive ASCII order by singleton subtag."
def test_extensions_are_ordered_by_singleton():
    assert standardize("en-b-warble-a-babble") == "en-a-babble-b-warble"


@pytest.mark.parametrize("tag, expected", [
    # IANA: "Tag: sgn-NO ... Description: Norwegian Sign Language ... Preferred-Value: nsl".
    # CLDR 49 gives `nsi`, which the registry names "Nigerian Sign Language".
    ("sgn-NO", "nsl"),
    # IANA: "Tag: zh-guoyu ... Preferred-Value: cmn".
    ("zh-guoyu", "cmn"),
    # IANA: "Subtag: bh ... Deprecated: 2026-06-14 ... Preferred-Value: bih".
    ("bh", "bih"),
    ("bih", "bih"),
    # IANA: "Subtag: heploc ... Preferred-Value: alalc97 ... Prefix: ja-Latn-hepburn";
    # UTS #35 Annex C, 4. Replacement: "ja-Latn-fonipa-hepburn-heploc" gives
    # "ja-Latn-alalc97-fonipa".
    ("ja-Latn-hepburn-heploc", "ja-Latn-alalc97"),
    ("ja-Latn-fonipa-hepburn-heploc", "ja-Latn-alalc97-fonipa"),
    # CLDR 49 aliases.json: "polytoni": {"_reason": "deprecated", "_replacement": "polyton"}.
    ("el-polytoni", "el-polyton"),
    # CLDR 49 aliases.json scriptAlias: "Qaai": {"_replacement": "Zinh"}.
    ("und-Qaai", "und-Zinh"),
    # CLDR 49 aliases.json: "und-arevela": {"_reason": "deprecated", "_replacement": "und"};
    # IANA: "Subtag: arevela ... Comments: Preferred tag is hy".
    ("hy-arevela", "hy"),
    # CLDR 49 aliases.json: "nbx": {"_reason": "deprecated", "_replacement": "gll"}.
    ("nbx", "gll"),
])
def test_a_deprecated_form_takes_its_replacement(tag, expected):
    assert standardize_lang(tag) == expected


# UTS #35 Annex C, Territory Exception: "look up the most likely territory for
# the base language code ... If that likely territory is in the list of
# replacements, use it. Otherwise, use the first territory in the list."
# CLDR 49 aliases.json: "SU": "RU AM AZ BY EE GE KZ KG LV LT MD TJ TM UA UZ";
# likelySubtags.json: "hy": "hy-Armn-AM", "uz": "uz-Latn-UZ", "en": "en-Latn-US".
@pytest.mark.parametrize("tag, expected", [
    ("ru-SU", "ru-RU"), ("hy-SU", "hy-AM"), ("uz-SU", "uz-UZ"), ("en-SU", "en-RU")])
def test_a_region_that_split_takes_the_likely_one_of_the_language(tag, expected):
    assert standardize_lang(tag) == expected


@pytest.mark.parametrize("tag, expected", [
    # UTS #35 section 4.3, Example1: "Input is ZH-ZZZZ-SG. ... Look up zh, and get the
    # match (zh_Hans_CN). Substitute SG, and return zh_Hans_SG."
    ("ZH-ZZZZ-SG", "zh-Hans-SG"),
    # CLDR 49 likelySubtags.json: "zh-TW": "zh-Hant-TW", "zh-Hant": "zh-Hant-TW".
    ("zh-TW", "zh-Hant-TW"), ("zh-Hant", "zh-Hant-TW"),
    # CLDR 49 aliases.json: "cmn": {"_reason": "macrolanguage", "_replacement": "zh"}.
    ("cmn", "zh-Hans-CN"),
    # A full tag is returned as it is (section 4.3 step 1.4).
    ("sr-Cyrl-ME", "sr-Cyrl-ME"),
])
def test_maximize_fills_the_likely_subtags(tag, expected):
    assert str(maximize(tag)) == expected


# UTS #35 section 4.3: "An implementation may choose to exclude language tags
# with the language subtag "und" from the following operation", and "If there
# is no match, signal an error and stop."
@pytest.mark.parametrize("tag", ["und", "und-TW", "zzz", "x-foo", "en--US"])
def test_maximize_gives_none_for_und_an_unknown_language_or_no_tag(tag):
    assert maximize(tag) is None


@pytest.mark.parametrize("tag, script", [
    # CLDR 49 likelySubtags.json entries; langcodes 3.5.1 gives the second script.
    ("ku-IQ", "Arab"),   # "ku-IQ": "ku-Arab-IQ"; langcodes Latn
    ("nan-TW", "Hant"),  # "nan-TW": "nan-Hant-TW"; langcodes Hans
    ("hak-TW", "Hant"),  # "hak-TW": "hak-Hant-TW"; langcodes Hans
    ("grc", "Grek"),     # "grc": "grc-Grek-GR"; langcodes Cprt
    ("cdo", "Hans"),     # "cdo": "cdo-Hans-CN"; langcodes Latn
])
def test_the_likely_script_is_the_cldr_49_script(tag, script):
    assert likely_script(tag) == script


@pytest.mark.parametrize("tag, region", [
    ("apc", "SY"),   # "apc": "apc-Arab-SY"; langcodes ZZ
    ("pap", "CW"),   # "pap": "pap-Latn-CW"; langcodes AW
    ("mrh", "IN"),   # "mrh": "mrh-Latn-IN"; langcodes has no entry
    # CLDR 49 aliases.json: "tw": {"_reason": "macrolanguage", "_replacement": "ak"};
    # likelySubtags.json: "ak": "ak-Latn-GH".
    ("tw", "GH"),
    # Modern Standard Arabic takes the override of `ar`: ("Arab", "001").
    ("arb", "001"),
])
def test_the_default_region_is_the_cldr_49_region(tag, region):
    assert default_region(tag) == region


TAGS = ["en", "en_us", "pt", "zh-TW", "zh-Hant", "yue", "ar", "arb", "ar-EG", "ku-IQ", "sr-ME", "iw",
        "eng", "zh-yue", "zh-min-nan", "sgn-US", "i-klingon", "x-foo", "und-Arab", "hyw", "lzh",
        "mey-SN", "gl-x-central", "zh-HK-HiuMaanNeural", "en--US", "tl", "cmn", "bh"]
_WITHOUT_LANGCODES = """
import builtins, json, sys
real_import = builtins.__import__
def refuse(name, *args, **kwargs):
    if name == "langcodes" or name.startswith("langcodes."):
        raise ImportError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = refuse
from linguatag import default_region, is_arabic_variety, likely_script, standardize_lang, with_default_region
functions = (standardize_lang, default_region, with_default_region, likely_script, is_arabic_variety)
print(json.dumps([[f(tag) for f in functions] for tag in sys.argv[1:]]))
"""


def test_the_output_is_the_same_without_langcodes():
    """Output depends on spec, input and explicit config, never on what is installed."""
    functions = (standardize_lang, default_region, with_default_region, likely_script,
                 is_arabic_variety)
    here = [[f(tag) for f in functions] for tag in TAGS]
    without = subprocess.run([sys.executable, "-c", _WITHOUT_LANGCODES, *TAGS], check=True,
                             capture_output=True, text=True).stdout
    assert json.loads(without) == here
