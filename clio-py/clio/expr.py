from __future__ import annotations
import abc
import functools
from typing import Any
import numpy as np
from clio import is_iterable, dttms, Keyed
from clio.collections import recurse_collections


class Expr:
    @abc.abstractmethod
    def execute(self, ctx: Context):
        raise NotImplementedError()

    def do_execute(self, ctx: Context):
        result = self.execute(ctx)
        return self.post_process(result, ctx)

    def post_process(self, result, ctx: Context):
        return result

    @abc.abstractmethod
    def __short_repr__(self) -> str:
        raise NotImplementedError()

    def __repr__(self) -> str:
        return self.__short_repr__()

    # boolean
    def __bool__(self) -> Expr:
        raise Exception("ambiguous when called before execution")

    # logical operators

    def __and__(self, other) -> Expr:
        if isinstance(other, bool) and other:
            return self
        return _And(self, other, "&")

    def __rand__(self, other) -> Expr:
        if isinstance(other, bool) and other:
            return self
        return _And(other, self, "&")

    def __or__(self, other) -> Expr:
        if isinstance(other, bool) and not other:
            return self
        return _Or(self, other, "|")

    def __ror__(self, other) -> Expr:
        if isinstance(other, bool) and not other:
            return self
        return _Or(other, self, "|")

    def __xor__(self, other) -> Expr:
        return _Xor(self, other, "^")

    def __rxor__(self, other) -> Expr:
        return _Xor(other, self, "^")

    # unary operators

    def __neg__(self) -> Expr:
        return _Neg(self, "-")

    def __pos__(self) -> Expr:
        return _Pos(self, "+")

    def __invert__(self) -> Expr:
        return _Invert(self, "~")

    # comparison operators

    def __lt__(self, other) -> Expr:
        return _LT(self, other, "<")

    def __gt__(self, other) -> Expr:
        return _GT(self, other, ">")

    def __le__(self, other) -> Expr:
        return _LE(self, other, "<=")

    def __ge__(self, other) -> Expr:
        return _GE(self, other, ">=")

    def __eq__(self, other) -> Expr:
        return _Eq(self, other, "==")

    def __ne__(self, other) -> Expr:
        return _NE(self, other, "!=")

    # math operators

    def __add__(self, other) -> Expr:
        return _Add(self, other, "+")

    def __radd__(self, other) -> Expr:
        return _Add(other, self, "+")

    def __sub__(self, other) -> Expr:
        return _Sub(self, other, "-")

    def __rsub__(self, other) -> Expr:
        return _Sub(other, self, "-")

    def __mul__(self, other) -> Expr:
        return _Mul(self, other, "*")

    def __rmul__(self, other) -> Expr:
        return _Mul(other, self, "*")

    def __truediv__(self, other) -> Expr:
        return _TrueDiv(self, other, "/")

    def __rtruediv__(self, other) -> Expr:
        return _TrueDiv(other, self, "/")

    def __floordiv__(self, other) -> Expr:
        return _FloorDiv(self, other, "//")

    def __rfloordiv__(self, other) -> Expr:
        return _FloorDiv(other, self, "//")

    def __mod__(self, other) -> Expr:
        return _Mod(self, other, "%")

    def __rmod__(self, other) -> Expr:
        return _Mod(other, self, "%")

    def __pow__(self, other) -> Expr:
        return _Pow(self, other, "**")

    def __rpow__(self, other) -> Expr:
        return _Pow(other, self, "**")

    # other utilities

    def isin(self, items: list[Any] | set[Any]) -> Expr:
        return _Isin(self, items, " in ")


class Context:
    def __call__(self, item, **kwargs):
        if isinstance(item, dict):
            return recurse_collections(item, map_=self.__call__, keep_nones=True)
        if isinstance(item, Expr):
            return item.do_execute(self)
        return item

    def lazy(self, item, map_=None, allow_none=False):
        """lazy load (on demand) from map"""
        return LazyLoader(self, item, map_=map_, allow_none=allow_none)


class LazyLoader:
    def __init__(self, loader, parent, map_, allow_none=False):
        if parent is None and not allow_none:
            raise Exception("item not found")
        self._loader = loader
        self._parent = parent
        self._map = map_
        self._cache = {}

    def __contains__(self, key):
        if self._parent is None:
            return False

        return Keyed.__accessor__(key) in self._parent

    def __getitem__(self, key):
        key = Keyed.__accessor__(key)
        if key in self._cache:
            return self._cache[key]

        if self._parent is not None:
            item = self._loader(self._parent[key])
            if self._map is not None:
                item = self._map(item)
        else:
            item = None

        self._cache[key] = item
        return item


@functools.cache
def _sub_bus_days(dttm, bus_days):
    return dttms.sub_busdays(dttm, days=bus_days)


@functools.cache
def _plus_bus_days(dttm, bus_days):
    return dttms.plus_busdays(dttm, days=bus_days)


class DttmContext(Context):
    def __init__(self, from_dttm: np.datetime64, to_dttm: np.datetime64, live: bool = False):
        self.from_dttm = from_dttm
        self.to_dttm = to_dttm
        self.live = live

    def trim(self, data):
        return dttms.trim_collection_to_span(data, self.from_dttm, self.to_dttm)

    def extend(self, from_days, to_days):
        from_dttm, to_dttm = self.from_dttm, self.to_dttm
        if from_days is not None:
            from_dttm = _sub_bus_days(from_dttm, from_days)
        if to_days is not None:
            to_dttm = _plus_bus_days(to_dttm, to_days)
        return DttmContext(from_dttm, to_dttm, live=self.live)

    def with_start_dttm(self, calc_start_dttm):
        if calc_start_dttm <= self.from_dttm:
            return self

        return DttmContext(calc_start_dttm, self.to_dttm, live=self.live)

    @property
    def from_dttm_as_date(self):
        return dttms.from_dttm_as_date(self.from_dttm)

    @property
    def to_dttm_as_date(self):
        return dttms.to_dttm_as_date(self.to_dttm)

    def __repr__(self):
        lv = " live" if self.live else ""
        return f"DttmContext[{dttms.format_dttm(self.from_dttm)} -> {dttms.format_dttm(self.to_dttm)}{lv}]"


class Col(Expr):
    def __init__(self, name: str):
        self._name = name

    def execute(self, ctx):
        if hasattr(ctx, self._name):
            return getattr(ctx, self._name)
        else:
            return ctx[self._name]

    def __short_repr__(self) -> str:
        return self._name.__repr__()


class Const(Expr):
    def __init__(self, c):
        self.c = c

    def execute(self, ctx):
        return self.c

    def __short_repr__(self) -> str:
        return self.c.__repr__()


class BinaryExpr(Expr):
    def __init__(self, x, y, sr):
        self.x = x
        self.y = y
        self._sr = sr

    def execute(self, ctx):
        return self.operate(ctx(self.x), ctx(self.y))

    @abc.abstractmethod
    def operate(self, x, y):
        pass

    def __short_repr__(self) -> str:
        return f"({self.x.__repr__()}{self._sr}{self.y.__repr__()})"


class UnaryExpr(Expr):
    def __init__(self, x, sr):
        self.x = x
        self._sr = sr

    def execute(self, ctx):
        return self.operate(ctx(self.x))

    @abc.abstractmethod
    def operate(self, x):
        pass

    def __short_repr__(self) -> str:
        return f"({self._sr}{self.x.__repr__()})"


# logical operators


class _And(BinaryExpr):
    def operate(self, x, y):
        return x & y


class _Or(BinaryExpr):
    def operate(self, x, y):
        return x | y


class _Xor(BinaryExpr):
    def operate(self, x, y):
        return x ^ y


# unary operators


class _Neg(UnaryExpr):
    def operate(self, x):
        return -x


class _Pos(UnaryExpr):
    def operate(self, x):
        return +x


class _Invert(UnaryExpr):
    def operate(self, x):
        return ~x


# comparison operators


class _LT(BinaryExpr):
    def operate(self, x, y):
        return x < y


class _GT(BinaryExpr):
    def operate(self, x, y):
        return x > y


class _LE(BinaryExpr):
    def operate(self, x, y):
        return x <= y


class _GE(BinaryExpr):
    def operate(self, x, y):
        return x >= y


class _Eq(BinaryExpr):
    def operate(self, x, y):
        return x == y


class _NE(BinaryExpr):
    def operate(self, x, y):
        return x != y


# math operators


class _Add(BinaryExpr):
    def operate(self, x, y):
        return x + y


class _Sub(BinaryExpr):
    def operate(self, x, y):
        return x - y


class _Mul(BinaryExpr):
    def operate(self, x, y):
        return x * y


class _TrueDiv(BinaryExpr):
    def operate(self, x, y):
        return x / y


class _FloorDiv(BinaryExpr):
    def operate(self, x, y):
        return x // y


class _Mod(BinaryExpr):
    def operate(self, x, y):
        return x % y


class _Pow(BinaryExpr):
    def operate(self, x, y):
        return x**y


# other utilities


class _Isin(BinaryExpr):
    def operate(self, x, y):
        if hasattr(x, "isin"):
            return x.isin(*y)
        else:
            if isinstance(x, np.ndarray):
                return np.isin(x, y)
            if is_iterable(x):
                return [x_ in y for x_ in x]
            else:
                return x in y
