"""Write the CLDR and IANA data files of linguatag/data.

Five files come out, and each names its source and version in a `source`
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
  that replaces it (RFC 5646 section 4.5). The language records are in
  `language_subtags.json`, apart from the rest, as most callers read none of
  them.
- `language_matching.json`: the `written-new` language matching data of the
  CLDR `supplemental/languageMatching.json`: the paradigm locales, the match
  variables and the `languageMatch` rules, in their order. UTS #35 section
  4.4, "Language Matching", reads them.
- `territory_containment.json`: the regions that each CLDR
  `supplemental/territoryContainment.json` region contains, without the
  `-status-` entries: the deprecated codes (`SU`, `YU`) and the grouping
  entries, which put `EU`, `EZ` and `UN` in `001`, `202` in `002`, and `003`
  and `419` in `019`. `EU`, `EZ` and `UN` stay as macroregions with their own
  members. A match variable such as `$americas` (`019`) is the set of regions
  that its macroregions contain.

Each source is a file or a URL. The defaults are the CLDR 49 release of
`cldr-json` and the IANA registry:

    python scripts/extract_cldr.py [likelySubtags.json] [aliases.json] [registry] \
        [languageMatching.json] [territoryContainment.json]

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
    languages = {"source": payload["source"], "language": payload.pop("language")}
    write("subtags.json", payload)
    write("language_subtags.json", languages)
    written = sum(len(v) for k, v in {**payload, **languages}.items() if k != "source")
    print(f"registry: {len(entries)} records in, {written} out", file=sys.stderr)


def language_matching(text: str) -> None:
    supplemental = json.loads(text)["supplemental"]
    matching = supplemental["languageMatching"]["written-new"]
    rules = [[rule["_desired"], rule["_supported"], rule["_distance"], rule.get("_oneway", False)]
             for rule in matching["languageMatch"]]
    write("language_matching.json", {
        "source": f"CLDR {cldr_version(supplemental)}, cldr-json "
                  "cldr-core/supplemental/languageMatching.json, written-new",
        "paradigm_locales": matching["paradigmLocales"]["_locales"],
        "variables": {name: variable["_value"]
                      for name, variable in matching["matchVariables"].items()},
        "rules": rules})
    print(f"languageMatch: {len(matching['languageMatch'])} in, {len(rules)} out",
          file=sys.stderr)


def territory_containment(text: str) -> None:
    supplemental = json.loads(text)["supplemental"]
    table = supplemental["territoryContainment"]
    contains = {region: entry["_contains"] for region, entry in sorted(table.items())
                if "-status-" not in region}
    write("territory_containment.json", {
        "source": f"CLDR {cldr_version(supplemental)}, cldr-json "
                  "cldr-core/supplemental/territoryContainment.json",
        "contains": contains})
    print(f"territoryContainment: {len(table)} in, {len(contains)} out "
          f"({len(table) - len(contains)} status entries left out)", file=sys.stderr)


def main() -> None:
    sources = sys.argv[1:] + [None] * (5 - len(sys.argv[1:]))
    likely_subtags(read(sources[0] or CLDR_URL.format(CLDR_JSON, "likelySubtags")))
    aliases(read(sources[1] or CLDR_URL.format(CLDR_JSON, "aliases")))
    subtags(read(sources[2] or IANA_URL))
    language_matching(read(sources[3] or CLDR_URL.format(CLDR_JSON, "languageMatching")))
    territory_containment(read(sources[4] or CLDR_URL.format(CLDR_JSON, "territoryContainment")))


if __name__ == "__main__":
    main()
