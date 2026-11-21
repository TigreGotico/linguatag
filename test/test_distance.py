"""The UTS #35 section 4.4 language matching distance over the CLDR 49 data.

Each expected value is the sum of the CLDR 49 ``languageMatch`` distances
that the quoted rules give, after CLDR 49 likely subtags
(``linguatag/data/language_matching.json``, ``likely_subtags.json``).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import linguatag
from linguatag import closest_lang, lang_distance
from linguatag.distance import is_paradigm, tag_distance

DATA = Path(linguatag.__file__).parent / "data"


@pytest.mark.parametrize("name, source", [
    ("language_matching.json",
     "CLDR 49, cldr-json cldr-core/supplemental/languageMatching.json, written-new"),
    ("territory_containment.json",
     "CLDR 49, cldr-json cldr-core/supplemental/territoryContainment.json"),
])
def test_each_data_file_names_its_source(name, source):
    assert json.loads((DATA / name).read_text(encoding="utf-8"))["source"] == source


# CLDR 49 languageInfo.xml:
#   <matchVariable id="$enUS" value="AS+CA+GU+MH+MP+PH+PR+UM+US+VI"/>
#   <languageMatch desired="en_*_$enUS" supported="en_*_$enUS" distance="4"/>
#   <languageMatch desired="en_*_$!enUS" supported="en_*_GB" distance="3"/>
#   <languageMatch desired="en_*_*" supported="en_*_*" distance="5"/>
# Canada and the Philippines are in the US English cluster: 4 from en-US and
# 5 from en-GB. langcodes 3.5.1 writes the cluster without CA and PH.
@pytest.mark.parametrize("tag", ["en-CA", "en-PH"])
def test_canada_and_the_philippines_are_in_the_us_english_cluster(tag):
    assert lang_distance(tag, "en-US") == 4
    assert lang_distance(tag, "en-GB") == 5
    assert closest_lang(tag, ["en-GB", "en-US"]) == "en-US"


# "<languageMatch desired="en_*_$!enUS" supported="en_*_GB" distance="3"/>":
# "So when matching desired=[en-SA] against [en-GU en en-IN en-GB], the value
# en-GB is returned."
def test_english_outside_the_us_cluster_prefers_british_english():
    assert lang_distance("en-SA", "en-GB") == 3
    assert lang_distance("en-SA", "en-IN") == 4
    assert lang_distance("en-SA", "en-GU") == 5
    assert closest_lang("en-SA", ["en-GU", "en-IN", "en-GB"]) == "en-GB"


# UTS #35 section 4.4: "desired=[es-419] matches to {es-MX} more closely than
# to {es}. Vice versa: {es-MX} matches more closely to {es-419} than to {es}.
# But es-MX should also match more closely to es-419 than to any of the
# es-419 sublocales, such as {es_CR}." `<matchVariable id="$americas"
# value="019"/>`, `<languageMatch desired="es_*_$americas"
# supported="es_*_$americas" distance="4"/>`, `es_*_*` 5, and
# `<paradigmLocales locales="en en_GB es es_419 pt_BR pt_PT"/>`.
def test_latin_american_spanish_matches_es_419_first():
    assert lang_distance("es-419", "es-MX") == 4
    assert lang_distance("es-419", "es") == 5
    assert lang_distance("es-MX", "es-419") == 4
    assert lang_distance("es-MX", "es") == 5
    assert closest_lang("es-MX", ["es-CR", "es-419"]) == "es-419"
    assert closest_lang("es-MX", ["es", "es-419"]) == "es-419"


@pytest.mark.parametrize("tag, paradigm", [
    ("en", True), ("en-US", True), ("en-GB", True), ("es", True), ("es-ES", True),
    ("es-419", True), ("pt-BR", True), ("pt-PT", True), ("es-MX", False), ("en-CA", False),
    ("pt-AO", False)])
def test_the_paradigm_locales(tag, paradigm):
    assert is_paradigm(tag) is paradigm


# `<languageMatch desired="gsw" supported="de" distance="4" oneway="true"/>`;
# gsw is gsw-Latn-CH and de is de-Latn-DE, and `*_*_*` gives 4 for the
# region. The other way no rule names the pair: `*` gives 80.
def test_a_one_way_rule_matches_in_one_direction():
    assert tag_distance("gsw", "de") == 8
    assert tag_distance("de", "gsw") == 84


# `<languageMatch desired="sr_Latn" supported="sr_Cyrl" distance="5"/>`; the
# script rule is two-way.
def test_a_script_rule_of_one_language():
    assert tag_distance("sr-Latn-RS", "sr-Cyrl-RS") == 5
    assert tag_distance("sr-Cyrl-RS", "sr-Latn-RS") == 5


# UTS #35 section 4.4: "nn-DE and nb-FR ... are first maximized to
# nn-Latn-DE and nb-Latn-FR". CLDR 49: `<languageMatch desired="nn"
# supported="nb" distance="20"/>` and `*_*_*` 4 for DE against FR.
def test_the_uts_35_nynorsk_example():
    assert tag_distance("nn-DE", "nb-FR") == 24


# CLDR 49 names Serbo-Croatian in `<languageMatch desired="sh" supported="hr"
# distance="4"/>` and `sh` => `sr` 4, but `<languageAlias type="sh"
# replacement="sr_Latn" reason="legacy"/>` means a canonical tag is never
# `sh`. No rule names `hr` with `sr`: `*` 80, and HR against RS `*_*_*` 4.
# `<languageMatch desired="hr" supported="bs" distance="4"/>` is two-way.
def test_croatian_and_serbian_are_two_languages():
    assert lang_distance("hr", "sr-Latn") == lang_distance("sr-Latn", "hr") == 84
    assert lang_distance("hr", "bs") == lang_distance("bs", "hr") == 8


# `<matchVariable id="$maghreb" value="MA+DZ+TN+LY+MR+EH"/>`,
# `ar_*_$maghreb` 4, `ar_*_$!maghreb` 4, `ar_*_*` 5. `001` contains regions
# in and out of `$maghreb`, so it is 5 from both sides, the largest distance
# over its clusters. `419` contains only regions of `019`, so `$americas`
# holds it.
def test_a_macroregion_is_in_each_cluster_of_its_regions():
    assert tag_distance("ar-MA", "ar-DZ") == 4
    assert tag_distance("ar-MA", "ar-EG") == 5
    assert tag_distance("ar-001", "ar-MA") == 5
    assert tag_distance("ar-001", "ar-EG") == 5
    assert tag_distance("es-419", "es-MX") == 4
    assert tag_distance("es-419", "es-ES") == 5


# UTS #35 section 4.4: "if the desired base language is und, the language
# matcher should not apply likely subtags to it." `*` 80, `*_*` 50, `*_*_*` 4.
def test_und_is_not_maximized():
    assert tag_distance("und", "en") == 134


# RFC 5646 section 2.2.1: "The single-character subtag 'x' as the primary subtag
# indicates that the language tag consists solely of subtags whose meaning is
# defined by private agreement." Such a tag is its own language: `*` 80.
def test_a_private_use_tag_is_not_und():
    assert tag_distance("x-foo", "und") == 80
    assert tag_distance("und", "x-foo") == 80
    assert tag_distance("x-foo", "x-bar") == 80
    assert tag_distance("x-foo", "X-Foo") == 0
    assert tag_distance("x-foo", "en") == 134


_PAIRS = [("en-CA", "en-US"), ("en-CA", "en-GB"), ("es-MX", "es-419"), ("sr-Latn", "hr"),
          ("gsw", "de"), ("nb", "no"), ("ar-EG", "ar"), ("zh-HK", "zh-TW"), ("zzz", "en")]
_WITHOUT_LANGCODES = """
import builtins, json, sys
real_import = builtins.__import__
def refuse(name, *args, **kwargs):
    if name == "langcodes" or name.startswith("langcodes."):
        raise ImportError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = refuse
from linguatag import closest_lang, lang_distance
pairs = json.loads(sys.argv[1])
print(json.dumps([[lang_distance(a, b), closest_lang(a, [b, "en-US"])] for a, b in pairs]))
"""


def test_the_distance_is_the_same_without_langcodes():
    """Output depends on spec, input and explicit config, never on what is installed."""
    here = [[lang_distance(a, b), closest_lang(a, [b, "en-US"])] for a, b in _PAIRS]
    without = subprocess.run([sys.executable, "-c", _WITHOUT_LANGCODES, json.dumps(_PAIRS)],
                             check=True, capture_output=True, text=True).stdout
    assert json.loads(without) == here
