"""A tag over `MAX_TAG_LENGTH` names no language, and it costs no parsing."""
import time

import pytest
from langcodes import standardize_tag

from linguatag import (MAX_TAG_LENGTH, closest_lang, default_region, lang_distance, lang_matches,
                       lect_steps, standardize_lang, with_default_region)
from linguatag.lects import private_use, without_private_use
from linguatag.standardize import _stable_form

# A parse of each prefix of the long tags below is quadratic and takes minutes.
TIME_BOUND = 1.0

AT_THE_LIMIT = "en" + "-Latn" * 50 + "-ab"
OVER_THE_LIMIT = AT_THE_LIMIT + "c"
LONG_TAGS = [OVER_THE_LIMIT, "en" + "-Latn" * 1200, "en" + "-Latn" * 20_000,
             "en" + "-x" * 50_000, "a" * 100_000, "en_" * 30_000 + "en"]


def _private_use_tag(language: str, length: int) -> str:
    """`language` with private-use subtags of eight letters or fewer, `length` long."""
    tag = language + "-x" + "-abcdefgh" * 27
    return tag + "-" + "a" * (length - len(tag) - 1)


# `ar-001` is longer than each of these spellings, so Modern Standard Arabic is
# the one family that a rewrite can push over the limit.
ARABIC_AT_THE_LIMIT = [_private_use_tag(language, length) for language in ("ar", "arb")
                       for length in range(250, MAX_TAG_LENGTH + 1)]
ARABIC_OVER_THE_LIMIT = [_private_use_tag(language, MAX_TAG_LENGTH + 1) for language in ("ar", "arb")]
# The default region takes each of these past the limit.
LATIN_ARABIC_AT_THE_LIMIT = [_private_use_tag("ar-Latn", 254), _private_use_tag("ar-Latn", 255),
                             _private_use_tag("arz-Latn", 255)]


def _timed(function, *args, **kwargs):
    start = time.perf_counter()
    result = function(*args, **kwargs)
    elapsed = time.perf_counter() - start
    assert elapsed < TIME_BOUND, f"{function.__name__} took {elapsed:.2f} s"
    return result


def test_the_limit_tags_have_the_lengths_they_claim():
    assert MAX_TAG_LENGTH == 255
    assert len(AT_THE_LIMIT) == MAX_TAG_LENGTH
    assert len(OVER_THE_LIMIT) == MAX_TAG_LENGTH + 1


def test_a_tag_at_the_limit_is_standardized():
    standard = standardize_tag("en-ab")
    assert _timed(standardize_lang, AT_THE_LIMIT) == standard


def test_a_tag_at_the_limit_is_measured():
    assert _timed(lang_distance, AT_THE_LIMIT, "en-AB") == 0
    assert _timed(lang_distance, AT_THE_LIMIT, "en") == lang_distance("en-ab", "en")
    assert _timed(closest_lang, AT_THE_LIMIT, ["fr", "en-AB"]) == "en-AB"
    assert _timed(closest_lang, "en-AB", ["fr", AT_THE_LIMIT]) == AT_THE_LIMIT


@pytest.mark.parametrize("tag", ARABIC_AT_THE_LIMIT, ids=lambda tag: f"{tag[:3]}{len(tag)}")
def test_arabic_at_the_limit_is_measured_as_a_short_tag(tag):
    short = tag.split("-x-")[0] + "-x-foo"
    assert standardize_lang(tag) == tag
    assert lang_distance(tag, "ar") == lang_distance(short, "ar") == 0
    assert lang_distance("ar", tag) == lang_distance("ar", short) == 0
    assert lang_distance("arz", tag) == lang_distance("arz", short) == 5
    assert lang_distance(tag, "ar-x-bar", lects="dialect") == lang_distance(short, "ar-x-bar", lects="dialect")
    assert closest_lang(tag, ["fr", "ar"]) == "ar"
    assert closest_lang("ar", ["fr", tag]) == tag


@pytest.mark.parametrize("tag", ARABIC_OVER_THE_LIMIT, ids=lambda tag: tag[:3])
def test_arabic_over_the_limit_names_no_language(tag):
    assert len(tag) == MAX_TAG_LENGTH + 1
    assert lang_distance(tag, "ar") == lang_distance("ar", tag) == 100
    assert closest_lang(tag, ["fr", "ar"]) is None


@pytest.mark.parametrize("tag", LATIN_ARABIC_AT_THE_LIMIT, ids=lambda tag: f"{tag[:8]}{len(tag)}")
def test_a_region_past_the_limit_keeps_the_script_of_the_tag(tag):
    short = tag.split("-x-")[0] + "-x-foo"
    assert len(with_default_region(tag)) > MAX_TAG_LENGTH
    assert lang_distance(short, "ar") > 5
    assert lang_distance(tag, "ar") == lang_distance(short, "ar")


def test_arabic_dialects_differ_only_when_lects_asks():
    assert lang_distance("ar-x-foo", "ar-x-bar") == 0
    assert lang_distance("ar-x-foo", "ar-x-bar", lects="dialect") == 2
    assert lang_distance("ar-x-foo", "ar-x-foo", lects="dialect") == 0
    assert closest_lang("ar-x-foo", ["ar-x-bar", "ar-x-foo"], lects="dialect") == "ar-x-foo"


@pytest.mark.parametrize("tag", LONG_TAGS, ids=lambda tag: str(len(tag)))
def test_a_longer_tag_names_no_language(tag):
    assert _timed(standardize_lang, tag) == ""
    assert _timed(with_default_region, tag) == ""
    assert _timed(default_region, tag) is None
    assert _timed(private_use, tag) == ()
    assert _timed(without_private_use, tag) == ""


@pytest.mark.parametrize("tag", LONG_TAGS, ids=lambda tag: str(len(tag)))
def test_a_longer_tag_matches_nothing(tag):
    assert _timed(lang_distance, tag, "en") == 100
    assert _timed(lang_distance, "en", tag) == 100
    assert _timed(lang_distance, tag, tag) == 100
    assert _timed(lang_distance, tag, "en", lects="standard") == 100
    assert _timed(lang_matches, tag, "en") is False
    assert _timed(lect_steps, tag, "en") is None
    assert _timed(closest_lang, tag, ["en", "fr"]) is None
    assert _timed(closest_lang, "en", [tag, "en-GB"]) == "en-GB"
    assert _timed(closest_lang, "en", [tag] * 20) is None


def test_a_longer_tag_stays_out_of_the_cache():
    before = _stable_form.cache_info()
    for tag in LONG_TAGS:
        standardize_lang(tag)
    assert _stable_form.cache_info() == before


def test_a_standard_form_over_the_limit_names_no_language():
    """`sh` is `sr-Latn`, so a tag at the limit can grow past it. The second
    call on that form must not disagree with the first."""
    tag = "sh-x" + "-abcdefgh" * 27 + "-" + "a" * (MAX_TAG_LENGTH - 4 - 9 * 27 - 1)
    assert len(tag) == MAX_TAG_LENGTH
    assert _timed(standardize_lang, tag) == ""
