"""Write linguatag/data/lineage.json from the orthography2ipa spec files.

Each orthography2ipa spec names its ``parent``: a dialect its language, a
language its earlier stage, up to a family clade. linguatag keeps the part of
that tree a lect needs: every spec whose code has a private-use subtag, and
its ancestors up to ``DEPTH`` levels. Two lects are as near as the number of
steps between them in this tree.

The specs are read from a git ref, so no checkout is needed:

    python scripts/build_lineage.py ~/path/to/orthography2ipa origin/dev

Run it again when orthography2ipa adds, renames or re-parents a lect. With
``--check`` it writes nothing and exits 1 when the rebuild differs from the
file. The commit that ``source`` records does not count as a difference.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from linguatag.standardize import standardize_lang

OUT = Path(__file__).resolve().parent.parent / "linguatag" / "data" / "lineage.json"
DATA = "orthography2ipa/data"
#: Steps above a lect that are kept. Lect nearness is capped at 3 steps, so a
#: common ancestor further up changes no score.
DEPTH = 4


def git(repo: str, *args: str, stdin: bytes = b"") -> bytes:
    return subprocess.run(["git", "-C", repo, *args], input=stdin,
                          capture_output=True, check=True).stdout


def read_parents(repo: str, ref: str) -> dict:
    names = git(repo, "ls-tree", "-r", "--name-only", ref, DATA).decode().split()
    names = [n for n in names if n.endswith(".json")]
    blobs = git(repo, "cat-file", "--batch",
                stdin="\n".join(f"{ref}:{n}" for n in names).encode())
    parents, pos = {}, 0
    while pos < len(blobs):
        end = blobs.index(b"\n", pos)
        size = int(blobs[pos:end].split()[2])
        spec = json.loads(blobs[end + 1:end + 1 + size])
        pos = end + 1 + size + 1
        if isinstance(spec, dict) and spec.get("code"):
            parents[spec["code"]] = spec.get("parent")
    print(f"{len(names)} spec files in, {len(parents)} codes read", file=sys.stderr)
    return parents


def lineage(parents: dict) -> dict:
    kept = {}
    for code in parents:
        if "-x-" not in code:
            continue
        node = code
        for _ in range(DEPTH):
            parent = parents.get(node)
            if not parent:
                break
            kept[standardize_lang(node)] = standardize_lang(parent)
            node = parent
    return dict(sorted(kept.items()))


def differences(committed: dict, rebuilt: dict) -> list:
    """One line for each parent link that differs between two trees."""
    lines = []
    for code in sorted(committed.keys() | rebuilt.keys()):
        if code not in rebuilt:
            lines.append(f"removed {code} (parent {committed[code]})")
        elif code not in committed:
            lines.append(f"added {code} (parent {rebuilt[code]})")
        elif committed[code] != rebuilt[code]:
            lines.append(f"changed {code}: parent {committed[code]} is {rebuilt[code]}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild linguatag/data/lineage.json.")
    parser.add_argument("repo", help="a clone of orthography2ipa")
    parser.add_argument("ref", nargs="?", default="origin/dev")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 when the rebuild differs from the file")
    args = parser.parse_args()
    sha = git(args.repo, "rev-parse", args.ref).decode().strip()
    parents = lineage(read_parents(args.repo, args.ref))
    if args.check:
        committed = json.loads(OUT.read_text(encoding="utf-8"))["parents"]
        lines = differences(committed, parents)
        print(f"{len(committed)} parent links in the file, {len(parents)} in "
              f"orthography2ipa@{sha}, {len(lines)} differ", file=sys.stderr)
        if lines:
            sys.exit("\n".join(lines))
        return
    OUT.write_text(json.dumps({"source": f"TigreGotico/orthography2ipa@{sha}",
                               "parents": parents}, indent=0, ensure_ascii=False) + "\n")
    print(f"{len(parents)} parent links out", file=sys.stderr)


if __name__ == "__main__":
    main()
