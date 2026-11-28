"""BCP-47 language tags: standardization, distance, closest match, the default
region of a tag that names none, the nearness of dialects named with a
private-use subtag, and the genealogy, place and period of a language."""
from linguatag._bcp47 import LanguageTag, LanguageTagError, language_scope, maximize
from linguatag._bcp47 import parse as parse_tag
from linguatag._lects import LECT_MODES, lect_steps, lookup_tags
from linguatag._lineage import (ancestors, ancestry_similarity, catalog_ids, family, family_path,
                               geographic_distance, parent, temporal_distance)
from linguatag._matching import (DEFAULT_MAX_LANGUAGE_DISTANCE, closest_lang,
                                is_arabic_variety, lang_distance, lang_matches)
from linguatag._regions import OVERRIDES, default_region, likely_script, with_default_region
from linguatag._standardize import standard_tag, standardize_lang
from linguatag._writing_systems import script_distance, script_distance_by_name, script_features

__all__ = [
    "DEFAULT_MAX_LANGUAGE_DISTANCE",
    "LECT_MODES",
    "LanguageTag",
    "LanguageTagError",
    "OVERRIDES",
    "ancestors",
    "catalog_ids",
    "ancestry_similarity",
    "closest_lang",
    "default_region",
    "family",
    "family_path",
    "geographic_distance",
    "is_arabic_variety",
    "lang_distance",
    "lang_matches",
    "language_scope",
    "lect_steps",
    "lookup_tags",
    "likely_script",
    "maximize",
    "parent",
    "parse_tag",
    "script_distance",
    "script_distance_by_name",
    "script_features",
    "standard_tag",
    "standardize_lang",
    "temporal_distance",
    "with_default_region",
]
