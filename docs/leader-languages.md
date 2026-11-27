# Leader languages

<!-- agent-hint
covers: the normalised tag, likely subtags, default region, macrolanguage step, family and data source of each leader tag.
source: scripts/docs_figures.py:leader_languages, linguatag/_standardize.py:standardize_lang, linguatag/_bcp47.py:maximize, linguatag/_regions.py:default_region, linguatag/_lineage.py:family, linguatag/_lineage.py:catalog_ids
generated: yes, by scripts/docs_figures.py
verify: python scripts/docs_figures.py --check
see: likely-subtags.md, genealogy.md, data-and-licence.md
-->

This page shows what linguatag returns for each leader tag. The script `scripts/docs_figures.py` writes the table from the public API. Do not edit the table by hand.

Each column comes from one call:

- **Normalised tag** is the result of `standardize_lang`.
- **Script** and **region** are the subtags that `maximize` adds from CLDR likely subtags.
- **Default region** is the result of `default_region`. The table shows it only for a tag that has no region subtag.
- **Macrolanguage step** is the language that `maximize` returns when it is different from the language of the tag. A dash means that `maximize` keeps the language.
- **Family** is the result of `family`. A dash means that linguatag returns no value.
- **Catalog ids** is the result of `catalog_ids`. A dash means that linguatag returns no value.
- **Data source** is the `source` field of each data file that gives a fact in the row.

| Tag | Normalised tag | Script | Region | Default region | Macrolanguage step | Family | Catalog ids | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pt-PT` | `pt-PT` | Latn | PT | - | - | Indo-European > Italic > Romance > Ibero-Romance | glottolog_code: port1283, wikidata_qid: Q5146 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `pt-BR` | `pt-BR` | Latn | BR | - | - | Indo-European > Italic > Romance > Ibero-Romance | glottolog_code: braz1246, wikidata_qid: Q750553 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `es-CO` | `es-CO` | Latn | CO | - | - | Indo-European > Italic > Romance > Ibero-Romance | glottolog_code: no entry, wikidata_qid: Q1115875 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `fr-FR` | `fr-FR` | Latn | FR | - | - | Indo-European > Italic > Romance > Gallo-Romance | glottolog_code: stan1290, wikidata_qid: Q150 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `it-IT` | `it-IT` | Latn | IT | - | - | Indo-European > Italic > Romance > Italo-Romance | glottolog_code: ital1282, wikidata_qid: Q652 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `de-DE` | `de-DE` | Latn | DE | - | - | Indo-European > Germanic > Northwest Germanic > West Germanic | glottolog_code: stan1295, wikidata_qid: Q188 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `nl-NL` | `nl-NL` | Latn | NL | - | - | Indo-European > Germanic > Northwest Germanic > West Germanic | glottolog_code: dutc1256, wikidata_qid: Q7411 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `da-DK` | `da-DK` | Latn | DK | - | - | Indo-European > Germanic > Northwest Germanic > North Germanic | glottolog_code: dani1285, wikidata_qid: Q9035 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `kab` | `kab` | Latn | DZ | DZ | - | Afro-Asiatic > Berber | glottolog_code: kaby1243, wikidata_qid: Q35853 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `hi-IN` | `hi-IN` | Deva | IN | - | - | Indo-European > Indo-Iranian > Indo-Aryan | glottolog_code: hind1269, wikidata_qid: Q1568 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `bn-IN` | `bn-IN` | Beng | IN | - | - | Indo-European > Indo-Iranian > Indo-Aryan | glottolog_code: beng1280, wikidata_qid: Q9610 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |
| `mwr` | `mwr` | Deva | IN | IN | - | Indo-European > Indo-Iranian > Indo-Aryan | glottolog_code: no entry, wikidata_qid: Q56312 | aliases.json: CLDR 49, cldr-json cldr-core/supplemental/aliases.json<br>likely_subtags.json: CLDR 49, cldr-json cldr-core/supplemental/likelySubtags.json<br>genealogy.json: TigreGotico/orthography2ipa@1c30a9d4af3f335653f08ffdd836c4fbb4ff98e5 |

---
[Index](index.md) · [← Reference](reference.md)
