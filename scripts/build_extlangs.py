"""Write linguatag/data/extlangs.json from the IANA Language Subtag Registry.

An extlang tag such as `zh-hak` names the language of its extlang subtag,
Hakka here, and RFC 5646 section 4.5 canonicalizes it to that subtag's
Preferred-Value: `zh-hak-TW` is `hak-TW`. The table maps every registered
`Prefix-Subtag` pair of type extlang to its Preferred-Value.

The registry is read from a file or a URL, the IANA one by default:

    python scripts/build_extlangs.py [registry]

Run it again when IANA registers a new extlang.
"""
import json
import sys
from pathlib import Path
from urllib.request import urlopen

OUT = Path(__file__).resolve().parent.parent / "linguatag" / "data" / "extlangs.json"
IANA = "https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry"


def read_registry(source: str) -> str:
    if "://" in source:
        with urlopen(source) as response:
            return response.read().decode("utf-8")
    return Path(source).read_text(encoding="utf-8")


def records(text: str) -> list:
    """Each record as a field -> values dict. A line that starts with a space
    continues the field above it."""
    out = []
    for block in text.split("\n%%\n"):
        fields, name = {}, None
        for line in block.splitlines():
            if line.startswith(" ") and name:
                fields[name][-1] += " " + line.strip()
            elif ":" in line:
                name, value = line.split(":", 1)
                fields.setdefault(name, []).append(value.strip())
        out.append(fields)
    return out


def main() -> None:
    text = read_registry(sys.argv[1] if len(sys.argv) > 1 else IANA)
    file_date = text.splitlines()[0].split(":", 1)[1].strip()
    extlangs = [r for r in records(text) if r.get("Type") == ["extlang"]]
    preferred = {}
    for record in extlangs:
        (subtag,), (prefix,), (value,) = (record["Subtag"], record["Prefix"],
                                          record["Preferred-Value"])
        preferred[f"{prefix}-{subtag}".lower()] = value.lower()
    payload = {"source": f"IANA Language Subtag Registry, File-Date: {file_date}",
               "preferred": dict(sorted(preferred.items()))}
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(extlangs)} extlang records in, {len(preferred)} mappings out",
          file=sys.stderr)


if __name__ == "__main__":
    main()
