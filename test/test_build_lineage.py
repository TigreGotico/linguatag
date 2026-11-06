"""`scripts/build_lineage.py --check`, against a small orthography2ipa clone."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_lineage.py"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _commit_specs(repo, specs):
    data = repo / "orthography2ipa" / "data"
    data.mkdir(parents=True, exist_ok=True)
    for path in data.iterdir():
        path.unlink()
    for code, parent in specs.items():
        (data / f"{code}.json").write_text(json.dumps({"code": code, "parent": parent}))
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "specs",
         "--allow-empty")


@pytest.fixture
def build(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("build_lineage", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "OUT", tmp_path / "lineage.json")
    return module


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / "o2i"
    repo.mkdir()
    _git(repo, "init", "-q")
    _commit_specs(repo, {"an": None, "an-x-cheso": "an", "an-x-ansotano": "an"})
    return repo


def _run(build, monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["build_lineage.py", *args])
    build.main()


def test_the_check_passes_on_a_fresh_rebuild(build, repo, monkeypatch):
    _run(build, monkeypatch, str(repo), "HEAD")
    written = build.OUT.read_text()
    _run(build, monkeypatch, str(repo), "HEAD", "--check")
    assert build.OUT.read_text() == written
    assert json.loads(written)["parents"] == {"an-x-ansotano": "an", "an-x-cheso": "an"}


def test_a_new_commit_alone_is_no_difference(build, repo, monkeypatch):
    _run(build, monkeypatch, str(repo), "HEAD")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x", "--allow-empty")
    _run(build, monkeypatch, str(repo), "HEAD", "--check")


@pytest.mark.parametrize("specs, line", [
    ({"an": None, "an-x-cheso": "an", "an-x-ansotano": "an", "an-x-benasque": "an"},
     "added an-x-benasque (parent an)"),
    ({"an": None, "an-x-cheso": "an"}, "removed an-x-ansotano (parent an)"),
    ({"an": None, "an-x-cheso": "an-x-ansotano", "an-x-ansotano": "an"},
     "changed an-x-cheso: parent an is an-x-ansotano"),
])
def test_the_check_fails_on_every_kind_of_drift(build, repo, monkeypatch, specs, line):
    _run(build, monkeypatch, str(repo), "HEAD")
    written = build.OUT.read_text()
    _commit_specs(repo, specs)
    with pytest.raises(SystemExit) as failure:
        _run(build, monkeypatch, str(repo), "HEAD", "--check")
    assert failure.value.code == line
    assert build.OUT.read_text() == written
