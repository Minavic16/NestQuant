from nestquant_studio.core.search_space import SearchSpace, candidate_key


def test_keys_stable_and_unique():
    sp = SearchSpace(
        {
            "axes": {
                "asset": {"type": "enum", "values": ["A", "B"]},
                "lookback": {"type": "int_range", "min": 10, "max": 20, "step": 5},
            }
        }
    )
    rows = sp.materialize()
    assert len(rows) == 6
    keys = [k for k, _ in rows]
    assert len(set(keys)) == 6
    assert keys == [k for k, _ in sp.materialize()]


def test_exclude_and_canonical_key():
    sp = SearchSpace(
        {
            "axes": {
                "asset": {"type": "enum", "values": ["A", "B"]},
                "tf": {"type": "enum", "values": ["1h"]},
            },
            "exclude": [{"asset": "B", "tf": "1h"}],
        }
    )
    rows = sp.materialize()
    assert len(rows) == 1
    assert rows[0][1]["asset"] == "A"
    assert candidate_key({"b": 1, "a": 2}) == candidate_key({"a": 2, "b": 1})