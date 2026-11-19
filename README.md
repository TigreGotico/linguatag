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

CLDR 49 likely-subtags is the base. CLDR picks the most-populous region, and for most languages that is also the motherland. `linguatag.OVERRIDES` replaces CLDR where the two differ, and each override cites its source: `en` is GB, `pt` is PT, `ur` is IN and `yue` is CN. An override holds for its own script only, so `yue-Hant` stays HK. When several countries share the area where a language first appeared, the CLDR pick is one of them and stays.

A bare `ar` is Modern Standard Arabic, the standard of no single country, so its region is `001`, the world, as CLDR spells it. `arb`, the code of Modern Standard Arabic itself, takes the same region.

## Likely script

`likely_script(tag)` gives the script of a tag: its script subtag, or else the script that CLDR 49 likely-subtags gives for the language in its region. `zh-TW` and `zh-HK` are `Hant`, `zh` is `Hans`, `sr-ME` is `Latn` and `ku-IQ` is `Arab`. A bare tag takes its default region first, so `yue` is `yue-CN` and `Hans`. Libyan Arabic `ayl` is `Arab`, Hassaniyya in Senegal (`mey-SN`) is `Latn`, Western Armenian `hyw` is `Armn` and Literary Chinese `lzh` is `Hant`.

## CLDR and IANA data

Standardization, the default region, the likely script and the distance come from data that this package carries, never from what else is installed. `linguatag/bcp47.py` parses a tag (RFC 5646 section 2.1), puts it in canonical form (RFC 5646 section 4.5 and UTS #35 Annex C) and adds likely subtags (UTS #35 section 4.3). `linguatag/distance.py` measures the language matching distance (UTS #35 section 4.4). They read five files in `linguatag/data`, and each names its source in a `source` field:

| File | Source |
| --- | --- |
| `likely_subtags.json` | CLDR 49 `supplemental/likelySubtags.json` |
| `aliases.json` | CLDR 49 `supplemental/aliases.json`: language, script, territory and variant aliases |
| `subtags.json` | the IANA Language Subtag Registry: every subtag, with its deprecation, Preferred-Value, Prefix, Suppress-Script and Macrolanguage |
| `language_matching.json` | CLDR 49 `supplemental/languageMatching.json`, `written-new`: paradigm locales, match variables and `languageMatch` rules |
| `territory_containment.json` | CLDR 49 `supplemental/territoryContainment.json`: the regions that each macroregion contains |

`scripts/extract_cldr.py` writes the five files. Run it again after a CLDR release or an IANA registry change.

The parser, the canonicalization and the distance follow the code of `langcodes` (see NOTICE).

## Distance and closest match

`lang_distance` is `0` for identical tags and grows as tags differ. A distance of 10 or less is a usable match. Both tags are standardized first, and a tag with no region is measured from its default region.

Standardization replaces an extlang tag and a deprecated subtag with their IANA Preferred-Values, as RFC 5646 section 4.5 says: `zh-hak` is Hakka (`hak`), `ar-arz-EG` is `arz-EG`, `ajp-JO` is `apc-JO` and `my-BU` is `my-MM`. It replaces an ISO 639-2 code with its two-letter code (`eng` is `en`) and drops a script that the registry suppresses for the language (`en-Latn` is `en`). An encompassed language keeps its own code: `cmn` stays `cmn` and `arb` stays `arb`.

The distance is the CLDR 49 language matching distance of UTS #35 section 4.4. Each tag gets its likely subtags, then each subtag that differs adds the distance of the first CLDR rule that matches it. Two regions of one language are 4 or 5 apart: `en-CA` is 4 from `en-US`, because CLDR puts Canada in the US English cluster, and 5 from `en-GB`. Two scripts of one language are 50 apart unless a rule says less (`sr-Latn` and `sr-Cyrl` are 5), and two languages 80 unless a rule says less (`nb` and `no` are 1, `arz` is 10 from `ar`).

`closest_lang` returns the candidate with the smallest distance, verbatim, when that distance is within `max_distance` (default 10). Pass `max_distance=0` to accept exact matches only. Among candidates at the same distance, the code that the request names wins first, and a code with no language, extlang or region subtag that has a Preferred-Value wins next: `closest_lang("zh-hak", ["hak", "zh-hak"])` is `zh-hak`, `closest_lang("ar-apc", ["ajp", "apc"])` is `apc`, and `closest_lang("my-MM", ["my-BU", "my-MM"])` is `my-MM`. A CLDR paradigm locale (`en-US`, `en-GB`, `es-ES`, `es-419`, `pt-BR`, `pt-PT`) wins after that: `closest_lang("es-MX", ["es-CR", "es-419"])` is `es-419`.

An Arabic variety (`arz`, `apc`, `ar-MA`, Hassaniyya `mey`) in Arabic script is at most 5 from Modern Standard Arabic (`ar`, `arb`). Juba Arabic (`pga`), Cypriot Maronite Arabic (`acy`) and Hassaniyya in Senegal (`mey-SN`) are written in Latin script, so they get this rule only with an explicit `-Arab` subtag. No other macrolanguage gets this rule. No spoken member of the `zh` macrolanguage other than Mandarin matches `cmn` or `zh` in Simplified script: Cantonese, Hakka, Min Nan, Wu, Gan, Xiang, Min Dong, Min Bei, Jinyu and the others the IANA registry lists under `zh`. `zh` in Traditional script and `zh-Latn` keep the CLDR distance for them. Literary Chinese (`lzh`) has no speakers, so this rule leaves it out. CLDR 49 writes it in Traditional script in China, so a Chinese resource in the same script and region serves an `lzh` request: `lzh` gets `zh-Hant-CN`, `lzh-TW` gets `zh-Hant`, and `lzh-Hans` gets `zh` or `cmn`. A bare `lzh` is 14 from `zh-Hant`, which is Taiwan, because the regions differ. It does not match Simplified Chinese. Fanti (`fat`) and Mandinka (`mnk`) match no other language, Akan (`ak`), Twi (`tw`), Mandingo (`man`) and Eastern Maninkakan (`emk`) included: CLDR 49 does not make them aliases of a macrolanguage, and no CLDR rule names them. Twi is an alias of Akan.

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
pip install linguatag
```

linguatag has no dependencies. The `langcodes` extra installs nothing, so a pin on `linguatag[langcodes]` still resolves.
