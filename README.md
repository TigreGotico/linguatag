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

## Default region

A tag with no region defaults to its motherland: the region where the language first appeared and is still spoken. `en` is `en-GB`, `pt` is `pt-PT`, `es` is `es-ES`.

CLDR likely-subtags is the base. CLDR picks the most-populous region, and for most languages that is also the motherland. `linguatag.OVERRIDES` replaces CLDR where the two differ, and each override cites its source: `en` is GB, `pt` is PT, `ur` is IN and `yue` is CN. An override holds for its own script only, so `yue-Hant` stays HK. When several countries share the area where a language first appeared, the CLDR pick is one of them and stays.

A bare `ar` is Modern Standard Arabic, the standard of no single country, so its region is `001`, the world, as CLDR spells it.

`linguatag/data/likely_regions.json` holds the CLDR regions. `scripts/build_likely_regions.py` rebuilds it from the installed `langcodes`.

## Distance and closest match

`lang_distance` is `0` for identical tags and grows as tags differ. A distance of 10 or less is a usable match. Both tags are standardized first, and a tag with no region is measured from its default region.

`closest_lang` returns the candidate with the smallest distance, verbatim, when that distance is within `max_distance` (default 10). Pass `max_distance=0` to accept exact matches only.

An Arabic variety (`arz`, `apc`, `ar-MA`) in Arabic script is at most 5 from Modern Standard Arabic (`ar`, `arb`). No other macrolanguage gets this rule. Cantonese never matches Mandarin.

## Install

```
pip install linguatag[langcodes]
```

`langcodes` is optional. Without it, standardization only folds case and underscores, and distance uses a coarse same-language measure with the same ordering.
