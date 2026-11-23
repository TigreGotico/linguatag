# Data and licence

<!-- agent-hint
covers: the data files that linguatag reads, how to regenerate them, and their licences.
source: linguatag/data/*.json, scripts/extract_cldr.py, scripts/build_lineage.py, NOTICE, LICENSE-CLDR
generated: no. scripts/extract_cldr.py writes the five CLDR and IANA files and scripts/build_lineage.py writes lineage.json, so edit the scripts, never the JSON.
verify: `python3 -c "import json,pathlib,sys;t=pathlib.Path(sys.argv[1]).read_text();g=[f.name+' | '+json.loads(f.read_text())['source'] for f in sorted(pathlib.Path('linguatag/data').glob('*.json'))];m=[l for l in g if l not in t];print('OK',len(g)) if not m else sys.exit('MISSING '+repr(m))" docs/data-and-licence.md`
see: ../NOTICE, ../LICENSE-CLDR
-->

This page lists the data files that linguatag reads, shows how to regenerate them, and gives their licences. linguatag reads all its data from JSON files in `linguatag/data`. It never reads the data of another installed package. Each file names its source in a `source` field.

## The data files

| File | Source | What reads it |
| --- | --- | --- |
| `likely_subtags.json` | CLDR 49 `supplemental/likelySubtags.json` | `maximize`, `default_region` and `likely_script` (UTS #35 section 4.3) |
| `aliases.json` | CLDR 49 `supplemental/aliases.json`: language, script, territory and variant aliases | canonical form (UTS #35 Annex C) |
| `subtags.json` | the IANA Language Subtag Registry: each subtag with its Deprecated, Preferred-Value, Prefix, Suppress-Script and Macrolanguage fields | parsing and canonical form (RFC 5646) |
| `language_matching.json` | CLDR 49 `supplemental/languageMatching.json`, `written-new`: paradigm locales, match variables and `languageMatch` rules | `lang_distance` (UTS #35 section 4.4) |
| `territory_containment.json` | CLDR 49 `supplemental/territoryContainment.json`: the regions in each macroregion | the region clusters of `lang_distance` |
| `lineage.json` | the orthography2ipa spec files at one commit | the `lects` argument |

To see the source of each file:

```
$ python3 -c "import json, pathlib; [print(p.name, '|', json.loads(p.read_text())['source']) for p in sorted(pathlib.Path('linguatag/data').glob('*.json'))]"
aliases.json | CLDR 49, cldr-json cldr-core/supplemental/aliases.json
language_matching.json | CLDR 49, cldr-json cldr-core/supplemental/languageMatching.json, written-new
likely_subtags.json | CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json
lineage.json | TigreGotico/orthography2ipa@1e6e911705761de8d5724276187c4903ae92eaf4
subtags.json | IANA Language Subtag Registry, File-Date: 2026-11-18
territory_containment.json | CLDR 49, cldr-json cldr-core/supplemental/territoryContainment.json
```

Nobody edits these files by hand. To change one, change its script or its source, run the script, and commit the script and the data together.

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

## Licences

linguatag is under the Apache License 2.0 ([LICENSE](../LICENSE)).

`linguatag/bcp47.py` and `linguatag/distance.py` port code from langcodes 3.5.1, Copyright (C) 2021 Robyn Speer, under the MIT License. The ported parts are `tag_parser.py`, `language_distance.py`, and the `Language.get`, `Language.maximize`, `Language.distance` and `standardize_tag` functions.

The four CLDR files hold Unicode CLDR release 49 data (cldr-json 49.0.0) under the Unicode License v3. The copyright is (C) 2015-2024 Unicode, Inc. [LICENSE-CLDR](../LICENSE-CLDR) holds the full notice.

`subtags.json` holds data from the IANA Language Subtag Registry. IANA and the IETF Trust dedicate their rights in the protocol registries to the public domain under CC0 1.0.

[NOTICE](../NOTICE) gives the full text of each attribution.

---
[Index](index.md) · [← Dialects](dialects.md)
