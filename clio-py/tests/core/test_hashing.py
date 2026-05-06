import hashlib
from dataclasses import dataclass

import pytest

import pandas as pd

from core.hashing import const_hash, ConstHash, bytes_to_chars


@dataclass
class MockConstHash(ConstHash):
    a: int
    b: int


@pytest.mark.parametrize(
    "a, b",
    [
        (None, None),
        (..., ...),
        ("a", "ab"[0]),
        (5, 10 // 2),
        ([1, 2, None, 4], [1, 2, None, 4]),
        ({"a": 1, "b": 2}, {"b": 2, "a": 1}),
        (MockConstHash(1, 2), MockConstHash(1, 2)),
        (pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})),
        (pd.Series(data=[1, 2, 3], index=[4, 5, 6]), pd.Series(data=[1, 2, 3], index=[4, 5, 6])),
        (pd.Index(["A", "B", "C"]), pd.Index(["A", "B", "C"])),
    ],
)
def test_hashing_equals(a, b):
    assert const_hash(a) == const_hash(b)


@pytest.mark.parametrize(
    "a, b",
    [
        (None, ...),
        ("a", "ab"[1]),
        (5, 10),
        ([1, 2, None, 4], [1, 2, 4, None]),
        ({"a": 1, "b": 2}, {"a": 1, "b": 1}),
        (MockConstHash(1, 2), MockConstHash(2, 1)),
        (pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), pd.DataFrame({"b": [1, 2, 3], "a": [4, 5, 6]})),
        (pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 7]})),
        (pd.Series(data=[1, 2, 3], index=[4, 5, 6]), pd.Series(data=[1, 2, 4], index=[4, 5, 6])),
        (pd.Series(data=[1, 2, 3], index=[4, 5, 6]), pd.Series(data=[1, 2, 3], index=[4, 5, 7])),
    ],
)
def test_hashing_not_equals(a, b):
    assert const_hash(a) != const_hash(b)


def test_string_const():
    """python's own string hash changes between runtimes!!"""
    assert const_hash("abc", len_=8) == "MrjtC1kG"


def test_hex_to_chars():
    lib = hashlib.md5()
    lib.update("abc".encode("utf-8"))
    d = bytes_to_chars(lib.digest(), len_=6)
    assert len(d) == 6
