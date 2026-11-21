# Likely subtags and default regions

<!-- agent-hint
covers: the default region and the likely script of a bare tag, and the CLDR maximize call.
source: linguatag/regions.py:default_region, linguatag/regions.py:OVERRIDES, linguatag/regions.py:likely_script, linguatag/bcp47.py:maximize, linguatag/data/likely_subtags.json
generated: no
verify: `.venv/bin/python -c "import re,sys,subprocess as s;t=open(sys.argv[1]).read();b=re.findall(r'\x60{3}python\n(.*?)\x60{3}',t,re.S);w=[l.split('# ',1)[1].strip() for c in b for l in c.splitlines() if l.strip().startswith('print(') and '# ' in l];g=[x.strip() for c in b for x in s.run([sys.executable,'-I','-c',c],capture_output=True,text=True).stdout.splitlines()];print('OK',len(w)) if g==w else print('MISMATCH',[p for p in zip(w,g) if p[0]!=p[1]] or (len(w),len(g)))" docs/likely-subtags.md`
see: matching.md, data-and-licence.md
-->

This page shows how linguatag fills in the region and the script of a tag that names only a language. The region is the motherland of the language: the region where it first appeared and is still spoken.

## The default region

```python
from linguatag import default_region, with_default_region

print(default_region("en"))        # GB
print(default_region("pt"))        # PT
print(default_region("es"))        # ES
print(default_region("pt-BR"))     # BR
print(default_region("zh-Hant"))   # TW
print(default_region("ar"))        # 001
print(default_region("und"))       # None

print(with_default_region("en"))            # en-GB
print(with_default_region("en_us"))         # en-US
print(with_default_region("gl-x-central"))  # gl-ES-x-central
print(with_default_region("und"))           # und
```

`default_region` returns the region that a tag names, or else its default region. It returns `None` for `und` and for a language that CLDR does not know. `with_default_region` returns the standardized tag with that region in place. A variant or a private-use subtag stays after the region. A tag with no default region comes back standardized and with no other change.

The tag is standardized first, so `iw` gives `IL`. An encompassed language that CLDR replaces with its macrolanguage takes the region of the macrolanguage, so `cmn` gives `CN`.

## Where the default region comes from

CLDR 49 likely subtags are the base. CLDR picks the most-populous region of each language, and for most languages that region is also the motherland. `linguatag.OVERRIDES` replaces CLDR where the two differ:

```python
from linguatag import OVERRIDES

print(sorted(OVERRIDES))  # ['ar', 'en', 'pt', 'ur', 'yue']
print(OVERRIDES["ar"])     # ('Arab', '001')
print(OVERRIDES["en"])     # ('Latn', 'GB')
print(OVERRIDES["pt"])     # ('Latn', 'PT')
print(OVERRIDES["ur"])     # ('Arab', 'IN')
print(OVERRIDES["yue"])    # ('Hans', 'CN')
```

Each entry gives the script and the region of the default. An override holds only for its own script, so `yue-Hant` keeps the CLDR region `HK` and `en-Dsrt` keeps `US`. When several countries share the area where a language first appeared, the CLDR pick is one of them and stays.

Each entry in `OVERRIDES` cites its source in a comment beside it in `linguatag/regions.py`. An entry added to the map cites its source in the same way.

A bare `ar` is Modern Standard Arabic. It is the standard of no single country.

So its region is `001`, the CLDR code for the world. `arb`, the code of Modern Standard Arabic itself, also gets `001`.

## The likely script

```python
from linguatag import likely_script

print(likely_script("zh-TW"))   # Hant
print(likely_script("zh"))      # Hans
print(likely_script("sr-ME"))   # Latn
print(likely_script("ku-IQ"))   # Arab
print(likely_script("yue"))     # Hans
print(likely_script("hyw"))     # Armn
print(likely_script("mey-SN"))  # Latn
print(likely_script("zzz"))     # None
```

`likely_script` returns the script subtag of a tag when it has one. Otherwise it returns the script that CLDR 49 likely subtags give for the language in its region. A bare tag takes its default region first, so `yue` becomes `yue-CN`, and that gives `Hans`. The result is `None` for `und` and for a language that CLDR does not know.

<!-- agent-hint: maximize gives en-Latn-US, while default_region gives GB for en. Do not use one in place of the other. -->
## maximize: the CLDR algorithm

`linguatag.bcp47.maximize` is UTS #35 section 4.3, "Add Likely Subtags", with no overrides:

```python
from linguatag.bcp47 import maximize

print(maximize("zh-TW"))  # zh-Hant-TW
print(maximize("sr-ME"))  # sr-Latn-ME
print(maximize("cmn"))    # zh-Hans-CN
print(maximize("en"))     # en-Latn-US
print(maximize("und"))    # None
```

`maximize` returns a `LanguageTag`, or `None`. It replaces an encompassed language with its macrolanguage, as section 4.3 requires, so `cmn` becomes `zh`. It returns `None` for `und` and for a language with no CLDR entry. Because it uses CLDR alone, `en` gives `US`. Use `default_region` when you want the motherland. linguatag has no "remove likely subtags" call.

---
[Index](index.md) · [← Parsing and normalising tags](parsing.md) · [Matching →](matching.md)
