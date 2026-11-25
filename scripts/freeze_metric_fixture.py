"""Freeze orthography2ipa's value of each moved metric on a fixed sample of pairs.

Run it with a Python that has orthography2ipa installed and is not the
linguatag test environment:

    python scripts/freeze_metric_fixture.py linguatag/data/genealogy.json test/data/metric_pairs.json

The tags come from the linguatag genealogy. The tests compare linguatag with
the values in the fixture and never import orthography2ipa.
"""
import json
import random
import sys
import warnings

from orthography2ipa import get
from orthography2ipa import distance as d
from orthography2ipa.script_distance import SCRIPT_REGISTRY, script_distance_by_name
from orthography2ipa.version import VERSION_STR

PAIRS = 600


def sample(tags: list, count: int, rng: random.Random, near: bool = False) -> list:
    """``count`` pairs of tags. With ``near``, two of every three are kin: a
    tag and its parent, siblings, or cousins under one grandparent."""
    known = set(tags)
    children = {}
    for tag in tags:
        parent = get(tag).parent
        if parent in known:
            children.setdefault(parent, []).append(tag)
    kin = [t for t in tags if get(t).parent in known and not get(get(t).parent).clade]
    pairs = []
    for index in range(count):
        if not near or index % 3 == 0:
            pairs.append(rng.sample(tags, 2))
            continue
        tag = rng.choice(kin)
        parent = get(tag).parent
        grand = get(parent).parent
        if index % 3 == 1 or grand not in known:
            other = rng.choice([parent, *children[parent]])
        else:
            other = rng.choice([c for p in children[grand] for c in [p, *children.get(p, [])]])
        pairs.append([tag, other] if other != tag else [tag, parent])
    return pairs


def main() -> None:
    genealogy, out = sys.argv[1], sys.argv[2]
    warnings.simplefilter("ignore")
    rng = random.Random(2612)
    tags = []
    for tag in json.load(open(genealogy, encoding="utf-8"))["nodes"]:
        try:
            if get(tag, strict=True).code == tag:
                tags.append(tag)
        except KeyError:
            pass
    located = [t for t in tags if get(t).location]
    dated = [t for t in tags if get(t).timespan]
    fixture = {"orthography2ipa": VERSION_STR, "tags": len(tags), "metrics": {}}

    def freeze(name, pairs, call, **kwargs):
        fixture["metrics"][name] = {"kwargs": kwargs, "rows": [
            [a, b, call(get(a), get(b), **kwargs)] for a, b in pairs]}

    freeze("ancestry_similarity", sample(tags, PAIRS, rng, near=True), d.ancestry_similarity)
    freeze("ancestry_similarity_temporal", sample(tags, PAIRS, rng, near=True),
           d.ancestry_similarity, temporal_decay=True)
    freeze("ancestry_similarity_depth_1", sample(tags, PAIRS, rng, near=True),
           d.ancestry_similarity, max_depth=1)
    freeze("geographic_distance", sample(located, PAIRS, rng) + sample(tags, 40, rng),
           d.geographic_distance)
    freeze("geographic_distance_km", sample(located, PAIRS, rng), d.geographic_distance, normalize=False)
    freeze("temporal_distance", sample(dated, PAIRS, rng) + sample(tags, 40, rng), d.temporal_distance)
    freeze("temporal_distance_1500", sample(dated, PAIRS, rng), d.temporal_distance, reference_year=1500)
    names = list(SCRIPT_REGISTRY)
    fixture["metrics"]["script_distance_by_name"] = {"kwargs": {}, "rows": [
        [a, b, script_distance_by_name(a, b)] for a in names for b in names]}
    for name, metric in fixture["metrics"].items():
        print(f"{name}: {len(metric['rows'])} pairs", file=sys.stderr)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(fixture, handle, indent=None, ensure_ascii=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
