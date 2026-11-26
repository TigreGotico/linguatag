import importlib
import sys

import pytest

import linguatag


def test_bcp47_alias_warns_and_forwards():
    sys.modules.pop("linguatag.bcp47", None)
    with pytest.warns(DeprecationWarning, match="linguatag.bcp47 is internal"):
        bcp47 = importlib.import_module("linguatag.bcp47")
    assert bcp47.parse("pt-PT").region == "PT"
    assert bcp47.LanguageTagError is linguatag.LanguageTagError
