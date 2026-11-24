# linguatag

<!-- agent-hint
covers: what linguatag does, a quickstart, its place in the stack, and how to install it.
source: linguatag/__init__.py:__all__, linguatag/matching.py, linguatag/regions.py, linguatag/standardize.py, pyproject.toml
generated: no
verify: python scripts/check_doc_page.py README.md
see: docs/index.md, docs/getting-started.md, AGENTS.md
-->

linguatag reads BCP 47 language tags. It puts a tag in one canonical form and gives a bare tag its default region and its likely script. It also measures how near two tags are. It picks the best tag from a list of available tags. The package carries all its data: CLDR 49, the IANA Language Subtag Registry, and a dialect tree from orthography2ipa in `lineage.json`.

```python
from linguatag import closest_lang, lang_distance, likely_script, standardize_lang, with_default_region

print(standardize_lang("en_us"))                       # en-US
print(with_default_region("pt"))                       # pt-PT
print(likely_script("zh-TW"))                          # Hant
print(lang_distance("pt", "pt-BR"))                    # 5
print(closest_lang("en-AU", ["fr-FR", "en-US"]))       # en-US
print(closest_lang("de", ["fr", "it"]))                # None
```

A bare tag means its motherland: `pt` is `pt-PT` and `en` is `en-GB`. `closest_lang` returns the candidate string as you gave it, or `None` when no candidate is near enough.

## Where this fits

Alone: tag normalisation and language matching for any program, with `from linguatag import closest_lang`.
In the stack: the base library for language tags. text2spoken, scriptconv, phoonnx, orthography2ipa and ovos-spec-tools call it to pick a resource for a requested language. It calls no other stack library.
Through scriptconv: `uv pip install --prerelease=allow "scriptconv[phonemizers]"`.

<!-- agent-hint: the langcodes extra installs nothing. Do not add langcodes as a dependency. -->
## Install

```
uv pip install --prerelease=allow linguatag
```

linguatag needs Python 3.11 or later and has no dependencies. The `langcodes` extra is empty. It installs nothing, and it exists so that a pin on `linguatag[langcodes]` resolves.

## Documentation

| Page | What it covers |
| --- | --- |
| [Getting started](docs/getting-started.md) | A walk-through of the main calls, with real output |
| [Parsing and normalising tags](docs/parsing.md) | `standardize_lang`, and the parser in `linguatag.bcp47` |
| [Likely subtags and default regions](docs/likely-subtags.md) | `likely_script`, `default_region`, `with_default_region` and `maximize` |
| [Matching](docs/matching.md) | `lang_distance`, `closest_lang`, `lang_matches`, `max_distance`, `und` and private-use tags |
| [Dialects](docs/dialects.md) | The `lects` argument for tags with a private-use dialect subtag |
| [Data and licence](docs/data-and-licence.md) | The CLDR 49 and IANA data files, and how to regenerate them |

Start with [Getting started](docs/getting-started.md), or see the [docs index](docs/index.md). Contributors read [AGENTS.md](AGENTS.md).

## Licence

linguatag is under the Apache License 2.0. The parser and the distance code are a port of langcodes 3.5.1 (MIT). The data files hold CLDR data under the Unicode License v3, and IANA registry data under CC0.

[NOTICE](NOTICE) and [LICENSE-CLDR](LICENSE-CLDR) give the full terms.
