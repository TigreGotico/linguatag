import pytest

from linguatag import standard_tag, standardize_lang


@pytest.mark.parametrize("tag, expected", [
    ("pt-PT-x-porto", "pt-PT"), ("en-GB-oed", "en-GB"), ("cmn-x-beijing", "zh"), ("zh-Hant-TW", "zh-Hant-TW"),
    ("sr-Latn-RS", "sr-Latn-RS"), ("pt_BR.UTF-8", "pt-BR"), ("eu-FR-x-zuberera", "eu-FR"), ("de-DE-u-co-phonebk", "de-DE"),
    ("sh", "sr-Latn"), ("iw", "he"), ("zh-HK-HiuMaanNeural", "zh-HK"), ("x-foo", "und"), ("", "und")])
def test_the_standard_tag_is_language_script_and_region(tag, expected):
    assert standard_tag(tag) == expected


@pytest.mark.parametrize("tag, expected", [("cmn-x-beijing", "zh"), ("cmn-TW-x-foo", "zh-TW"), ("arb-x-foo", "ar"),
                                           ("pt-PT-x-porto", "pt-PT-x-porto"), ("arz-x-cairo", "arz-x-cairo")])
def test_a_macrolanguage_fold_drops_the_private_lect_of_the_member(tag, expected):
    assert standardize_lang(tag, macro=True) == expected
