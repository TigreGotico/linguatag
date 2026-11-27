# Reference

<!-- agent-hint
covers: the signature, the return value and one example of each name in linguatag.__all__
source: linguatag/__init__.py:__all__, linguatag/_standardize.py, linguatag/_regions.py, linguatag/_matching.py, linguatag/_lects.py, linguatag/_lineage.py, linguatag/_writing_systems.py
generated: no
verify: python scripts/check_doc_page.py docs/reference.md
see: getting-started.md, matching.md
-->

This page gives the signature and one example for each of the 27 names that `from linguatag import ...` offers. Each name has a page that explains its rules, and the table at the end links it.

## Normalise a tag

`standardize_lang(tag: str) -> str` puts a tag in one canonical form. It never raises. For a string that is not a well-formed tag, it replaces the language and the extlang and gives each subtag its BCP 47 case.

```python
from linguatag import standardize_lang

print(standardize_lang("EN_us"))              # en-US
print(standardize_lang("iw"))                 # he
print(standardize_lang("zh-HK-HiuMaanNeural"))  # zh-HK-hiumaanneural
```

## Read the subtags of a tag

`parse_tag(tag: str) -> LanguageTag` gives the subtags of a tag and replaces nothing. It reads underscores as hyphens and ignores case. `LanguageTag` has the fields `language`, `extlangs`, `script`, `region`, `variants`, `extensions`, `private` and `whole`. `whole` holds a private-use tag or a grandfathered tag that has no replacement. For a string that is not a well-formed tag, `parse_tag` raises `LanguageTagError`, a `ValueError`.

```python
from linguatag import LanguageTagError, parse_tag

tag = parse_tag("pt_latn_pt")
print(tag.language, tag.script, tag.region)   # pt Latn PT
print(parse_tag("x-foo").whole)               # x-foo
try:
    parse_tag("pt--PT")
except LanguageTagError:
    print("not a tag")                        # not a tag
```

## Region and script of a bare tag

`default_region(tag: str) -> Optional[str]` gives the region where the language started and is still spoken. It returns `None` for a language that has none.

`with_default_region(tag: str) -> str` gives the standardized tag with that region inserted. A variant or a private-use subtag stays after the region. A tag with no default region comes back standardized and otherwise unchanged.

`likely_script(tag: str) -> Optional[str]` gives the ISO 15924 script of the tag, or the script that CLDR 49 expects for it. It returns `None` for a string that is not a language tag, for `und` and for an unknown language.

```python
from linguatag import default_region, likely_script, with_default_region

print(default_region("en"))                # GB
print(with_default_region("zh-Hant"))      # zh-Hant-TW
print(with_default_region("gl-x-central")) # gl-ES-x-central
print(with_default_region("xx"))           # xx
print(likely_script("ar"))                 # Arab
print(likely_script("und"))                # None
```

`language_scope(tag: str) -> Optional[str]` gives the IANA scope of the primary language subtag: `"language"`, `"macrolanguage"`, `"collection"` (a language family), `"special"` (`mul`, `und`, `zxx`, `mis`) or `"private-use"`. It returns `None` for a subtag that the IANA registry does not hold, such as the retired ISO 639-3 code `mol`. Give the subtag as the registry spells it: `pt`, not `por`.

```python
from linguatag import language_scope

print(language_scope("itc"))   # collection
print(language_scope("zh"))    # macrolanguage
print(language_scope("en-US")) # language
print(language_scope("mol"))   # None
```

`OVERRIDES` maps a language to the `(script, region)` that linguatag uses in place of the CLDR value. Each entry cites its source in `linguatag/_regions.py`.

```python
from linguatag import OVERRIDES

print(sorted(OVERRIDES))           # ['ar', 'en', 'pt', 'ur', 'yue']
print(OVERRIDES["pt"])             # ('Latn', 'PT')
```

`maximize(tag: str) -> Optional[LanguageTag]` adds the likely subtags of CLDR 49 (UTS #35 section 4.3) with no overrides, so `en` gives `US`, not the default region `GB`. It returns `None` for `und` and for a language with no CLDR entry.

```python
from linguatag import maximize

print(maximize("zh-TW"))   # zh-Hant-TW
print(maximize("en"))      # en-Latn-US
print(maximize("und"))     # None
```

## Measure and pick

`lang_distance(desired: str, supported: str, lects: Optional[str] = None) -> int` gives the CLDR 49 matching distance. `0` is identical, and a value above `DEFAULT_MAX_LANGUAGE_DISTANCE` is no usable match. The first argument is the request, because the distance is one-way.

`lang_matches(a: str, b: str, max_distance: int = 10) -> bool` is `lang_distance(a, b) <= max_distance`.

`closest_lang(target: str, available: Sequence[str], max_distance: int = 10, lects: Optional[str] = None) -> Optional[str]` returns the entry of `available` with the smallest distance, as written in the list. It returns `None` when no entry is within `max_distance`. `available` is read once, so an iterator works.

```python
from linguatag import DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang, lang_distance, lang_matches

print(DEFAULT_MAX_LANGUAGE_DISTANCE)                    # 10
print(lang_distance("en-AU", "en-US"))                  # 5
print(lang_matches("arz", "ar"))                        # True
print(closest_lang("en-AU", iter(["fr", "en-GB"])))     # en-GB
print(closest_lang("en", []))                           # None
```

The page [Matching](matching.md) gives the steps and the tie rules.

## Dialects

`LECT_MODES` is the tuple of values that the `lects` argument takes besides `None`. `lect_steps(a: str, b: str) -> Optional[int]` counts the steps between two private-use dialect tags in the dialect tree, and returns `None` when they do not meet.

```python
from linguatag import LECT_MODES, lect_steps

print(LECT_MODES)                                  # ('dialect', 'standard')
print(lect_steps("pt-x-central", "pt-x-minhoto"))  # 2
print(lect_steps("pt", "en"))                      # None
```

## Genealogy, place and time

`parent(tag: str) -> Optional[str]` gives the genealogical parent. `ancestors(tag: str) -> List[str]` gives the chain of parents, nearest first. `family(tag: str) -> str` and `family_path(tag: str) -> Tuple[str, ...]` give the family as text and as clade names. `catalog_ids(tag: str) -> Dict[str, Optional[str]]` gives the `glottolog_code` and `wikidata_qid` of a tag.

`ancestry_similarity(a, b, max_depth=10, temporal_decay=False, decay_halflife=1000.0) -> float`, `geographic_distance(a, b, normalize=True) -> Optional[float]` and `temporal_distance(a, b, reference_year=2025) -> Optional[float]` measure two tags. `script_features(name) -> dict`, `script_distance(a: dict, b: dict) -> float` and `script_distance_by_name(a: str, b: str) -> float` compare writing systems.

```python
from linguatag import ancestors, script_distance_by_name, temporal_distance

print(ancestors("pt-PT-x-porto")[0])                    # pt-PT-x-minho
print(round(script_distance_by_name("Latin", "Greek"), 4))  # 0.1667
print(temporal_distance("la", "qqq"))                   # None
```

## Ask about Arabic

`is_arabic_variety(tag: str) -> bool` tells whether the language subtag of the tag is Arabic or a variety of it. Script and region do not count.

```python
from linguatag import is_arabic_variety

print(is_arabic_variety("arz-EG"))   # True
print(is_arabic_variety("ur"))       # False
```

## Where each name is explained

| Names | Page |
| --- | --- |
| `standardize_lang`, `parse_tag`, `LanguageTag`, `LanguageTagError` | [Parsing and normalising tags](parsing.md) |
| `default_region`, `with_default_region`, `likely_script`, `maximize`, `OVERRIDES` | [Likely subtags and default regions](likely-subtags.md) |
| `lang_distance`, `lang_matches`, `closest_lang`, `DEFAULT_MAX_LANGUAGE_DISTANCE` | [Matching](matching.md) |
| `is_arabic_variety` | [Getting started](getting-started.md#tell-whether-a-tag-names-arabic) |
| `LECT_MODES`, `lect_steps` | [Dialects](dialects.md) |
| `parent`, `ancestors`, `family`, `family_path`, `catalog_ids`, `ancestry_similarity`, `geographic_distance`, `temporal_distance`, `script_features`, `script_distance`, `script_distance_by_name` | [Genealogy, place and time](genealogy.md) |

---
[Index](index.md) · [← Performance](performance.md)
