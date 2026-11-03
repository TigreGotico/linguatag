"""BCP-47 language tags: standardization, distance, closest match, and the
default region of a tag that names none."""
from linguatag.matching import (DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang,
                                lang_distance, lang_matches)
from linguatag.regions import OVERRIDES, default_region, with_default_region
from linguatag.standardize import standardize_lang

__all__ = [
    "DEFAULT_MAX_LANGUAGE_DISTANCE",
    "OVERRIDES",
    "closest_lang",
    "default_region",
    "lang_distance",
    "lang_matches",
    "standardize_lang",
    "with_default_region",
]
