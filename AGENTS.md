# AGENTS.md

linguatag reads BCP 47 language tags: it normalises them, gives a bare tag its default region and likely script, and measures how near two tags are. Its callers use `closest_lang` to pick a resource for a requested language.

## Map

| Path | Content |
| --- | --- |
| `linguatag/__init__.py` | The public API, in `__all__` |
| `linguatag/standardize.py` | `standardize_lang` |
| `linguatag/bcp47.py` | `parse`, `standardize` and `maximize`, ported from langcodes |
| `linguatag/regions.py` | `default_region`, `with_default_region`, `likely_script` and `OVERRIDES` |
| `linguatag/distance.py` | The CLDR matching distance of UTS #35 section 4.4 |
| `linguatag/matching.py` | `lang_distance`, `closest_lang`, `lang_matches` and `is_arabic_variety` |
| `linguatag/lects.py` | The dialect score for the `lects` argument |
| `linguatag/lineage.py` | `parent`, `ancestors`, `family`, `ancestry_similarity`, `geographic_distance` and `temporal_distance` |
| `linguatag/writing_systems.py` | `script_features`, `script_distance` and `script_distance_by_name` |
| `linguatag/data/` | The CLDR 49, IANA and dialect-tree JSON files |
| `scripts/` | `extract_cldr.py`, `build_lineage.py` and `build_genealogy.py`, which write `linguatag/data/`, `freeze_metric_fixture.py`, which writes `test/data/metric_pairs.json` from orthography2ipa, and `check_doc_page.py`, which checks a README or docs page against the code, and `docs_figures.py`, which writes the SVG files of `docs/figures/` |
| `test/` | The pytest suite |
| `docs/` | The user docs, listed in `docs/index.md` |

## Setup and tests

```
uv venv
uv pip install --prerelease=allow -e '.[test]'
.venv/bin/python -m pytest -q test
```

CI runs the same suite on Python 3.11, 3.12, 3.13 and 3.14 ([build-tests.yml](.github/workflows/build-tests.yml)).

## Hard rules

The package has no runtime dependencies. The `langcodes` extra stays empty so that downstream pins on `linguatag[langcodes]` resolve ([README](README.md#install)).

Nobody edits the files in `linguatag/data/` by hand. Change the script or its source, run it, and commit the script and the data together ([Data and licence](docs/data-and-licence.md)).

Each entry in `OVERRIDES` cites its source in a comment beside it ([Likely subtags and default regions](docs/likely-subtags.md#where-the-default-region-comes-from)).

A pull request title is a conventional commit. A label workflow reads it, and the release workflow uses the label to set the next version ([conventional-label.yaml](.github/workflows/conventional-label.yaml), [release_workflow.yml](.github/workflows/release_workflow.yml)).

The release workflow writes `linguatag/version.py` and `CHANGELOG.md`. Nobody edits them by hand.

## Before a push

1. Run `.venv/bin/python -m pytest -q test`.
2. After a data change, run `python3 scripts/extract_cldr.py` and make sure each "in" count agrees with its "out" count.
3. After a data change or a docs change, run `.venv/bin/python scripts/docs_figures.py --check`. It fails when a committed figure differs from the data. Run `python scripts/docs_figures.py --measure` only to record the timings again.
4. After a docs change, run `.venv/bin/python scripts/check_doc_page.py <page>` for each page that you changed. `test/test_doc_pages.py` runs it for every page with an agent hint.
