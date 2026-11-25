# Data and licence

<!-- agent-hint
covers: the data files that linguatag reads, how to regenerate them, and their licences.
source: linguatag/data/*.json, scripts/extract_cldr.py, scripts/build_lineage.py, scripts/build_genealogy.py, NOTICE, LICENSE-CLDR
generated: no for the page. scripts/extract_cldr.py writes the five CLDR and IANA files, scripts/build_lineage.py writes lineage.json and scripts/build_genealogy.py writes the five genealogy files, so edit the scripts, never the JSON. scripts/docs_figures.py writes docs/figures/data-files.svg.
verify: python scripts/docs_figures.py --check && python scripts/check_doc_page.py docs/data-and-licence.md
see: ../NOTICE, ../LICENSE-CLDR
-->

This page lists the data files that linguatag reads, shows how to regenerate them, and gives their licences. linguatag reads all its data from JSON files in `linguatag/data`. It never reads the data of another installed package. Each file names its source in a `source` field.

## The data files

| File | Source | What reads it |
| --- | --- | --- |
| `likely_subtags.json` | CLDR 49 `supplemental/likelySubtags.json` | `maximize`, `default_region` and `likely_script` (UTS #35 section 4.3) |
| `aliases.json` | CLDR 49 `supplemental/aliases.json`: language, script, territory and variant aliases | canonical form (UTS #35 Annex C) |
| `subtags.json` | the IANA Language Subtag Registry, without the language records: each extlang, script, region and variant subtag and each grandfathered and redundant tag, with its Deprecated, Preferred-Value, Prefix, Suppress-Script and Macrolanguage fields | parsing and canonical form (RFC 5646) |
| `language_subtags.json` | the language records of the same registry, a file of their own so that a caller who reads no language record does not parse them | `standardize` (Suppress-Script), `closest_lang` and `standardize_lang` (Preferred-Value) |
| `language_matching.json` | CLDR 49 `supplemental/languageMatching.json`, `written-new`: paradigm locales, match variables and `languageMatch` rules | `lang_distance` (UTS #35 section 4.4) |
| `territory_containment.json` | CLDR 49 `supplemental/territoryContainment.json`: the regions in each macroregion | the region clusters of `lang_distance` |
| `lineage.json` | the orthography2ipa spec files at one commit | the `lects` argument |
| `genealogy.json` | the same spec files at one commit: the parent, weighted ancestors, family and clade flag of each tag | `parent`, `ancestors`, `family` and `ancestry_similarity` |
| `places.json` | the same spec files: the latitude and longitude of each tag | `geographic_distance` |
| `times.json` | the same spec files: the start and end year of each tag | `temporal_distance` and the temporal decay of `ancestry_similarity` |
| `lects.json` | the same spec files: the name of each private-use lect, with coverage lists that people fill | nothing yet; it holds the regions, islands and cities of each lect |
| `scripts.json` | the orthography2ipa script typology at the same commit | `script_distance` and `script_distance_by_name` |

The figure shows the size of each file and how many records it holds.

![Horizontal bars of the size of each data file: genealogy.json 820 kB and 7,677 records, places.json 196 kB and 7,256 records, likely_subtags.json 191 kB and 7,868 records, language_subtags.json 135 kB and 8,276 records, aliases.json 47 kB and 1,145 records, subtags.json 40 kB and 1,022 records, lects.json 19 kB and 190 records, language_matching.json 17 kB and 391 records, times.json 15 kB and 605 records, lineage.json 7 kB and 265 records, territory_containment.json 5 kB and 35 records, scripts.json 5 kB and 49 records.](figures/data-files.svg)

*Figure: the 12 data files by size. Read the bars: `genealogy.json` and `places.json` hold about 68 percent of the 1,497 kB.*

To see the source of each file:

```
$ python3 -c "import json, pathlib; [print(p.name, '|', json.loads(p.read_text())['source']) for p in sorted(pathlib.Path('linguatag/data').glob('*.json'))]"
aliases.json | CLDR 49, cldr-json cldr-core/supplemental/aliases.json
language_matching.json | CLDR 49, cldr-json cldr-core/supplemental/languageMatching.json, written-new
language_subtags.json | IANA Language Subtag Registry, File-Date: 2026-11-18
lects.json | TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5
likely_subtags.json | CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json
genealogy.json | TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5
lineage.json | TigreGotico/orthography2ipa@1e6e911705761de8d5724276187c4903ae92eaf4
places.json | TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5
scripts.json | TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5
subtags.json | IANA Language Subtag Registry, File-Date: 2026-11-18
territory_containment.json | CLDR 49, cldr-json cldr-core/supplemental/territoryContainment.json
times.json | TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5
```

Nobody edits these files by hand. To change one, change its script or its source, run the script, and commit the script and the data together.

## The loader is read-only

`bcp47.load_data` returns a read-only view of the parsed JSON. Dictionaries are frozen dicts and JSON arrays are tuples, so a caller cannot change package data for every other caller. The view is made once when the file is read and shared, so a repeated call costs no copy. `registry` returns a read-only view of the records of one kind, made the same way. The language records are in `language_subtags.json`, so `load_data("subtags.json")` holds no `language` key; read them with `registry("language")` or `load_data("language_subtags.json")`.

The view stays a dict, so JSON, copy and pickle work. A deep copy or an unpickled value is a plain, mutable dict. A shallow copy leaves the nested views frozen. To change package data for one call only, make a deep copy first.

```python
from linguatag.bcp47 import load_data
from linguatag.lects import lect_steps

print(lect_steps("pt-x-central", "pt-x-minhoto"))  # 2
try:
    load_data("lineage.json")["parents"]["pt-x-central"] = "pt-x-minhoto"
except TypeError:
    print("TypeError")  # TypeError
print(lect_steps("pt-x-central", "pt-x-minhoto"))  # 2
```

## Regenerate the CLDR and IANA files

`scripts/extract_cldr.py` writes the first five files. It needs only the Python standard library. By default it downloads the CLDR 49 release of `cldr-json` and the IANA registry. Run it after a CLDR release or an IANA registry change.

1. Go to the root of a linguatag checkout.
2. Run the script:

   ```
   $ python3 scripts/extract_cldr.py
   likelySubtags: 7868 in, 7868 out
   languageAlias: 502 in, 502 out
   scriptAlias: 1 in, 1 out
   territoryAlias: 640 in, 640 out
   variantAlias: 2 in, 2 out
   registry: 9298 records in, 9298 out
   languageMatch: 381 in, 381 out
   territoryContainment: 46 in, 35 out (11 status entries left out)
   ```

3. Make sure that each "in" count agrees with its "out" count. The territory containment file leaves out the status entries on purpose.
4. Run `git diff --stat linguatag/data` to see which files changed.
5. Run the tests.

The counts change when the sources change. To read a source from a local file, give the paths in this order: likely subtags, aliases, IANA registry, language matching, territory containment. A missing argument takes the default URL:

```
python3 scripts/extract_cldr.py likelySubtags.json aliases.json language-subtag-registry languageMatching.json territoryContainment.json
```

To move to a different CLDR release, change the `CLDR_JSON` constant in the script.

## Regenerate the dialect tree

`scripts/build_lineage.py` writes `lineage.json` from an orthography2ipa clone. It reads the spec files at a git ref, so the clone needs no checkout of that ref. The second argument defaults to `origin/dev`. The script imports linguatag, so run it with a Python that has linguatag installed. This run uses the commit that the `source` field of the committed `lineage.json` names, so it writes the same file:

```
$ python scripts/build_lineage.py ~/path/to/orthography2ipa 1e6e911705761de8d5724276187c4903ae92eaf4
7672 spec files in, 7671 codes read
265 parent links out
```

Run it again when orthography2ipa adds, renames or moves a lect.

## Regenerate the genealogy files

`scripts/build_genealogy.py` writes `genealogy.json`, `places.json`, `times.json`, `lects.json` and `scripts.json` from an orthography2ipa clone. It reads the spec files and `script_distance.py` at a git ref, so the clone needs no checkout, and it never imports orthography2ipa. Run it with a Python that has linguatag installed. It overwrites `lects.json`, so run it once as the first build. After that, people edit the files in linguatag.

```
$ python scripts/build_genealogy.py ~/path/to/orthography2ipa 1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5
7680 spec files in, 7679 specs read
alias yol dropped: standardizes to enm
21 scripts, 28 type distances read
7679 specs in: 7677 genealogy nodes, 7256 places, 605 timespans, 190 lects out
```

Two codes that standardize to one tag give one node, and the code that already is the tag wins. `scripts/freeze_metric_fixture.py` writes `test/data/metric_pairs.json`. Run it with a Python that has orthography2ipa installed and that is not the test environment. The tests compare linguatag with the values in that file.

## Licences

linguatag is under the Apache License 2.0 ([LICENSE](../LICENSE)).

`linguatag/bcp47.py` and `linguatag/distance.py` port code from langcodes 3.5.1, Copyright (C) 2021 Robyn Speer, under the MIT License. The ported parts are `tag_parser.py`, `language_distance.py`, and the `Language.get`, `Language.maximize`, `Language.distance` and `standardize_tag` functions.

The four CLDR files hold Unicode CLDR release 49 data (cldr-json 49.0.0) under the Unicode License v3. The copyright is (C) 2015-2024 Unicode, Inc. [LICENSE-CLDR](../LICENSE-CLDR) holds the full notice.

`subtags.json` and `language_subtags.json` hold data from the IANA Language Subtag Registry. IANA and the IETF Trust dedicate their rights in the protocol registries to the public domain under CC0 1.0.

[NOTICE](../NOTICE) gives the full text of each attribution.

---
[Index](index.md) · [← Genealogy, place and time](genealogy.md) · [Performance →](performance.md)
