"""`langcodes` is a plain dependency, so every install measures the same."""
import subprocess
import sys
from importlib.metadata import metadata, requires

import pytest
from langcodes import tag_distance

from linguatag import DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang, lang_distance

ONE_ANSWER_PAIRS = [("iw", "he"), ("por", "pt"), ("eng", "en"), ("cmn", "zh"),
                    ("nb", "no"), ("zh-TW", "zh-CN"), ("zh-Hans", "zh-Hant")]


@pytest.mark.parametrize("a, b", ONE_ANSWER_PAIRS)
def test_distance_is_the_langcodes_distance(a, b):
    assert lang_distance(a, b) == tag_distance(a, b)
    assert lang_distance(b, a) == tag_distance(b, a)


@pytest.mark.parametrize("request_tag, offered", [("zh-TW", "zh-CN"), ("zh-Hant", "zh-Hans")])
def test_traditional_chinese_never_accepts_simplified(request_tag, offered):
    assert tag_distance(request_tag, offered) > DEFAULT_MAX_LANGUAGE_DISTANCE
    assert closest_lang(request_tag, [offered]) is None


@pytest.mark.parametrize("available", [["pt-BR", "pt-PT"], ["pt-PT", "pt-BR"]])
def test_a_regional_cluster_decides_whatever_the_order(available):
    expected = min(available, key=lambda tag: tag_distance("pt-AO", tag))
    assert closest_lang("pt-AO", available) == expected


def test_a_plain_install_requires_langcodes():
    plain = [line for line in requires("linguatag") if "extra ==" not in line]
    assert [line.split(">=")[0] for line in plain] == ["langcodes"]


def test_the_langcodes_extra_stays_valid_and_adds_nothing():
    assert "langcodes" in metadata("linguatag").get_all("Provides-Extra")
    assert [line for line in requires("linguatag") if 'extra == "langcodes"' in line] == []


def test_without_langcodes_the_import_fails():
    """A missing dependency is an error, never a second meaning of the API."""
    code = "import sys; sys.modules['langcodes'] = None; import linguatag"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 1
    assert "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr
