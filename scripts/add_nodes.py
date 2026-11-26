"""Add new languages and lects to the genealogy, place and time data.

    python scripts/add_nodes.py nodes.json [--update]

``nodes.json`` maps each tag to its facts::

    {"xx-x-new": {"parent": "xx", "family_path": ["Indo-European"],
                  "glottolog_code": null, "wikidata_qid": "Q1",
                  "place": [41.5, -6.4], "years": [1300, null]}}

``parent`` is required. Without ``family_path`` a node takes the family of its
parent. A ``null`` stays in the data: it means that the catalog has no entry.
A tag that the data already holds is refused unless ``--update`` is given.
An update keeps the weighted ``ancestors`` when the parent stays the same.
"""
import json
import re
import sys
from pathlib import Path

from linguatag import standardize_lang

DATA = Path(__file__).resolve().parent.parent / "linguatag" / "data"
TABLES = {"genealogy.json": "nodes", "places.json": "places", "times.json": "years"}
CATALOG = ("glottolog_code", "wikidata_qid")
GLOTTOCODE = re.compile(r"^[a-z]{4}[0-9]{4}$")
QID = re.compile(r"^Q[1-9][0-9]*$")


def dump(data: dict) -> str:
    """The data file format: one line for each scalar key and each table entry."""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            entries = ",\n".join(f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                                 for k, v in sorted(value.items()))
            lines.append(f'"{key}": {{\n{entries}\n}}')
        else:
            lines.append(f'"{key}": {json.dumps(value, ensure_ascii=False)}')
    return "{\n" + ",\n".join(lines) + "\n}\n"


def check(tag: str, fact: dict, nodes: dict) -> None:
    if standardize_lang(tag) != tag:
        raise ValueError(f"{tag!r} is not a standard tag; use {standardize_lang(tag)!r}")
    parent = fact.get("parent")
    if parent not in nodes:
        raise ValueError(f"{tag!r}: parent {parent!r} is not in the genealogy")
    node, seen = parent, {tag}
    while node:
        if node in seen:
            raise ValueError(f"{tag!r}: the parent chain makes a cycle at {node!r}")
        seen.add(node)
        node = nodes.get(node, {}).get("parent")
    code, qid = fact.get("glottolog_code"), fact.get("wikidata_qid")
    if code is not None and not GLOTTOCODE.match(code):
        raise ValueError(f"{tag!r}: {code!r} is not a glottocode")
    if qid is not None and not QID.match(qid):
        raise ValueError(f"{tag!r}: {qid!r} is not a Wikidata QID")
    unknown = set(fact) - {"parent", "family_path", "place", "years", *CATALOG}
    if unknown:
        raise ValueError(f"{tag!r}: unknown fields {sorted(unknown)}")


def main() -> None:
    facts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    update = "--update" in sys.argv[2:]
    files = {name: json.loads((DATA / name).read_text(encoding="utf-8")) for name in TABLES}
    nodes = files["genealogy.json"]["nodes"]
    known = sorted(set(facts) & set(nodes))
    if known and not update:
        raise SystemExit(f"already in the data, pass --update to change them: {known}")
    old = {tag: dict(nodes[tag]) for tag in known}
    for tag, fact in facts.items():
        nodes.setdefault(tag, {})["parent"] = fact.get("parent")
    for tag, fact in facts.items():
        check(tag, fact, nodes)
    def depth(tag: str) -> int:
        return 1 + depth(facts[tag]["parent"]) if facts.get(tag, {}).get("parent") in facts else 0

    for tag in sorted(facts, key=depth):
        fact = facts[tag]
        path = fact.get("family_path", nodes[fact["parent"]].get("family_path", []))
        node = {"parent": fact["parent"]}
        if old.get(tag, {}).get("parent") == fact["parent"] and "ancestors" in old[tag]:
            node["ancestors"] = old[tag]["ancestors"]
        node.update({"family": " > ".join(path), "family_path": path})
        node.update({k: fact[k] for k in CATALOG if k in fact})
        nodes[tag] = node
        if "place" in fact:
            files["places.json"]["places"][tag] = fact["place"]
        if "years" in fact:
            files["times.json"]["years"][tag] = fact["years"]
    for name, data in files.items():
        (DATA / name).write_text(dump(data), encoding="utf-8")
    print(f"{len(facts)} nodes in, {len(facts) - len(known)} added, {len(known)} updated")


if __name__ == "__main__":
    main()
