"""Deprecated alias of ``linguatag._bcp47`` for releases that imported it.
Use the top-level names: ``parse_tag``, ``LanguageTag``, ``LanguageTagError``."""
import warnings

from linguatag import _bcp47

warnings.warn("linguatag.bcp47 is internal; import from linguatag (parse_tag, LanguageTag, "
              "LanguageTagError)", DeprecationWarning, stacklevel=2)


def __getattr__(name):
    return getattr(_bcp47, name)
