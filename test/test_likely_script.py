"""`likely_script`: the script of a tag, from its subtag or from CLDR likely-subtags."""
import pytest

from linguatag import likely_script

# CLDR 49 likelySubtags.xml (unicode-org/cldr, tag release-49):
#   <likelySubtag from="zh" to="zh_Hans_CN"/>
#   <likelySubtag from="zh_TW" to="zh_Hant_TW"/>
#   <likelySubtag from="zh_HK" to="zh_Hant_HK"/>
#   <likelySubtag from="zh_MO" to="zh_Hant_MO"/>
#   <likelySubtag from="yue_CN" to="yue_Hans_CN"/>
#   <likelySubtag from="sr" to="sr_Cyrl_RS"/>
#   <likelySubtag from="sr_ME" to="sr_Latn_ME"/>
#   <likelySubtag from="pa_PK" to="pa_Arab_PK"/>
#   <likelySubtag from="uz_AF" to="uz_Arab_AF"/>
#   <likelySubtag from="az_IR" to="az_Arab_IR"/>
#   <likelySubtag from="lzh" to="lzh_Hant_CN"/>
CLDR_49 = {
    "zh": "Hans", "zh-CN": "Hans", "zh-TW": "Hant", "zh-HK": "Hant", "zh-MO": "Hant",
    "yue-CN": "Hans", "sr": "Cyrl", "sr-RS": "Cyrl", "sr-ME": "Latn", "pa-PK": "Arab",
    "uz-AF": "Arab", "az-IR": "Arab", "lzh": "Hant",
}


@pytest.mark.parametrize("tag, script", sorted(CLDR_49.items()))
def test_a_tag_with_no_script_takes_the_cldr_likely_script_of_its_region(tag, script):
    assert likely_script(tag) == script


@pytest.mark.parametrize("tag, script", [("zh-Hant", "Hant"), ("zh-Hans-TW", "Hans"), ("sr-Latn-RS", "Latn"),
                                         ("en-Dsrt-US", "Dsrt")])
def test_a_script_subtag_wins_over_the_likely_script(tag, script):
    assert likely_script(tag) == script


def test_a_bare_tag_takes_its_default_region_first():
    # `OVERRIDES` gives a bare `yue` the region CN, where CLDR gives HK.
    assert likely_script("yue") == likely_script("yue-CN") == "Hans"


def test_the_package_table_corrects_the_langcodes_snapshot():
    # CLDR 49: <likelySubtag from="hyw" to="hyw_Armn_AM" origin="sil1"/>; langcodes 3.5.1 gives Latn.
    assert likely_script("hyw") == "Armn"


def test_an_underscore_tag_is_standardized_first():
    assert likely_script("zh_TW") == "Hant"


@pytest.mark.parametrize("tag", ["zzz", "qaa", "und", "123"])
def test_a_language_with_no_likely_subtags_has_no_script(tag):
    assert likely_script(tag) is None


@pytest.mark.parametrize("tag", ["", "a", "en--US", "-en"])
def test_a_tag_that_langcodes_cannot_parse_has_no_script(tag):
    assert likely_script(tag) is None


def test_without_langcodes_only_the_package_table_gives_a_script(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "langcodes", None)
    monkeypatch.setitem(sys.modules, "langcodes.data_dicts", None)
    assert likely_script("zh-TW") is None
    assert likely_script("zh-Hant") == "Hant"
    assert likely_script("hyw") == "Armn"
