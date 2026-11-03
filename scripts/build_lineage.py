"""Write linguatag/data/lineage.json from the orthography2ipa spec files.

Each orthography2ipa spec names its ``parent``: a dialect its language, a
language its earlier stage, up to a family clade. linguatag keeps the part of
that tree a lect needs: every spec whose code has a private-use subtag, and
its ancestors up to ``DEPTH`` levels. Two lects are as near as the number of
steps between them in this tree.

The specs are read from a git ref, so no checkout is needed:

    python scripts/build_lineage.py ~/path/to/orthography2ipa origin/dev

Run it again when orthography2ipa adds, renames or re-parents a lect.
"""
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


def main() -> None:
    repo, ref = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "origin/dev"
    sha = git(repo, "rev-parse", ref).decode().strip()
    parents = lineage(read_parents(repo, ref))
    OUT.write_text(json.dumps({"source": f"TigreGotico/orthography2ipa@{sha}",
                               "parents": parents}, indent=0, ensure_ascii=False) + "\n")
    print(f"{len(parents)} parent links out", file=sys.stderr)


if __name__ == "__main__":
    main()
