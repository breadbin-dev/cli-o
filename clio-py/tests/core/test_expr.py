import operator
import pytest

import numpy as np

from core.expr import Expr, Col, Context
from tests import assert_explicit_equals


class MockQuery(Expr):
    def __init__(self, r):
        self.r = r

    def execute(self, ctx):
        return self.r


@pytest.mark.parametrize(
    "op, x, y, r",
    [
        # logical operators
        (operator.and_, True, True, True),
        (operator.and_, True, False, False),
        (operator.or_, True, True, True),
        (operator.or_, True, False, True),
        (operator.or_, False, False, False),
        (operator.xor, True, False, True),
        (operator.xor, True, True, False),
        # comparison operators
        (operator.lt, 2, 5, True),
        (operator.lt, 2, 2, False),
        (operator.lt, 2, 1, False),
        (operator.gt, 2, 5, False),
        (operator.gt, 5, 5, False),
        (operator.gt, 5, 2, True),
        (operator.le, 2, 5, True),
        (operator.le, 2, 2, True),
        (operator.le, 2, 1, False),
        (operator.ge, 2, 5, False),
        (operator.ge, 5, 5, True),
        (operator.ge, 5, 2, True),
        (operator.eq, 2, 5, False),
        (operator.eq, 5, 5, True),
        (operator.ne, 2, 5, True),
        (operator.ne, 5, 5, False),
        # math operators
        (operator.add, 2, 5, 7),
        (operator.sub, 2, 5, -3),
        (operator.mul, 2, 5, 10),
        (operator.truediv, 5, 2, 2.5),
        (operator.floordiv, 5, 2, 2),
        (operator.mod, 5, 2, 1),
        (operator.pow, 5, 2, 25),
    ],
)
def test_binary_operator(op, x, y, r):
    assert op(x, y) == r
    ctx = Context()
    assert ctx(op(MockQuery(x), y)) == r
    assert ctx(op(x, MockQuery(y))) == r


@pytest.mark.parametrize(
    "op, x, r",
    [
        (operator.invert, 3, -4),
        (operator.pos, 3, 3),
        (operator.neg, 3, -3),
    ],
)
def test_unary_operator(op, x, r):
    assert op(x) == r
    assert Context()(op(MockQuery(x))) == r


def test_binary_err():
    with pytest.raises(Exception):
        if MockQuery(True):
            pass

    with pytest.raises(Exception):
        if 5 == MockQuery(5):
            pass


def test_assignment():
    ctx = Context()

    i = MockQuery(5)
    i += MockQuery(4)
    assert ctx(i) == 9

    i = MockQuery(5)
    i += 4
    assert ctx(i) == 9

    i = 5
    i += MockQuery(4)
    assert ctx(i) == 9


def test_isin():
    ctx = Context()
    ctx.A = [1, 2, 3]
    ctx.B = {1, 2, 3}
    ctx.C = np.asarray([1, 2, 3])
    ctx.D = 2
    ctx.E = 1

    assert Col("A").isin({1, 4}).execute(ctx) == [True, False, False]
    assert Col("B").isin([1, 4]).execute(ctx) == [True, False, False]
    assert_explicit_equals(Col("C").isin([1, 4]).execute(ctx), np.asarray([True, False, False]))
    assert_explicit_equals(Col("D").isin([1, 4]).execute(ctx), False)
    assert_explicit_equals(Col("E").isin([1, 4]).execute(ctx), True)
