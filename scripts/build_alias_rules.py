"""Write ``linguatag/data/alias_rules.json``: the compiled UTS #35 alias rules
and the legacy whole-tag replacements, with and without the macrolanguage
rules. Run it after ``extract_cldr.py`` changes ``aliases.json`` or
``subtags.json``; a test checks that the file is fresh."""
import json
from pathlib import Path

from linguatag import _bcp47

OUT = Path(_bcp47.__file__).parent / "data" / "alias_rules.json"


def compiled() -> dict:
    parts = {name: {"rules": [_bcp47._rule_row(rule) for rule in _bcp47._build_rules(macro)],
                   "legacy": _bcp47._alias_table(macro)[1]}
            for name, macro in (("standard", False), ("macrolanguage", True))}
    return {"source": "scripts/build_alias_rules.py, from aliases.json, subtags.json and language_subtags.json", **parts}


if __name__ == "__main__":
    OUT.write_text(json.dumps(compiled(), ensure_ascii=False, separators=(",", ":")) + "\n")
    print(OUT, {name: len(part["rules"]) for name, part in compiled().items() if name != "source"})
