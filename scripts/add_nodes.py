"""Add new languages and lects to the genealogy, place and time data.

    python scripts/add_nodes.py nodes.json [--update]

``nodes.json`` maps each tag to its facts::

    {"xx-x-new": {"parent": "xx", "family_path": ["Indo-European"],
                  "glottolog_code": null, "wikidata_qid": "Q1",
                  "place": [41.5, -6.4], "years": [1300, null]}}

``parent`` is required. A ``null`` parent makes a root, such as an isolate or
a top-level clade; a tag that starts with ``x-clade-`` is a clade. Without
``family_path`` a node takes the family of its parent, and a root has none. A ``null`` stays in the data: it means that the catalog has no entry.
A tag that the data already holds is refused unless ``--update`` is given.
An update changes only the keys that the file gives. It drops the weighted
``ancestors`` and takes the family of the new parent when the parent changes. The descendants
of a moved node take its new family path in place of its old one and keep the
levels below it, unless the file gives their family path.
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
    if parent is not None and parent not in nodes:
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


def set_family(node: dict, path: list | None) -> None:
    """Give the node a family path, or remove its family when the path is None."""
    if path is None:
        node.pop("family", None)
        node.pop("family_path", None)
    else:
        node.update({"family": " > ".join(path), "family_path": path})


def main() -> None:
    facts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    update = "--update" in sys.argv[2:]
    files = {name: json.loads((DATA / name).read_text(encoding="utf-8")) for name in TABLES}
    nodes = files["genealogy.json"]["nodes"]
    known = sorted(set(facts) & set(nodes))
    if known and not update:
        raise SystemExit(f"already in the data, pass --update to change them: {known}")
    old = {tag: dict(nodes[tag]) for tag in known}
    before = {tag: node.get("family_path", []) for tag, node in nodes.items()}
    for tag, fact in facts.items():
        nodes.setdefault(tag, {})["parent"] = fact.get("parent")
    for tag, fact in facts.items():
        check(tag, fact, nodes)
    def depth(tag: str) -> int:
        return 1 + depth(facts[tag]["parent"]) if facts.get(tag, {}).get("parent") in facts else 0

    for tag in sorted(facts, key=depth):
        fact, node = facts[tag], dict(old.get(tag, {}))
        parent = fact["parent"]
        moved = node.get("parent") != parent
        node["parent"] = parent
        if parent is None:
            del node["parent"]
        if tag.startswith("x-clade-"):
            node["clade"] = True
        if moved:
            node.pop("ancestors", None)
        if "family_path" in fact:
            set_family(node, fact["family_path"])
        elif moved:
            set_family(node, nodes[parent].get("family_path") if parent else None)
        node.update({k: fact[k] for k in CATALOG if k in fact})
        nodes[tag] = node
        if "place" in fact:
            files["places.json"]["places"][tag] = fact["place"]
        if "years" in fact:
            files["times.json"]["years"][tag] = fact["years"]
    children = {}
    for tag, node in nodes.items():
        children.setdefault(node.get("parent"), []).append(tag)
    moved = [tag for tag in facts if old.get(tag, {}).get("parent") != facts[tag]["parent"]]
    while moved:
        tag = moved.pop()
        for child in children.get(tag, []):
            if child in facts or child not in before:
                continue
            # A descendant keeps its own levels below the moved node, such as
            # the name of a clade: only the prefix of the moved node changes.
            prefix, path = before[tag], before[child]
            if path[:len(prefix)] == prefix:
                set_family(nodes[child], nodes[tag].get("family_path", []) + path[len(prefix):] or None)
            moved.append(child)
    for name, data in files.items():
        (DATA / name).write_text(dump(data), encoding="utf-8")
    print(f"{len(facts)} nodes in, {len(facts) - len(known)} added, {len(known)} updated")


if __name__ == "__main__":
    main()
