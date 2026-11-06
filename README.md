# linguatag

BCP-47 language tags: standardization, distance, closest match, and the default region of a tag that names none.

```python
from linguatag import closest_lang, default_region, lang_distance, with_default_region

default_region("en")            # 'GB'
with_default_region("zh-Hant")  # 'zh-Hant-TW'
lang_distance("pt", "pt-PT")    # 0
lang_distance("pt", "pt-BR")    # 5
closest_lang("en", ["en-US", "en-GB"])  # 'en-GB'
closest_lang("en-AU", ["fr-FR", "en-US"])  # 'en-US'
```

## Standardization

`standardize_lang` folds underscores and case, and replaces deprecated forms through `langcodes`: `en_us` is `en-US`, `iw` is `he`, `zh-yue` is `yue`.

`tl` and `tgl` are `tl`, with any region, so `tl-PH` stays `tl-PH`. The IANA Language Subtag Registry gives `tl` no `Preferred-Value`, and RFC 5646 section 4.5 replaces a subtag only through that field. CLDR aliases `tl` to `fil` with the reason `legacy`, and `langcodes` follows CLDR, so `linguatag` overrides it here. `fil` stays `fil`, and the distance between the two tags is 0.

A tag that `langcodes` cannot parse, such as a voice id, keeps its unparseable part in lowercase after its standardized prefix: `zh-HK-HiuMaanNeural` is `zh-HK-hiumaanneural`. `None` and a tag with an empty subtag (`en_`, `-en`, `en--US`) name no language, and they standardize to an empty string.

`MAX_TAG_LENGTH` is 255 characters. A longer string also names no language: every function treats it as an empty tag, before any parsing. The limit follows the 255-byte file name limit, because tags come from directory names and config values. A tag whose standard form passes the limit gets the same result.

## Default region

A tag with no region defaults to its motherland: the region where the language first appeared and is still spoken. `en` is `en-GB`, `pt` is `pt-PT`, `es` is `es-ES`.

CLDR likely-subtags is the base. CLDR picks the most-populous region, and for most languages that is also the motherland. `linguatag.OVERRIDES` replaces CLDR where the two differ, and each override cites its source: `en` is GB, `pt` is PT, `ur` is IN and `yue` is CN. An override holds for its own script only, so `yue-Hant` stays HK. When several countries share the area where a language first appeared, the CLDR pick is one of them and stays.

A bare `ar` is Modern Standard Arabic, the standard of no single country, so its region is `001`, the world, as CLDR spells it.

`linguatag/data/likely_regions.json` holds the CLDR regions. `scripts/build_likely_regions.py` rebuilds it from the installed `langcodes`.

## Distance and closest match

`lang_distance` is `0` for identical tags and grows as tags differ. A distance of 10 or less is a usable match. Both tags are standardized first, and a tag with no region is measured from its default region.

`closest_lang` returns the candidate with the smallest distance, verbatim, when that distance is within `max_distance` (default 10). Pass `max_distance=0` to accept exact matches only.

An Arabic variety (`arz`, `apc`, `ar-MA`) in Arabic script is at most 5 from Modern Standard Arabic (`ar`, `arb`). Juba Arabic (`pga`) and Cypriot Maronite Arabic (`acy`) are written in Latin script, so they get this rule only with an explicit `-Arab` subtag. No other macrolanguage gets this rule. Cantonese never matches Mandarin.

## Dialects

A private-use subtag names a dialect, such as `an-x-cheso` or `pt-PT-x-porto`. BCP-47 gives it no meaning, so by default it adds nothing to the distance, and `an-x-cheso` is as near to `an-x-ansotano` as to `an`. Pass `lects` to score it:

```python
closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="dialect")   # 'an-x-ansotano'
closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="standard")  # 'an'
```

`"dialect"` takes the nearest other dialect first and the standard language last. `"standard"` takes the standard language first and the dialects after it. Nearness is the number of steps between two dialects in the orthography2ipa dialect tree: a parent dialect is 1 step away, a sibling 2. The lect score adds at most 4. `closest_lang` uses it only to order the candidates within `max_distance`, so it never decides whether a tag matches.

`linguatag/data/lineage.json` holds the tree. `scripts/build_lineage.py` rebuilds it from the orthography2ipa spec files at a git ref. With `--check` it writes nothing and exits 1 when the rebuild differs from the file. The `Lineage Check` workflow runs this check every week against the `dev` branch of orthography2ipa.

## Install

```
pip install linguatag
```

`langcodes` is a required dependency. It has no required dependencies of its own. The `linguatag[langcodes]` extra is empty, and it exists so that requirements that name it stay valid.
