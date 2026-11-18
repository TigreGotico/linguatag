# linguatag

BCP-47 language tags: standardization, distance, closest match, and the default region of a tag that names none.

```python
from linguatag import (closest_lang, default_region, is_arabic_variety, lang_distance,
                       likely_script, with_default_region)

default_region("en")            # 'GB'
with_default_region("zh-Hant")  # 'zh-Hant-TW'
likely_script("zh-TW")          # 'Hant'
lang_distance("pt", "pt-PT")    # 0
lang_distance("pt", "pt-BR")    # 5
closest_lang("en", ["en-US", "en-GB"])  # 'en-GB'
closest_lang("en-AU", ["fr-FR", "en-US"])  # 'en-US'
is_arabic_variety("ar-Latn-x-buckwalt")  # True
is_arabic_variety("fa")         # False
```

## Default region

A tag with no region defaults to its motherland: the region where the language first appeared and is still spoken. `en` is `en-GB`, `pt` is `pt-PT`, `es` is `es-ES`.

CLDR likely-subtags is the base. CLDR picks the most-populous region, and for most languages that is also the motherland. `linguatag.OVERRIDES` replaces CLDR where the two differ, and each override cites its source: `en` is GB, `pt` is PT, `ur` is IN and `yue` is CN. An override holds for its own script only, so `yue-Hant` stays HK. When several countries share the area where a language first appeared, the CLDR pick is one of them and stays.

A bare `ar` is Modern Standard Arabic, the standard of no single country, so its region is `001`, the world, as CLDR spells it.

## Likely script

`likely_script(tag)` gives the script of a tag: its script subtag, or else the script that CLDR likely-subtags gives for the language in its region. `zh-TW` and `zh-HK` are `Hant`, `zh` is `Hans`, and `sr-ME` is `Latn`. A bare tag takes its default region first, so `yue` is `yue-CN` and `Hans`. It needs `langcodes` for every language that the package table does not hold.

`linguatag/data/likely_regions.json` holds the CLDR regions. `scripts/build_likely_regions.py` rebuilds it from the installed `langcodes`.

The CLDR data in `langcodes` has no entry for some Arabic varieties, and it puts them in Latin script. CLDR 49 puts them in Arabic script: Libyan Arabic `ayl` is `ayl-Arab-LY` and Hassaniyya `mey` is `mey-Arab-DZ`. For these varieties the table holds the CLDR 49 entries, with their scripts, and the build script reads them from the CLDR release. A tag that names no script is measured in the CLDR script, so `mey` and `mey-Arab` are at distance 0. Hassaniyya in Senegal, `mey-SN`, is in Latin script, as CLDR gives it.

The same holds for two more languages. The `langcodes` data has no entry for Western Armenian and puts it in Latin script in the US, and it puts Literary Chinese in Simplified script. CLDR 49 gives `hyw_Armn_AM` and `lzh_Hant_CN`, and the table holds these entries. So `hyw` is `hyw-Armn-AM` and `lzh-TW` is `lzh-Hant-TW`. A `hyw-Latn` request matches no Armenian-script resource, such as `hyw` or `hyw-AM`.

## Distance and closest match

`lang_distance` is `0` for identical tags and grows as tags differ. A distance of 10 or less is a usable match. Both tags are standardized first, and a tag with no region is measured from its default region.

Standardization replaces an extlang tag and a deprecated language subtag with their IANA Preferred-Values, as RFC 5646 section 4.5 says: `zh-hak` is Hakka (`hak`), `ar-arz-EG` is `arz-EG`, and `ajp-JO` is `apc-JO`. `linguatag/data/extlangs.json` and `linguatag/data/deprecated_languages.json` hold the tables. `langcodes` replaces a deprecated region subtag (`my-BU` is `my-MM`), and `linguatag/data/deprecated_regions.json` holds the IANA Preferred-Values of region subtags for the tie rule below. `scripts/build_preferred_values.py` rebuilds the three tables from the IANA Language Subtag Registry.

`closest_lang` returns the candidate with the smallest distance, verbatim, when that distance is within `max_distance` (default 10). Pass `max_distance=0` to accept exact matches only. Among candidates at the same distance, the code that the request names wins first, and a code with no language, extlang or region subtag that has a Preferred-Value wins next: `closest_lang("zh-hak", ["hak", "zh-hak"])` is `zh-hak`, `closest_lang("ar-apc", ["ajp", "apc"])` is `apc`, and `closest_lang("my-MM", ["my-BU", "my-MM"])` is `my-MM`.

An Arabic variety (`arz`, `apc`, `ar-MA`, Hassaniyya `mey`) in Arabic script is at most 5 from Modern Standard Arabic (`ar`, `arb`). Juba Arabic (`pga`), Cypriot Maronite Arabic (`acy`) and Hassaniyya in Senegal (`mey-SN`) are written in Latin script, so they get this rule only with an explicit `-Arab` subtag. No other macrolanguage gets this rule. No spoken member of the `zh` macrolanguage other than Mandarin matches `cmn` or `zh` in Simplified script: Cantonese, Hakka, Min Nan, Wu, Gan, Xiang, Min Dong, Min Bei, Jinyu and the others the IANA registry lists under `zh`. `zh` in Traditional script and `zh-Latn` keep the langcodes distance for them. Literary Chinese (`lzh`) has no speakers, so this rule leaves it out. CLDR 49 writes it in Traditional script in China, so a Chinese resource in the same script and region serves an `lzh` request: `lzh` gets `zh-Hant-CN`, `lzh-TW` gets `zh-Hant`, and `lzh-Hans` gets `zh` or `cmn`. A bare `lzh` is 14 from `zh-Hant`, which is Taiwan, because the regions differ. It does not match Simplified Chinese. Fanti (`fat`) and Mandinka (`mnk`) match no other language, Akan (`ak`), Twi (`tw`), Mandingo (`man`) and Eastern Maninkakan (`emk`) included: CLDR 49 does not make them aliases of a macrolanguage. Twi is an alias of Akan.

## Arabic varieties

`is_arabic_variety` tells whether a tag names Arabic. The language subtag decides. Script, region and private-use subtags do not count, so `ar-Latn-x-buckwalt` and Juba Arabic (`pga`) are Arabic varieties. Arabic is `ar` (`ara`), the individual languages that the IANA registry puts in the `ar` macrolanguage (`arb`, `arz`, `acy`, `pga` and the others), and Hassaniyya (`mey`). The IANA registry puts Hassaniyya in no macrolanguage, and Glottolog classifies it as Arabic. A different language in Arabic script is not Arabic: `fa`, `ur` and `und-Arab` are `False`.

`lang_distance` answers a different question: whether a resource for one tag can serve a request for another.

## Dialects

A private-use subtag names a dialect, such as `an-x-cheso` or `pt-PT-x-porto`. BCP-47 gives it no meaning, so by default it adds nothing to the distance, and `an-x-cheso` is as near to `an-x-ansotano` as to `an`. Pass `lects` to score it:

```python
closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="dialect")   # 'an-x-ansotano'
closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="standard")  # 'an'
```

`"dialect"` takes the nearest other dialect first and the standard language last. `"standard"` takes the standard language first and the dialects after it. Nearness is the number of steps between two dialects in the orthography2ipa dialect tree: a parent dialect is 1 step away, a sibling 2. The lect score adds at most 4. `closest_lang` uses it only to order the candidates within `max_distance`, so it never decides whether a tag matches.

`linguatag/data/lineage.json` holds the tree. `scripts/build_lineage.py` rebuilds it from the orthography2ipa spec files at a git ref.

## Install

```
pip install linguatag[langcodes]
```

`langcodes` is optional. Without it, standardization only folds case and underscores and replaces extlang tags, and distance uses a coarse same-language measure with the same ordering.
