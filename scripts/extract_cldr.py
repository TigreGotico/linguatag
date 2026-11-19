"""Write the CLDR and IANA data files of linguatag/data.

Three files come out, and each names its source and version in a `source`
field:

- `likely_subtags.json`: the CLDR `supplemental/likelySubtags.json` table,
  as it is. UTS #35 section 4.3, "Add Likely Subtags", reads it.
- `aliases.json`: the `languageAlias`, `scriptAlias`, `territoryAlias` and
  `variantAlias` entries of the CLDR `supplemental/aliases.json`, each with
  its replacement and its reason. UTS #35 Annex C, "LocaleId
  Canonicalization", reads them.
- `subtags.json`: the IANA Language Subtag Registry. Each record of type
  language, extlang, script, region or variant gives its subtag; each
  grandfathered or redundant record gives its tag. A record keeps the fields
  that canonicalization reads: `Deprecated`, `Preferred-Value`, `Prefix`,
  `Suppress-Script` and `Macrolanguage`. A subtag that is in the file is
  valid; a subtag with `deprecated` is deprecated; `preferred` is the value
  that replaces it (RFC 5646 section 4.5).

Each source is a file or a URL. The defaults are the CLDR 49 release of
`cldr-json` and the IANA registry:

    python scripts/extract_cldr.py [likelySubtags.json] [aliases.json] [registry]

Run it again after a CLDR release or an IANA registry change. It prints the
number of entries in and out for each file.
"""
import json
import sys
from pathlib import Path
from urllib.request import urlopen

DATA = Path(__file__).resolve().parent.parent / "linguatag" / "data"
CLDR_JSON = "49.0.0"
CLDR_URL = ("https://raw.githubusercontent.com/unicode-org/cldr-json/{}"
            "/cldr-json/cldr-core/supplemental/{}.json")
IANA_URL = "https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry"
ALIAS_KINDS = {"languageAlias": "language", "scriptAlias": "script",
               "territoryAlias": "region", "variantAlias": "variant"}
REGISTRY_FIELDS = {"Deprecated": "deprecated", "Preferred-Value": "preferred",
                   "Prefix": "prefix", "Suppress-Script": "suppress_script",
                   "Macrolanguage": "macrolanguage"}


def read(source: str) -> str:
    if "://" in source:
        with urlopen(source) as response:
            return response.read().decode("utf-8")
    return Path(source).read_text(encoding="utf-8")


def write(name: str, payload: dict) -> None:
    (DATA / name).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")


def cldr_version(supplemental: dict) -> str:
    return supplemental["version"]["_cldrVersion"]


def likely_subtags(text: str) -> None:
    supplemental = json.loads(text)["supplemental"]
    table = supplemental["likelySubtags"]
    write("likely_subtags.json", {
        "source": f"CLDR {cldr_version(supplemental)}, cldr-json "
                  "cldr-core/supplemental/likelySubtags.json",
        "likely": dict(sorted(table.items()))})
    print(f"likelySubtags: {len(table)} in, {len(table)} out", file=sys.stderr)


def aliases(text: str) -> None:
    supplemental = json.loads(text)["supplemental"]
    alias = supplemental["metadata"]["alias"]
    payload = {"source": f"CLDR {cldr_version(supplemental)}, cldr-json "
                         "cldr-core/supplemental/aliases.json"}
    for cldr_name, name in ALIAS_KINDS.items():
        entries = alias[cldr_name]
        payload[name] = {type_: [entry["_replacement"], entry["_reason"]]
                         for type_, entry in sorted(entries.items())}
        print(f"{cldr_name}: {len(entries)} in, {len(payload[name])} out", file=sys.stderr)
    write("aliases.json", payload)


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


def subtags(text: str) -> None:
    file_date = text.splitlines()[0].split(":", 1)[1].strip()
    entries = [r for r in records(text) if "Type" in r]
    payload = {"source": f"IANA Language Subtag Registry, File-Date: {file_date}"}
    for record in entries:
        (kind,) = record["Type"]
        key = record["Subtag"][0] if "Subtag" in record else record["Tag"][0]
        fields = {}
        for field, name in REGISTRY_FIELDS.items():
            if field in record:
                fields[name] = record[field] if field == "Prefix" else record[field][0]
        payload.setdefault(kind, {})[key] = fields
    for kind in list(payload)[1:]:
        payload[kind] = dict(sorted(payload[kind].items()))
    write("subtags.json", payload)
    print(f"registry: {len(entries)} records in, "
          f"{sum(len(v) for k, v in payload.items() if k != 'source')} out", file=sys.stderr)


def main() -> None:
    sources = sys.argv[1:] + [None] * (3 - len(sys.argv[1:]))
    likely_subtags(read(sources[0] or CLDR_URL.format(CLDR_JSON, "likelySubtags")))
    aliases(read(sources[1] or CLDR_URL.format(CLDR_JSON, "aliases")))
    subtags(read(sources[2] or IANA_URL))


if __name__ == "__main__":
    main()
