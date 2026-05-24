import pytest

import pandas as pd

from core import collections
from core.collections import (
    build_filter,
    compare_collections,
    find_by_inner_keys,
    find_by_inner_key,
    RecursionCache,
    recurse_collections,
    BijectiveMap,
)


def test_default_tree():
    tree = collections.default_tree()
    tree["a"]["b"]["c"] = 1

    assert tree["a"]["b"]["c"] == 1


def test_filter():
    assert build_filter(lambda x: x == "a")("a")
    assert not build_filter(lambda x: x == "a")("b")

    assert build_filter({"a", "b"})("a")
    assert not build_filter({"a", "b"})("c")

    assert build_filter("^a")("aa")
    assert not build_filter("^a")("ba")

    assert not build_filter("^(?!aa)")("aab")
    assert build_filter("^(?!aa)")("aba")

    assert build_filter(None, if_none=True)("a")
    assert not build_filter(None, if_none=False)("a")


def test_compare_collections():
    assert compare_collections([1, 2, 3], [2, 3, 4]) == ([1], [2, 3], [4])

    a = {"a": 1, "b": 2, "c": 3}
    b = {"b": 2, "c": -3, "d": 4}
    r = ({"a": 1, "c": 3}, {"b": 2}, {"d": 4, "c": -3})
    assert compare_collections(a, b) == r

    a = {"a": {"aa": 2}, "b": {"ba": 3, "bb": 4}, "c": [4, 6]}
    b = {"b": {"ba": -3, "bb": 4}, "c": [5, 4, 3], "d": [1, 2]}
    r = (
        {"a": {"aa": 2}, "b": {"ba": 3}, "c": [6]},
        {"b": {"bb": 4}, "c": [4]},
        {"b": {"ba": -3}, "c": [3, 5], "d": [1, 2]},
    )
    assert compare_collections(a, b) == r


def test_find_by_inner_key():
    x = {"a": {"a1": {"x": 1, "y": 2}}, "b": {"b1": {"x": 3, "y": 4}}, "c": {"c1": 5}}
    assert find_by_inner_key(x, "x") == {"a": {"a1": 1}, "b": {"b1": 3}}


def test_find_by_inner_keys():
    x = {"a": {"a1": {"x": 1, "y": 2, "z": 6}}, "b": {"b1": {"x": 3, "y": 4}}, "c": {"c1": 5}}
    assert find_by_inner_keys(x, {"x", "z"}) == {
        "a": {"a1": {"x": 1, "z": 6}},
        "b": {"b1": {"x": 3}},
    }


def test_recursive_cache():
    one_list = [1, 3, 4, 5]
    one_map = {"a": 1, "b": 2, "c": 3}

    some_structure = {"x": one_list, "y": one_map, "z": [one_list, one_map, {"0": one_map}]}

    cache = RecursionCache()
    visited = []

    def map_(x):
        visited.append(x)
        return x

    recurse_collections(some_structure, map_=map_, cache=cache)
    assert visited == [1, 3, 4, 5, 1, 2, 3]


def test_recursive_map():
    coll = {
        "RATES_CLP": {"start": "22:01", "end": "21:59", "tz": "America/New_York"},
        "RATES_COP": {"start": "22:01", "end": "21:59", "tz": "America/New_York"},
        "RATES_CNY": {
            "disjoint_union": {
                "session_1": {"start": "02:00", "end": "03:59", "tz": "Europe/London"},
                "session_2": {"start": "05:00", "end": "08:59", "tz": "Europe/London"},
            },
        },
    }
    coll_expected = {
        "RATES_CLP": {"start": "altered", "end": "21:59", "tz": "America/New_York"},
        "RATES_COP": {"start": "altered", "end": "21:59", "tz": "America/New_York"},
        "RATES_CNY": {
            "disjoint_union": {
                "session_1": {"start": "altered", "end": "03:59", "tz": "Europe/London"},
                "session_2": {"start": "altered", "end": "08:59", "tz": "Europe/London"},
            },
        },
    }

    def map_(key, value):
        return "altered" if key == "start" else value

    coll_recursed = recurse_collections(coll, kv_map=map_)
    assert coll_recursed == coll_expected


def test_biject_map_initialization():
    bmap = BijectiveMap(a=1, b=2)
    assert bmap["a"] == 1
    assert bmap["b"] == 2
    assert bmap.inverse(1) == "a"
    assert bmap.inverse(2) == "b"


def test_biject_map_set_item():
    bmap = BijectiveMap()
    bmap["x"] = 42
    assert bmap["x"] == 42
    assert bmap.inverse(42) == "x"


def test_biject_map_overwrite_value_for_same_key():
    bmap = BijectiveMap(a=1, b=2)
    bmap["a"] = 99

    assert "a" in bmap
    assert bmap["a"] == 99
    with pytest.raises(KeyError):
        _ = bmap.inverse(1)
    assert bmap.inverse(99) == "a"


def test_biject_map_error_on_duplicate_value():
    bmap = BijectiveMap(a=1, b=2)
    with pytest.raises(ValueError) as exc_info:
        bmap["c"] = 2
    assert "Value '2' is already mapped by key 'b'" in str(exc_info.value)


def test_biject_map_delete_item():
    bmap = BijectiveMap(x=10, y=20)
    del bmap["x"]
    assert "x" not in bmap
    with pytest.raises(KeyError):
        _ = bmap.inverse(10)


def test_biject_map_update():
    bmap = BijectiveMap()
    bmap.update({"m": 100, "n": 200})
    assert bmap["m"] == 100
    assert bmap["n"] == 200
    assert bmap.inverse(100) == "m"
    assert bmap.inverse(200) == "n"

    with pytest.raises(ValueError):
        bmap.update({"o": 200})


def test_biject_map_clear():
    bmap = BijectiveMap(a=1, b=2, c=3)
    bmap.clear()

    assert len(bmap) == 0
    with pytest.raises(KeyError):
        _ = bmap.inverse(1)


def test_biject_map_inverse_lookup():
    bmap = BijectiveMap({"fox": "orange", "sky": "blue"})
    assert bmap.inverse("blue") == "sky"
    assert bmap.inverse("orange") == "fox"
    with pytest.raises(KeyError):
        _ = bmap.inverse("red")


def test_biject_map_inverse_duplicate():
    with pytest.raises(ValueError) as exc_info:
        BijectiveMap(a=1, b=1)
    assert "Value '1' is already mapped by key 'a'" in str(exc_info.value)


def test_recurse_collections_filter_on_value_only():
    data = {
        "a": 1,
        "b": 2,
        "c": {"d": 3, "e": 4},
        "f": [5, 6, 7],
    }

    def filter_value_only(value):
        return value >= 4

    def map_values(value):
        return value * 10

    result = recurse_collections(data, filter_=filter_value_only, map_=map_values)
    expected = {
        "c": {"e": 40},
        "f": [50, 60, 70],
    }
    assert result == expected


def test_recurse_collections_map_on_key_and_value():
    """Test filtering based on both key and value."""
    data = {
        "a": 1,
        "b": 2,
        "c": {"d": 3, "e": 4},
        "f": [5, 6, 7],
    }

    def filter_key_and_value(value):
        return value >= 4

    def map_values(key, value):
        return value * 10 if key == "e" else value

    result = recurse_collections(data, filter_=filter_key_and_value, kv_map=map_values)
    expected = {
        "c": {"e": 40},
        "f": [5, 6, 7],
    }
    assert result == expected


def test_compare_columns():
    a, _, _ = compare_collections(
        pd.DataFrame({"a": [1, 2, 3], "b": [1, 2, 3]}), pd.DataFrame({"a": [1, 2, 3], "c": [1, 2, 3]})
    )
    assert a.get("hash") is not None

    a, _, _ = compare_collections(pd.Series(data=[1, 2, 3], name="a"), pd.Series(data=[1, 2, 3], name="b"))
    assert a.get("hash") is not None
