"""The cost of a first call: a tag with no alias builds no alias table and
reads no language record, and a tag that has an alias still gets its
replacement."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import linguatag
from linguatag import _bcp47 as bcp47

DATA = Path(linguatag.__file__).parent / "data"


def _after(call: str) -> dict:
    """What a fresh interpreter has done after ``call``: the files it read
    and the alias tables it built."""
    tree = str(DATA.parent.parent)
    code = (
        "import json, pathlib, linguatag, linguatag._bcp47 as b\n"
        f"assert linguatag.__file__.startswith({tree!r}), linguatag.__file__\n"
        "read = []\n"
        "read_text = pathlib.Path.read_text\n"
        "pathlib.Path.read_text = lambda self, *a, **k: read.append(self.name) or read_text(self, *a, **k)\n"
        f"{call}\n"
        "print(json.dumps({'read': read, 'tables': b._alias_table.cache_info().currsize"
        " + b._rules.cache_info().currsize}))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, cwd="/", env={"PYTHONPATH": tree})
    return json.loads(out.stdout)


@pytest.mark.parametrize("tag", ["en", "pt-PT", "de", "fr-CA", "uk", "pt-BR-x-minhoto"])
def test_a_tag_with_no_alias_builds_no_table(tag):
    state = _after(f"assert linguatag.standardize_lang({tag!r}) == {tag!r}")
    assert state["tables"] == 0
    assert "language_subtags.json" not in state["read"]


@pytest.mark.parametrize("call", ["default_region('pt') == 'PT'", "with_default_region('fr-CA') == 'fr-CA'",
                                  "likely_script('pt') == 'Latn'"])
def test_a_bare_or_regional_tag_builds_no_table(call):
    state = _after(f"assert linguatag.{call}")
    assert state["tables"] == 0
    assert "language_subtags.json" not in state["read"]


@pytest.mark.parametrize("tag, expected", [("iw", "he"), ("eng", "en"), ("sh", "sr-Latn"),
                                           ("en-GB-oed", "en-GB-oxendict"), ("zh-min-nan", "nan"),
                                           ("de-DD", "de-DE"), ("en-polytoni", "en-polyton")])
def test_a_tag_with_an_alias_builds_the_table(tag, expected):
    state = _after(f"assert linguatag.standardize_lang({tag!r}) == {expected!r}")
    assert state["tables"] > 0


def test_a_legacy_whole_tag_is_not_canonical_without_rules(monkeypatch):
    """A tag that a legacy replacement matches whole takes the table path,
    though no rule key names any of its subtags."""
    tag = bcp47.parse("xx-YY")
    monkeypatch.setattr(bcp47, "_alias_keys", lambda: (frozenset(), frozenset({"xx-yy"})))
    assert not bcp47._has_no_alias(tag)
    monkeypatch.setattr(bcp47, "_alias_keys", lambda: (frozenset(), frozenset()))
    assert bcp47._has_no_alias(tag)


def test_every_deprecated_subtag_is_a_cldr_alias_type():
    """The fast path takes its keys from the CLDR alias types alone."""
    aliases = json.loads((DATA / "aliases.json").read_text(encoding="utf-8"))
    registry = json.loads((DATA / "subtags.json").read_text(encoding="utf-8"))
    registry.update(json.loads((DATA / "language_subtags.json").read_text(encoding="utf-8")))
    for kind in ("language", "script", "region", "variant"):
        missing = [subtag for subtag, record in registry[kind].items()
                   if "preferred" in record and ".." not in subtag and subtag not in aliases[kind]]
        assert missing == [], kind


def test_the_compiled_alias_rules_are_fresh():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build", DATA.parent.parent / "scripts" / "build_alias_rules.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert json.loads((DATA / "alias_rules.json").read_text()) == build.compiled()
