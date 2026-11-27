import pytest

from linguatag import LanguageTagError, parse_tag, standardize_lang


@pytest.mark.parametrize("locale, expected", [
    ("ar_SA.UTF-8", "ar-SA"), ("pt_BR.utf8", "pt-BR"), ("en_US@euro", "en-US"), ("en_US.UTF-8@euro", "en-US"),
    ("sr_RS@latin", "sr-Latn-RS"), ("ca_ES@valencia", "ca-ES-valencia"), ("C.UTF-8", "und"), ("POSIX", "und"), ("C", "und"),
])
def test_a_posix_locale_reads_as_its_language(locale, expected):
    assert standardize_lang(locale) == expected


@pytest.mark.parametrize("tag, expected", [
    ("an-x-benasques", "an-x-benasques"), ("ar-Latn-buckwalter", "ar-Latn"), ("bs-Cyrl-BA-Latn", "bs-Cyrl-BA"),
    ("fr-BE-", "fr-BE"), ("ar_SA.UTF-8", "ar-SA"), ("pt-PT-x-Porto", "pt-PT-x-porto"), ("C", "und"),
])
def test_the_tolerant_reader_keeps_the_well_formed_prefix(tag, expected):
    assert str(parse_tag(tag, strict=False)) == expected


def test_the_tolerant_reader_gives_the_parts():
    tag = parse_tag("bs-Cyrl-BA-Latn", strict=False)
    assert (tag.language, tag.script, tag.region) == ("bs", "Cyrl", "BA")
    assert parse_tag("an-x-benasques", strict=False).private == "x-benasques"


@pytest.mark.parametrize("tag", ["an-x-benasques", "bs-Cyrl-BA-Latn", "fr-BE-", "ar_SA.UTF-8"])
def test_the_strict_reader_still_refuses(tag):
    with pytest.raises(LanguageTagError):
        parse_tag(tag)


@pytest.mark.parametrize("tag", ["", "123", "-"])
def test_the_tolerant_reader_refuses_a_string_with_no_language(tag):
    with pytest.raises(LanguageTagError):
        parse_tag(tag, strict=False)
