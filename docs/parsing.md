# Parsing and normalising tags

<!-- agent-hint
covers: how standardize_lang gives a tag one spelling, and how parse_tag reads the subtags of a tag.
source: linguatag/_standardize.py:standardize_lang, linguatag/_bcp47.py:parse (exported as parse_tag), linguatag/_bcp47.py:standardize
generated: no
verify: python scripts/check_doc_page.py docs/parsing.md
see: likely-subtags.md
-->

This page shows how linguatag gives every way of writing a language tag one spelling. Use `standardize_lang` for this. It is the call that the rest of the package uses before it compares two tags.

## standardize_lang

```python
from linguatag import standardize_lang

print(standardize_lang("en_us"))      # en-US
print(standardize_lang("iw"))         # he
print(standardize_lang("eng"))        # en
print(standardize_lang("zh-hak"))     # hak
print(standardize_lang("ar-arz-EG"))  # arz-EG
print(standardize_lang("ajp-JO"))     # apc-JO
print(standardize_lang("my-BU"))      # my-MM
print(standardize_lang("sh"))         # sr-Latn
print(standardize_lang("en-Latn"))    # en
print(standardize_lang("cmn"))        # cmn
print(standardize_lang("tgl"))        # tl
```

Each line applies one rule:

| Input | Output | Rule |
| --- | --- | --- |
| `en_us` | `en-US` | An underscore becomes a hyphen, and each subtag takes its BCP 47 case. |
| `iw`, `ajp-JO`, `my-BU` | `he`, `apc-JO`, `my-MM` | A deprecated subtag becomes its IANA Preferred-Value (RFC 5646 section 4.5). |
| `zh-hak`, `ar-arz-EG` | `hak`, `arz-EG` | A language and its extlang become the extlang. |
| `eng` | `en` | An ISO 639-2 code becomes its two-letter code, from the CLDR alias rules. |
| `sh` | `sr-Latn` | A legacy code becomes its CLDR replacement. |
| `en-Latn` | `en` | A script that the IANA registry suppresses for the language goes (RFC 5646 section 3.1.9). |
| `cmn` | `cmn` | An encompassed language keeps its own code. It does not become its macrolanguage `zh`. |
| `tgl` | `tl` | Tagalog stays `tl`. CLDR replaces it with Filipino, `fil`, and linguatag does not. |
| `tl-Latn-PH` | `tl-PH` | Tagalog stays `tl` with other subtags too, and `Latn`, its IANA Suppress-Script, goes. |

`standardize_lang(tag, macro=True)` folds an individual language into its macrolanguage with the CLDR 49 macrolanguage rules. CLDR folds only the main member of a macrolanguage, so Mandarin becomes `zh` and Cantonese stays `yue`:

```python
from linguatag import standardize_lang

print(standardize_lang("cmn", macro=True))  # zh
print(standardize_lang("arb", macro=True))  # ar
print(standardize_lang("yue", macro=True))  # yue
```

`standardize_lang` never raises. A string that is not a well-formed tag gets the extlang and deprecated-language rules and the BCP 47 case of each subtag, and nothing more:

```python
from linguatag import standardize_lang

print(standardize_lang("zh-HK-HiuMaanNeural"))  # zh-HK-hiumaanneural
```

A leading, trailing or doubled separator makes an empty subtag, and BCP 47 section 2.1 gives a subtag 1 to 8 characters. So `pt-BR-` is not a tag. `standardize_lang` keeps the separator, and the matching functions put the string at distance 100 from every tag, so it matches nothing. When the input can contain extra separators, remove the empty subtags before the call. `str.strip` removes only the leading and trailing separators, so split the string and join the parts that are not empty:

```python
from linguatag import closest_lang, standardize_lang

print(standardize_lang("pt_BR_"))                     # pt-BR-
print(closest_lang("pt--BR", ["pt-PT", "pt-BR"]))     # None
parts = "pt--BR".replace("_", "-").split("-")
print(closest_lang("-".join(p for p in parts if p), ["pt-PT", "pt-BR"]))  # pt-BR
```

## Read the subtags with parse_tag

```python
from linguatag import LanguageTagError, parse_tag

print(parse_tag("EN-latn-us"))         # en-Latn-US
print(parse_tag("en-latn-us").script)  # Latn
try:
    parse_tag("en-")
except LanguageTagError as error:
    print(error)                       # subtag '' is not 1 to 8 letters and digits
```

`parse_tag` returns a `LanguageTag` with the fields `language`, `extlangs`, `script`, `region`, `variants`, `extensions`, `private` and `whole`. It follows the RFC 5646 section 2.1 grammar, and it replaces nothing. It reads `root` as `und`, and it gives `None` as the language of `und`. `LanguageTagError` is a subclass of `ValueError`.

`standardize_lang` replaces deprecated and extlang subtags, so `standardize_lang("sgn-US")` is `ase`. A tag with an extlang whose IANA `Prefix` is a different language stays as written: `standardize_lang("en-hak")` is `en-hak`. White space around a tag is no part of it (RFC 5646 section 2.1), so `standardize_lang(" pt-br ")` is `pt-BR`. A space inside a tag, as in `pt- BR`, leaves the tag malformed. Only the names in `linguatag.__all__` are the public API. The modules inside the package, such as `linguatag._bcp47`, are internal.

---
[Index](index.md) · [← Getting started](getting-started.md) · [Likely subtags and default regions →](likely-subtags.md)
