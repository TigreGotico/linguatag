# Genealogy, place and time

<!-- agent-hint
covers: the parent, ancestors, family, place and period of a language tag, the three metrics built on them, and the writing-system distance.
source: linguatag/_lineage.py, linguatag/_writing_systems.py, linguatag/data/genealogy.json, linguatag/data/places.json, linguatag/data/times.json, linguatag/data/lects.json, linguatag/data/scripts.json, scripts/add_nodes.py
generated: no for the page. The data files are the source of truth. scripts/add_nodes.py edits genealogy.json, places.json, times.json and lineage.json.
verify: python scripts/check_doc_page.py docs/genealogy.md
see: dialects.md, data-and-licence.md
-->

This page shows how to ask where a language comes from, where it is spoken and when. It also shows how to measure how far apart two languages or two writing systems are. The data comes from the orthography2ipa spec files at one commit. linguatag never imports orthography2ipa.

## Walk up the tree

Each language and lect has one genealogical parent. `parent` gives it, and `ancestors` follows the parents to the top, nearest first:

```python
from linguatag import ancestors, family, family_path, parent

print(parent("pt-PT-x-porto"))            # pt-PT-x-minho
print(ancestors("pt-PT-x-porto")[:3])     # ['pt-PT-x-minho', 'pt-PT', 'pt-PT-x-medieval']
print(ancestors("ars-SA-x-qassim")[:4])   # ['ars-SA', 'ar-x-peninsul', 'arb', 'xpa']
print(family("pt-PT-x-porto"))            # Indo-European > Italic > Romance > Ibero-Romance
print(family_path("pt-PT-x-porto"))       # ('Indo-European', 'Italic', 'Romance', 'Ibero-Romance')
```

A clade is a node of the classification, such as `x-clade-iberrom`. It is a step in the chain, and it is a language of no phonology. A tag that the data does not hold has no parent, no ancestors and no family:

```python
from linguatag import ancestors, family, parent

print(parent("qqq-x-nothing"))     # None
print(ancestors("qqq-x-nothing"))  # []
print(repr(family("qqq-x-nothing")))  # ''
```

Every function standardizes its tags first, so `PT-pt-X-PORTO` and `pt-PT-x-porto` give the same answer.

A macrolanguage with a region that has no node of its own reads the individual language that most of that region speaks, when CLDR 49 `territoryInfo` gives it 50 percent or more. A member with an ISO 639-1 code, such as Indonesian (`id`) or Norwegian Bokmål (`nb`), is a standard language of its own, so it does not take the tag. Otherwise the tag reads the macrolanguage. The rule applies to every function on this page, the distances included:

```python
from linguatag import catalog_ids

print(catalog_ids("ar-EG")["glottolog_code"])  # egyp1253
print(catalog_ids("zh-HK")["glottolog_code"])  # cant1236
print(catalog_ids("ar-SA")["glottolog_code"])  # stan1318
```

CLDR gives Egyptian Arabic 64 percent of Egypt and Cantonese 90 percent of Hong Kong. It gives Najdi Arabic 3 percent of Saudi Arabia, so `ar-SA` stays Arabic. `zh-HK` has the start year of `yue`, and the data holds none, so `temporal_distance` gives `None` for it.

## Find a tag in other catalogs

The tree models regional descent in more depth than Glottolog, so its shape can differ from the Glottolog tree. `catalog_ids` links each node to the other catalogs:

```python
from linguatag import catalog_ids

print(catalog_ids("pt-BR"))          # {'glottolog_code': 'braz1246', 'wikidata_qid': 'Q750553'}
print(catalog_ids("an-x-cheso"))     # {'glottolog_code': None, 'wikidata_qid': 'Q3573993'}
print(catalog_ids("qqq-x-nothing"))  # {}
```

A key with the value `None` means that the catalog has no entry for the variety. A key that is absent means that no one checked.

## Measure two tags

`ancestry_similarity` is 1.0 for the same tag and 0.0 for two tags with no common ancestor. The ancestors of a tag carry weights, and a weight can be below 1.0 for a substrate or a neighbour that left traces. The similarity of two tags is the product of the weights along their best connecting paths. A clade adds nothing, so the trace skips it.

```python
from linguatag import ancestry_similarity

print(round(ancestry_similarity("pt-PT", "pt-PT-x-porto"), 4))  # 0.7381
print(round(ancestry_similarity("pt-PT", "es-ES"), 4))           # 0.4131
print(round(ancestry_similarity("pt-PT", "de-DE"), 4))           # 0.0605
print(ancestry_similarity("pt-PT", "pt-PT"))                   # 1.0
```

A path also loses weight with the years between an ancestor and its descendant, with a half-life of 2,000 years (`decay_halflife`). So an old shared ancestor, such as Proto-Indo-European for Portuguese and German, counts for less than a recent one, such as Hispanic Latin for Portuguese and Spanish. `temporal_decay=False` turns this off. The argument `max_depth` limits the levels that the trace follows above each tag.

`geographic_distance` gives the great-circle distance of the points of two tags. A point stands for an area, so trust the number for dialects of one language and not for a language spoken on several continents. It returns `None` when a tag has no point:

```python
from linguatag import geographic_distance

print(round(geographic_distance("pt-PT", "es-ES", normalize=False)))  # 378
print(round(geographic_distance("pt-PT", "es-ES"), 4))                # 0.0189
print(geographic_distance("pt-PT", "qqq-x-nothing"))                  # None
```

Without `normalize=False`, the distance is a share of half the circumference of the Earth. With it, the distance is in kilometres.

`temporal_distance` is one minus the share of time in which two tags are both spoken. A tag with no end year is spoken until `reference_year`, which is 2025 by default. It returns `None` when a tag has no period:

```python
from linguatag import temporal_distance

print(temporal_distance("la", "pt-PT"))                    # 1.0
print(round(temporal_distance("pt-PT", "es-ES"), 4))       # 0.3527
print(temporal_distance("pt-PT", "qqq-x-nothing"))         # None
```

## Compare writing systems

`script_distance_by_name` compares two of the 21 writing systems of `scripts.json` by their type, direction, vowel marking, case and ancestor scripts. `script_features` gives the typology of one system, and `script_distance` compares two such typologies:

```python
from linguatag import script_distance, script_distance_by_name, script_features

print(round(script_distance_by_name("Latin", "Greek"), 4))   # 0.1667
print(round(script_distance_by_name("Latin", "Arabic"), 2))  # 0.57
print(round(script_distance_by_name("Latin", "Hanzi"), 2))   # 0.81
print(script_features("Arabic")["type"])                     # abjad
print(script_distance(script_features("Latin"), script_features("Latin")))  # 0.0
```

## The data files

| File | Holds |
| --- | --- |
| `genealogy.json` | For each tag: its `parent`, its weighted `ancestors` when the spec lists them, its `family`, its `family_path` and `clade` when the tag is a clade node. The `sources` table gives the source of the edge from a tag to its parent; `NOT FOUND` marks an edge that a source check found no source for. A tag that is not in the table has no source check |
| `places.json` | The latitude and longitude of each tag that has a point |
| `times.json` | The start year and end year of each tag that has a period. The start year is the year of the earliest attested distinct variety. A living language has `null` as its end year. The `sources` table gives the source of a corrected period; `NOT FOUND` marks a tag whose period was removed because no source supports it, and `WIKIPEDIA-ONLY` marks a year with no primary source |
| `lects.json` | Each private-use lect with its name and the lists `regions`, `islands` and `cities` that it covers |
| `scripts.json` | The 21 writing systems and the distance of each pair of script types |

Each file names the orthography2ipa commit that it comes from in its `source` field. After a first build, people edit these files in linguatag. `lects.json` has empty coverage lists. An orthography2ipa spec states the regions, islands and cities of a lect in prose only, and the build script copies no prose.

[Data and licence](data-and-licence.md) shows how to rebuild the files.

---
[Index](index.md) · [← Dialects](dialects.md) · [Data and licence →](data-and-licence.md)
