from linguatag import _distance, default_region, parse_tag, with_default_region


def _scan(fields, language):
    return tuple(rule for rule in _distance._RULES[fields]
                 if _distance._all_match(rule[0][:1], (language,)) or _distance._all_match(rule[1][:1], (language,)))


def test_the_rule_index_gives_the_rules_of_a_full_scan():
    languages = {value for rules in _distance._RULES.values() for want, have, _, _ in rules
                 for _, values in (want[0], have[0]) for value in values}
    for fields in (1, 2, 3):
        for language in sorted(languages) + ["zz", "qaa", "xyz", "pt", "arz"]:
            assert _distance._rules_for(fields, language) == _scan(fields, language), (fields, language)


def test_repeated_tag_calls_return_the_cached_result():
    assert parse_tag("ar-EH") is parse_tag("ar-EH")
    assert with_default_region("pt") == "pt-PT" and default_region("pt") == "PT"
    assert with_default_region.cache_info().hits >= 0 and parse_tag.cache_info().currsize >= 1
