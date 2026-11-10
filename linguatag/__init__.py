"""BCP-47 language tags: standardization, distance, closest match, and the
default region of a tag that names none, and the nearness of dialects
named with a private-use subtag."""
from linguatag.lects import LECT_MODES, lect_steps
from linguatag.matching import (DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang,
                                is_arabic_variety, lang_distance, lang_matches)
from linguatag.regions import OVERRIDES, default_region, with_default_region
from linguatag.standardize import standardize_lang

__all__ = [
    "DEFAULT_MAX_LANGUAGE_DISTANCE",
    "LECT_MODES",
    "OVERRIDES",
    "closest_lang",
    "default_region",
    "is_arabic_variety",
    "lang_distance",
    "lang_matches",
    "lect_steps",
    "standardize_lang",
    "with_default_region",
]
