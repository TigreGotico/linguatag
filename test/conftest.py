"""Fixtures shared by the test modules."""
import builtins

import pytest

import linguatag.matching as matching
import linguatag.standardize as standardize


@pytest.fixture
def no_langcodes(monkeypatch):
    """Both standardization and distance as they run without langcodes."""
    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "langcodes" or name.startswith("langcodes."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    standardize.standardize_lang.cache_clear()
    matching._parseable_prefix.cache_clear()
    monkeypatch.setattr(builtins, "__import__", refuse)
    yield
    standardize.standardize_lang.cache_clear()
    matching._parseable_prefix.cache_clear()
