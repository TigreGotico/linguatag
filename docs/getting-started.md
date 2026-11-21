# Getting started

<!-- agent-hint
covers: how to install linguatag and run each main call once.
source: linguatag/__init__.py:__all__, linguatag/matching.py, linguatag/regions.py, linguatag/standardize.py
generated: no
verify: `.venv/bin/python -c "import re,sys,subprocess as s;t=open(sys.argv[1]).read();b=re.findall(r'\x60{3}python\n(.*?)\x60{3}',t,re.S);w=[l.split('# ',1)[1].strip() for c in b for l in c.splitlines() if l.strip().startswith('print(') and '# ' in l];g=[x.strip() for c in b for x in s.run([sys.executable,'-I','-c',c],capture_output=True,text=True).stdout.splitlines()];print('OK',len(w)) if g==w else sys.exit('MISMATCH '+repr([p for p in zip(w,g) if p[0]!=p[1]] or (len(w),len(g))))" docs/getting-started.md`
see: parsing.md, matching.md
-->

This page installs linguatag and runs each main call once. Every comment after a call shows what the call prints.

## Install

Make a virtual environment and install the latest release with uv:

```
uv venv
uv pip install --prerelease=allow linguatag
```

linguatag needs Python 3.11 or later. It has no dependencies.

## Give a tag one spelling

Config files, directory names and voice ids write one language in many ways. `standardize_lang` turns each way into one string:

```python
from linguatag import standardize_lang

print(standardize_lang("en_us"))   # en-US
print(standardize_lang("iw"))      # he
print(standardize_lang("eng"))     # en
print(standardize_lang("zh-hak"))  # hak
print(standardize_lang("en-Latn")) # en
```

`iw` is a deprecated code for Hebrew, `eng` is the three-letter code for English, and `zh-hak` is Hakka written as an extlang. `en-Latn` loses its script, because the IANA registry marks Latin as the script that English needs no subtag for. [Parsing and normalising tags](parsing.md) gives all the rules.

## Find the region and the script of a bare tag

A tag with no region means the region where the language started and is still spoken:

```python
from linguatag import default_region, likely_script, with_default_region

print(default_region("en"))          # GB
print(with_default_region("pt"))     # pt-PT
print(with_default_region("zh-Hant"))  # zh-Hant-TW
print(likely_script("zh-TW"))        # Hant
print(likely_script("sr-ME"))        # Latn
```

[Likely subtags and default regions](likely-subtags.md) explains where these values come from.

## Measure how near two tags are

`lang_distance` gives `0` for the same language and region, and a larger number for tags that are further apart. A distance of 10 or less is a usable match:

```python
from linguatag import lang_distance

print(lang_distance("pt", "pt-PT"))   # 0
print(lang_distance("pt", "pt-BR"))   # 5
print(lang_distance("en", "fr"))      # 84
```

`pt` is `pt-PT`, so the first distance is 0. Brazil is a different region of the same language, so the second distance is small.

## Pick the best tag from a list

`closest_lang` takes the requested tag and the tags you have. It returns the nearest one as you wrote it, or `None`:

```python
from linguatag import closest_lang

print(closest_lang("en", ["en-US", "en-GB"]))           # en-GB
print(closest_lang("en-AU", ["fr-FR", "en-US"]))        # en-US
print(closest_lang("zh-HK", ["zh-HK-HiuMaanNeural", "zh-CN-XiaoxiaoNeural"]))  # zh-HK-HiuMaanNeural
print(closest_lang("de", ["fr", "it"]))                 # None
```

A voice id such as `zh-HK-HiuMaanNeural` is not a language tag. linguatag measures its longest part that is a tag, here `zh-HK`.

## Tell whether a tag names Arabic

`is_arabic_variety` looks only at the language subtag:

```python
from linguatag import is_arabic_variety

print(is_arabic_variety("arz-EG"))              # True
print(is_arabic_variety("ar-Latn-x-buckwalt"))  # True
print(is_arabic_variety("fa"))                  # False
```

Persian (`fa`) uses Arabic script but is a different language. Arabic is `ar`, each language that the IANA registry puts in the `ar` macrolanguage, and Hassaniyya (`mey`). The registry puts Hassaniyya in no macrolanguage, and Glottolog classifies it as Arabic. To ask whether an Arabic resource can serve a request, use `lang_distance` instead.

---
[Index](index.md) · [Parsing and normalising tags →](parsing.md)
