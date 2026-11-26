"""Write the genealogy, place, time, lect and script files of linguatag/data/
from one orthography2ipa commit.

    python scripts/build_genealogy.py ~/path/to/orthography2ipa origin/dev

The files are read from git objects, so no checkout is needed and
orthography2ipa is never imported. Each output file names the commit in its
``source`` field. After the first run people edit the files in linguatag; run
the script again only to take a new orthography2ipa commit as the base.

``genealogy.json``  every spec key: parent, weighted ancestors, family, clade.
``places.json``     latitude and longitude of each key that has a location.
``times.json``      start and end year of each key that has a timespan.
``lects.json``      each private-use lect with its name and coverage. A spec
                    holds coverage as prose in its notes only, so the lists
                    start empty and people fill them.
``scripts.json``    the writing-system table and the script-type distances.
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

from linguatag._standardize import standardize_lang

DATA = Path(__file__).resolve().parent.parent / "linguatag" / "data"
SPECS = "orthography2ipa/data"
SCRIPT_DISTANCE = "orthography2ipa/script_distance.py"


def git(repo: str, *args: str, stdin: bytes = b"") -> bytes:
    return subprocess.run(["git", "-C", repo, *args], input=stdin,
                          capture_output=True, check=True).stdout


def read_specs(repo: str, ref: str) -> dict:
    names = git(repo, "ls-tree", "-r", "--name-only", ref, SPECS).decode().split()
    names = [n for n in names if n.endswith(".json")]
    blobs = git(repo, "cat-file", "--batch",
                stdin="\n".join(f"{ref}:{n}" for n in names).encode())
    specs, pos = {}, 0
    while pos < len(blobs):
        end = blobs.index(b"\n", pos)
        size = int(blobs[pos:end].split()[2])
        spec = json.loads(blobs[end + 1:end + 1 + size])
        pos = end + 1 + size + 1
        if isinstance(spec, dict) and spec.get("code"):
            specs[spec["code"]] = spec
    print(f"{len(names)} spec files in, {len(specs)} specs read", file=sys.stderr)
    return specs


def classification_parent(spec: dict):
    """The spec it inherits from, else its PARENT-role ancestor."""
    if spec.get("inherits"):
        return spec["inherits"]
    return next((a["code"] for a in spec.get("ancestors", []) if a["role"] == "parent"), None)


def family_path(specs: dict, code: str, memo: dict) -> list:
    """Names of the clade nodes above ``code``, broadest first."""
    if code not in memo:
        memo[code] = []  # a cycle reads the empty path
        parent = classification_parent(specs[code])
        if parent in specs:
            memo[code] = family_path(specs, parent, memo) + (
                [specs[parent]["name"]] if specs[parent].get("clade") else [])
    return memo[code]


def by_tag(specs: dict) -> dict:
    """The specs keyed by their standardized tag. When two codes standardize to
    one tag, the spec whose code already is that tag wins."""
    keyed = {}
    for code, spec in sorted(specs.items()):
        tag = standardize_lang(code)
        if tag not in keyed or code == tag:
            keyed[tag] = spec
        else:
            print(f"alias {code} dropped: standardizes to {tag}", file=sys.stderr)
    return dict(sorted(keyed.items()))


def build_genealogy(specs: dict, keyed: dict) -> dict:
    nodes, memo = {}, {}
    for tag, spec in keyed.items():
        node = {}
        parent = classification_parent(spec)
        if parent:
            node["parent"] = standardize_lang(parent)
        if spec.get("ancestors"):
            node["ancestors"] = [[standardize_lang(a["code"]), a["role"], a.get("weight", 0.0)]
                                 for a in spec["ancestors"]]
        path = family_path(specs, spec["code"], memo)
        family = spec.get("family") or " > ".join(path)
        if family:
            node["family"] = family
        if path:
            node["family_path"] = path
        if spec.get("clade"):
            node["clade"] = True
        nodes[tag] = node
    return nodes


def build_places(keyed: dict) -> dict:
    return {t: [s["location"]["latitude"], s["location"]["longitude"]]
            for t, s in keyed.items() if s.get("location")}


def build_times(keyed: dict) -> dict:
    return {t: [s["timespan"]["start_year"], s["timespan"].get("end_year")]
            for t, s in keyed.items() if s.get("timespan")}


def build_lects(keyed: dict) -> dict:
    return {t: {"name": s["name"], "regions": [], "islands": [], "cities": []}
            for t, s in keyed.items() if "-x-" in t}


def build_scripts(repo: str, ref: str) -> dict:
    """The script registry and type distances, read from the module source."""
    tree = ast.parse(git(repo, "show", f"{ref}:{SCRIPT_DISTANCE}"))
    value = lambda node: (node.attr.lower() if isinstance(node, ast.Attribute)
                          else ast.literal_eval(node))
    scripts, distances = {}, []
    for stmt in tree.body:
        target = getattr(stmt, "target", None) or (stmt.targets[0] if isinstance(stmt, ast.Assign) else None)
        if getattr(target, "id", "") == "SCRIPT_REGISTRY":
            for call in stmt.value.values:
                name, kind, direction, case, vowels, block, ancestors = map(value, call.args)
                scripts[name] = {"type": kind, "directionality": direction, "has_case": case,
                                 "vowel_marking": vowels, "unicode_block": block,
                                 "ancestor_scripts": list(ancestors)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "raw":
            distances = [[value(k.elts[0]), value(k.elts[1]), ast.literal_eval(v)]
                         for k, v in zip(node.value.keys, node.value.values)]
    print(f"{len(scripts)} scripts, {len(distances)} type distances read", file=sys.stderr)
    return {"scripts": scripts, "type_distances": distances}


def write(name: str, source: str, **fields) -> None:
    """One line for the source, one line for each entry of a table."""
    lines = []
    for key, value in fields.items():
        if isinstance(value, dict):
            entries = ",\n".join(f"{json.dumps(k, ensure_ascii=False)}: "
                                 f"{json.dumps(v, ensure_ascii=False)}" for k, v in value.items())
            lines.append(f'"{key}": {{\n{entries}\n}}')
        else:
            lines.append(f'"{key}": {json.dumps(value, ensure_ascii=False)}')
    body = ",\n".join([f'"source": {json.dumps(source)}', *lines])
    (DATA / name).write_text("{\n" + body + "\n}\n")


def main() -> None:
    repo, ref = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "origin/dev"
    source = f"TigreGotico/orthography2ipa@{git(repo, 'rev-parse', ref).decode().strip()}"
    specs = read_specs(repo, ref)
    keyed = by_tag(specs)
    nodes = build_genealogy(specs, keyed)
    places, times, lects = build_places(keyed), build_times(keyed), build_lects(keyed)
    write("genealogy.json", source, nodes=nodes)
    write("places.json", source, places=places)
    write("times.json", source, years=times)
    write("lects.json", source, lects=lects)
    write("scripts.json", source, **build_scripts(repo, ref))
    print(f"{len(specs)} specs in: {len(nodes)} genealogy nodes, {len(places)} places, "
          f"{len(times)} timespans, {len(lects)} lects out", file=sys.stderr)


if __name__ == "__main__":
    main()
