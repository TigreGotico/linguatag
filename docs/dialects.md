# Dialects

<!-- agent-hint
covers: how the lects argument orders tags that name a dialect with a private-use subtag.
source: linguatag/_lects.py:lect_score, linguatag/_lects.py:lect_steps, linguatag/_lects.py:lookup_tags, linguatag/data/lineage.json
generated: no
verify: python scripts/check_doc_page.py docs/dialects.md
see: matching.md, data-and-licence.md
-->

This page shows how to rank tags that differ only in a private-use dialect subtag. A private-use subtag can name a dialect, such as `an-x-cheso` or `pt-PT-x-porto`. BCP 47 gives such a subtag no meaning. By default it adds nothing to the distance, so `an-x-cheso` is as near to `an-x-ansotano` as to `an`.

## Ask for a dialect order

```python
from linguatag import closest_lang

print(closest_lang("an-x-cheso", ["an", "an-x-ansotano"]))                    # an
print(closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="dialect"))   # an-x-ansotano
print(closest_lang("an-x-cheso", ["an", "an-x-ansotano"], lects="standard"))  # an
```

With no `lects`, the tie goes to the first candidate. With `lects="dialect"`, the nearest other dialect comes first and the standard language last. With `lects="standard"`, the standard language comes first and the dialects after it.

## The lect score

`lang_distance` takes the same `lects` argument. It adds a lect score from 0 to 4 to the language distance:

```python
from linguatag import LECT_MODES, lang_distance, lect_steps

print(LECT_MODES)                                                  # ('dialect', 'standard')
print(lect_steps("an-x-cheso", "an"))                              # 1
print(lect_steps("an-x-cheso", "an-x-ansotano"))                   # 2
print(lang_distance("an-x-cheso", "an", lects="dialect"))          # 4
print(lang_distance("an-x-cheso", "an-x-ansotano", lects="dialect"))   # 2
print(lang_distance("an-x-cheso", "an", lects="standard"))         # 1
print(lang_distance("an-x-cheso", "an-x-ansotano", lects="standard"))  # 3
```

`lect_steps` counts the steps between two tags in the dialect tree, or returns `None` when they do not meet. A parent is 1 step away and a sibling 2. The score uses these steps as follows:

| Mode | Standard language | Other dialect |
| --- | --- | --- |
| `"dialect"` | 4 | its steps, at most 3 |
| `"standard"` | 1 | its steps plus 1, at most 4 |

A request for the standard language scores a dialect of it by its steps plus 1, in both modes. `lang_distance` raises `ValueError` for a `lects` value other than `None`, `"dialect"` or `"standard"`. `closest_lang` computes the lect score only for a candidate within `max_distance`, so with no such candidate it returns `None` and does not raise:

```python
from linguatag import closest_lang

print(closest_lang("en", ["fr"], lects="bogus"))  # None
```

The lect score never raises a distance that is 10 or less to a value above 10. So `closest_lang` uses it only to order the candidates that already match.

## An unknown subtag after a lect

A tag can add a private-use subtag that the data does not know, such as a voice name. The tag then reads as the nearest lect that the data knows, as RFC 4647 section 3.4 (Lookup) removes one subtag at a time from the end:

```python
from linguatag import closest_lang

print(closest_lang("pt-BR-x-sp-foo", ["pt", "pt-BR", "pt-BR-x-sp"], lects="standard"))  # pt-BR-x-sp
```

`lookup_tags` gives the tags that Lookup tries, most specific first. A program with its own alias table looks each tag up in turn:

```python
from linguatag import lookup_tags

print(lookup_tags("pt-PT-x-lisboa-foo"))  # ['pt-PT-x-lisboa-foo', 'pt-PT-x-lisboa', 'pt-PT', 'pt']
```

## The dialect tree

`linguatag/data/lineage.json` holds the tree. It is the part of the orthography2ipa spec tree that the lects need: each spec code with a private-use subtag, and its ancestors up to 4 levels above it. Its `source` field names the orthography2ipa commit that it comes from. [Data and licence](data-and-licence.md) shows how to rebuild it.

---
[Index](index.md) · [← Matching](matching.md) · [Genealogy, place and time →](genealogy.md)
