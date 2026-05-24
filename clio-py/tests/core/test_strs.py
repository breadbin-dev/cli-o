import pytest

from core import strs


@pytest.mark.parametrize(
    "mem, target, expectation",
    [
        ("10.0g", None, 10 * 1024 * 1024 * 1024),
        ("10.0g", "k", 10 * 1024 * 1024),
        ("10.0t", "k", 10 * 1024 * 1024 * 1024),
        ("10", "k", 10),
    ],
)
def test_parse_readable_mem(mem, target, expectation):
    assert strs.parse_readable_mem(mem, target=target) == expectation


@pytest.mark.parametrize(
    "camel, snake",
    [
        ("thisIsCamel", "this_is_camel"),
        ("ThisIsAlso", "this_is_also"),
        ("this_is_not", "this_is_not"),
    ],
)
def test_camel_to_snake(camel, snake):
    assert strs.camel_to_snake(camel) == snake
