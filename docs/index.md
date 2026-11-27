# linguatag documentation

<!-- agent-hint
covers: the reading order of the linguatag docs, with one line for each page.
source: docs/*.md
generated: no
verify: python scripts/check_doc_page.py docs/index.md
see: getting-started.md
-->

This index lists the linguatag docs pages in reading order. linguatag reads BCP 47 language tags, gives a bare tag its default region and likely script, and measures how near two tags are. The first page is a walk-through. The pages after it explain one topic each.

![Horizontal bars of the genealogy nodes in each top-level family. The 12 largest families are Atlantic-Congo, Austronesian, Indo-European, Sino-Tibetan, Afro-Asiatic, Nuclear Trans New Guinea, Otomanguean, Austroasiatic, Sign Language, Pama-Nyungan, Tai-Kadai and Bookkeeping. One more bar groups the other families, and one bar holds the nodes with no family. The Genealogy page explains the tree.](figures/genealogy-families.svg)

| Page | What it covers |
| --- | --- |
| [Getting started](getting-started.md) | Install the package and run each main call, with real output |
| [Parsing and normalising tags](parsing.md) | `standardize_lang`, `parse_tag`, `LanguageTag` and `LanguageTagError` |
| [Likely subtags and default regions](likely-subtags.md) | `likely_script`, `default_region`, `with_default_region`, `OVERRIDES` and `maximize` |
| [Matching](matching.md) | `lang_distance`, `closest_lang` and `lang_matches`, the steps of a match, the distance ladder, the `max_distance` argument, ties, `und` and private-use tags, Arabic and Chinese rules |
| [Dialects](dialects.md) | The `lects` argument, `lect_steps` and the lect tree in `lineage.json` |
| [Genealogy, place and time](genealogy.md) | `parent`, `ancestors`, `family`, `ancestry_similarity`, `geographic_distance`, `temporal_distance` and `script_distance_by_name`, with the data files that they read |
| [Data and licence](data-and-licence.md) | The CLDR 49 and IANA data files with their sizes, the scripts that write them, and their licences |
| [Performance](performance.md) | What the import and the first call cost, what a warm call costs, and how to measure both |
| [Reference](reference.md) | The signature and one example of each name in `__all__` |
| [Leader languages](leader-languages.md) | What `standardize_lang`, `maximize`, `default_region`, `family` and `catalog_ids` return for each leader tag, with the data source of each fact |

The [README](../README.md) has the quickstart and the place of linguatag in the stack.

[AGENTS.md](../AGENTS.md) tells contributors how to test and what a pull request needs.
