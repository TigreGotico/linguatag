import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import add_nodes  # noqa: E402


@pytest.fixture
def data(tmp_path, monkeypatch):
    for name in add_nodes.TABLES:
        shutil.copy(add_nodes.DATA / name, tmp_path / name)
    monkeypatch.setattr(add_nodes, "DATA", tmp_path)
    return tmp_path


def run(tmp_path, monkeypatch, facts, *flags):
    path = tmp_path / "nodes.json"
    path.write_text(json.dumps(facts), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["add_nodes.py", str(path), *flags])
    add_nodes.main()


def read(data, name):
    return json.loads((data / name).read_text(encoding="utf-8"))


def test_a_new_lect_and_its_new_child(data, monkeypatch, capsys):
    run(data, monkeypatch, {
        "pt-PT-x-zchild": {"parent": "pt-PT-x-znew", "glottolog_code": None},
        "pt-PT-x-znew": {"parent": "pt-PT", "wikidata_qid": "Q5146", "place": [38.7, -9.1], "years": [1500, None]},
    })
    nodes = read(data, "genealogy.json")["nodes"]
    assert nodes["pt-PT-x-znew"] == {"parent": "pt-PT", "family": "Indo-European > Italic > Romance > Ibero-Romance",
                                     "family_path": ["Indo-European", "Italic", "Romance", "Ibero-Romance"],
                                     "wikidata_qid": "Q5146"}
    assert nodes["pt-PT-x-zchild"]["glottolog_code"] is None
    assert nodes["pt-PT-x-zchild"]["family_path"] == nodes["pt-PT-x-znew"]["family_path"]
    assert read(data, "places.json")["places"]["pt-PT-x-znew"] == [38.7, -9.1]
    assert read(data, "times.json")["years"]["pt-PT-x-znew"] == [1500, None]
    assert capsys.readouterr().out == "2 nodes in, 2 added, 0 updated\n"


def test_other_nodes_keep_their_bytes(data, monkeypatch):
    before = (data / "genealogy.json").read_text(encoding="utf-8").splitlines()
    run(data, monkeypatch, {"pt-PT-x-znew": {"parent": "pt-PT"}})
    after = (data / "genealogy.json").read_text(encoding="utf-8").splitlines()
    assert sorted(set(after) - set(before)) == [l for l in after if l.startswith('"pt-PT-x-znew"')]
    assert set(before) <= set(after)


@pytest.mark.parametrize("facts, message", [
    ({"pt-PT-x-znew": {"parent": "qqq"}}, "parent 'qqq' is not in the genealogy"),
    ({"PT-pt-x-znew": {"parent": "pt-PT"}}, "is not a standard tag"),
    ({"pt-PT-x-znew": {"parent": "pt-PT", "glottolog_code": "port"}}, "is not a glottocode"),
    ({"pt-PT-x-znew": {"parent": "pt-PT", "wikidata_qid": "5146"}}, "is not a Wikidata QID"),
    ({"pt-PT-x-za": {"parent": "pt-PT-x-zb"}, "pt-PT-x-zb": {"parent": "pt-PT-x-za"}}, "makes a cycle"),
    ({"pt-PT-x-znew": {"parent": "pt-PT", "regions": []}}, "unknown fields"),
])
def test_a_bad_node_is_refused(data, monkeypatch, facts, message):
    with pytest.raises(ValueError, match=message):
        run(data, monkeypatch, facts)


def test_a_known_tag_needs_update(data, monkeypatch):
    with pytest.raises(SystemExit, match="pass --update"):
        run(data, monkeypatch, {"pt-BR": {"parent": "pt-PT-x-medieval"}})


def test_an_update_keeps_the_weighted_ancestors(data, monkeypatch):
    before = read(data, "genealogy.json")["nodes"]["pt-BR"]
    run(data, monkeypatch, {"pt-BR": {"parent": "pt-PT-x-medieval", "wikidata_qid": "Q750553",
                                      "glottolog_code": "braz1246"}}, "--update")
    assert read(data, "genealogy.json")["nodes"]["pt-BR"] == before


def test_an_update_changes_only_the_keys_it_gives(data, monkeypatch):
    before = read(data, "genealogy.json")["nodes"]["chm"]
    run(data, monkeypatch, {"chm": {"parent": before["parent"], "wikidata_qid": "Q1"}}, "--update")
    assert read(data, "genealogy.json")["nodes"]["chm"] == {**before, "wikidata_qid": "Q1"}


def test_an_update_to_a_new_parent_drops_the_ancestors(data, monkeypatch):
    before = read(data, "genealogy.json")["nodes"]["pt-BR"]
    run(data, monkeypatch, {"pt-BR": {"parent": "pt-PT"}}, "--update")
    after = read(data, "genealogy.json")["nodes"]["pt-BR"]
    assert "ancestors" not in after and after["parent"] == "pt-PT"
    assert after["glottolog_code"] == before["glottolog_code"] == "braz1246"


def test_a_null_parent_makes_a_root(data, monkeypatch):
    run(data, monkeypatch, {
        "x-clade-zzzz0001": {"parent": None, "glottolog_code": "zzzz0001"},
        "qaa": {"parent": "x-clade-zzzz0001", "glottolog_code": None},
        "qab": {"parent": None, "family_path": ["Isolate"], "glottolog_code": "zzzz0002"},
    })
    nodes = json.loads((data / "genealogy.json").read_text())["nodes"]
    assert nodes["x-clade-zzzz0001"] == {"clade": True, "glottolog_code": "zzzz0001"}
    assert nodes["qaa"]["parent"] == "x-clade-zzzz0001" and nodes["qaa"]["glottolog_code"] is None
    assert nodes["qab"] == {"family": "Isolate", "family_path": ["Isolate"], "glottolog_code": "zzzz0002"}


def test_a_move_gives_the_new_family_to_the_descendants(data, monkeypatch):
    germanic = ["Indo-European", "Germanic", "Northwest Germanic", "West Germanic"]
    run(data, monkeypatch, {"pt-BR": {"parent": "af"},
                            "pt-BR-x-zown": {"parent": "pt-BR-x-sp", "family_path": ["Isolate"]}}, "--update")
    nodes = read(data, "genealogy.json")["nodes"]
    for tag in ("pt-BR", "pt-BR-x-sp", "pt-UY"):
        assert nodes[tag]["family_path"] == germanic
        assert nodes[tag]["family"] == "Indo-European > Germanic > Northwest Germanic > West Germanic"
    assert nodes["pt-BR-x-zown"]["family_path"] == ["Isolate"]


def test_a_move_to_the_root_removes_the_family(data, monkeypatch):
    run(data, monkeypatch, {"pt-BR": {"parent": None}}, "--update")
    nodes = read(data, "genealogy.json")["nodes"]
    assert nodes["pt-BR"] == {"glottolog_code": "braz1246", "wikidata_qid": "Q750553"}


def test_a_moved_clade_keeps_its_name_in_the_descendants(data, monkeypatch):
    # x-clade-alba1267 is ["Indo-European"]; its children are ["Indo-European", "Albanian"].
    run(data, monkeypatch, {"x-clade-alba1267": {"parent": "gem"}}, "--update")
    nodes = read(data, "genealogy.json")["nodes"]
    assert nodes["x-clade-alba1267"]["family_path"] == ["Indo-European", "Germanic"]
    assert nodes["aae"]["family_path"] == ["Indo-European", "Germanic", "Albanian"]
    assert nodes["aae"]["family"] == "Indo-European > Germanic > Albanian"
