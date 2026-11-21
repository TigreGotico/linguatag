# Parsing and normalising tags

<!-- agent-hint
covers: how standardize_lang gives a tag one spelling, and what the parser in linguatag.bcp47 does.
source: linguatag/standardize.py:standardize_lang, linguatag/bcp47.py:parse, linguatag/bcp47.py:standardize
generated: no
verify: `.venv/bin/python -c "import re,sys,subprocess as s;t=open(sys.argv[1]).read();b=re.findall(r'\x60{3}python\n(.*?)\x60{3}',t,re.S);w=[l.split('# ',1)[1].strip() for c in b for l in c.splitlines() if l.strip().startswith('print(') and '# ' in l];g=[x.strip() for c in b for x in s.run([sys.executable,'-I','-c',c],capture_output=True,text=True).stdout.splitlines()];print('OK',len(w)) if g==w else sys.exit('MISMATCH '+repr([p for p in zip(w,g) if p[0]!=p[1]] or (len(w),len(g))))" docs/parsing.md`
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

`standardize_lang` never raises. A string that is not a well-formed tag gets the extlang and deprecated-language rules and the BCP 47 case of each subtag, and nothing more:

```python
from linguatag import standardize_lang

print(standardize_lang("zh-HK-HiuMaanNeural"))  # zh-HK-hiumaanneural
```

## The parser in linguatag.bcp47

`linguatag.bcp47` holds the lower-level calls. The top-level package does not export them.

```python
from linguatag.bcp47 import LanguageTagError, parse, standardize

print(parse("EN-latn-us"))         # en-Latn-US
print(parse("en-latn-us").script)  # Latn
print(standardize("sgn-US"))       # ase
try:
    parse("en-")
except LanguageTagError as error:
    print(error)                   # subtag '' is not 1 to 8 letters and digits
```

`parse` returns a `LanguageTag` with the fields `language`, `extlangs`, `script`, `region`, `variants`, `extensions`, `private` and `whole`. It follows the RFC 5646 section 2.1 grammar, and it replaces nothing. It reads `root` as `und`, and it gives `None` as the language of `und`. `LanguageTagError` is a subclass of `ValueError`.

`standardize` is the canonical form that `standardize_lang` uses for a well-formed tag. It raises `LanguageTagError` for a tag that is not well-formed. A tag with an extlang whose IANA `Prefix` is a different language stays as written: `standardize("en-hak")` is `en-hak`.

---
[Index](index.md) · [← Getting started](getting-started.md) · [Likely subtags and default regions →](likely-subtags.md)
