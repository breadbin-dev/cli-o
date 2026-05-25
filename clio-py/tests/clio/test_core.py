import dataclasses
import functools
import gc
import weakref

import numpy as np
import pytest

from clio import is_iterable, Keyed, Key, ToDict, dttms, kwargs_expand, kwargs_default, InstanceCache


def test_is_iterable():
    assert is_iterable([1, 2, 3])
    assert is_iterable((1, 2, 3))
    assert not is_iterable(np.asarray([1, 2, 3]))
    assert not is_iterable(1)
    assert not is_iterable("hello")


@dataclasses.dataclass
class MockSingleKeyed(Keyed):
    field1: str
    field2: float

    def key(self) -> Key:
        return Key(self.field1)


def test_single_key_object():
    o = MockSingleKeyed("a", 1)

    assert o.key() == Key("a")
    assert hash(o.key()) == hash(Key("a"))
    assert o.key() != Key("b")
    assert hash(o.key()) != Key("b")

    assert str(o.key()) == "a"
    assert o.is_key_field("field1")
    assert not o.is_key_field("field2")


@dataclasses.dataclass
class MockMultiKeyed(Keyed):
    field1: int
    field2: str
    field3: float

    def key(self) -> Key:
        return Key(self.field1, self.field2)


def test_multi_key_object():
    o = MockMultiKeyed(1, "a", 2.0)

    assert o.key() == Key(1, "a")
    assert hash(o.key()) == hash(Key(1, "a"))
    assert o.key() != Key(1, "b")
    assert hash(o.key()) != Key(1, "b")

    assert str(o.key()) == "1__a"
    assert o.is_key_field("field1")
    assert o.is_key_field("field2")
    assert not o.is_key_field("field3")


@dataclasses.dataclass
class MockInnerClass(ToDict):
    field1: int
    field2: np.datetime64


@dataclasses.dataclass
class MockOuterClass(ToDict):
    field1: str
    field2: MockInnerClass


def test_to_dict():
    item = MockOuterClass("hello", MockInnerClass(5, dttms.parse_dttm("20220101_22")))
    result = MockOuterClass.__from_dict__(item.__to_dict__())
    assert item == result

    item = MockOuterClass(None, MockInnerClass(None, ...))
    result = MockOuterClass.__from_dict__(item.__to_dict__())
    assert item == result


def test_lru_with_args():
    class MockLRU:
        def __init__(self, b=2):
            self.calls = 0
            self.b = b

        @kwargs_expand
        @functools.cache
        def a_method(self, a=..., b: int = kwargs_default()):
            self.calls += 1
            return "ok"

    lru = MockLRU()

    assert lru.a_method() == "ok"
    assert lru.a_method() == "ok"
    assert lru.calls == 1

    assert lru.a_method(a=..., b=2) == "ok"
    assert lru.a_method(a=..., b=...) == "ok"
    assert lru.calls == 1


class _CallCounter:
    def __init__(self):
        self.calls = 0

    @InstanceCache
    def compute(self, x):
        self.calls += 1
        return x * 2

    @InstanceCache(maxsize=1)
    def compute_limited(self, x):
        self.calls += 1
        return x * 3

    def __hash__(self):
        return 1

    def __eq__(self, other):
        return True


def test_instance_cache_basic():
    obj = _CallCounter()
    assert obj.compute(5) == 10
    assert obj.compute(5) == 10
    assert obj.calls == 1


def test_instance_cache_different_args():
    obj = _CallCounter()
    assert obj.compute(1) == 2
    assert obj.compute(2) == 4
    assert obj.calls == 2


def test_instance_cache_is_per_instance():
    a, b = _CallCounter(), _CallCounter()
    a.compute(7)
    b.compute(7)
    assert a.calls == 1
    assert b.calls == 1


@pytest.mark.parametrize("do_gc", [True, False])
def test_instance_cache_gc(do_gc):
    obj = _CallCounter()
    obj.compute(1)
    ref = weakref.ref(obj)
    del obj
    if do_gc:
        gc.collect()
    assert ref() is None


def test_instance_cache_maxsize():
    obj = _CallCounter()
    obj.compute_limited(1)
    obj.compute_limited(1)
    assert obj.calls == 1
    obj.compute_limited(2)
    obj.compute_limited(1)
    assert obj.calls == 3
