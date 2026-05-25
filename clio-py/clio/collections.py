from __future__ import annotations

import itertools
import numbers
import operator
import re

from collections import defaultdict, UserDict
from dataclasses import is_dataclass, asdict
from itertools import chain
from typing import Callable
from functools import reduce

import numpy as np
import pandas as pd

from clio import is_iterable, is_collection, is_frame
from clio.hashing import const_hash


def flat_union(iterables):
    return reduce(np.union1d, iterables, [])


def flat_intersection(iterables):
    return reduce(np.intersect1d, iterables, iterables[0])


def flip(items, ncol):
    return itertools.chain(*[items[i::ncol] for i in range(ncol)])


def flat_lists(iterables):
    result = []
    for i in iterables:
        if is_iterable(i):
            result += flat_lists(i)
        else:
            result.append(i)
    return result


def ensure_list(x, add_item=None):
    if x is None or x is ...:
        return x

    if isinstance(x, (list, set, tuple)) and add_item is None:
        return x
    else:
        if is_iterable(x):
            lst = list(x)
            if add_item is not None:
                lst.append(add_item)
            return lst
        else:
            if add_item is None:
                return [x]
            else:
                return [x, add_item]


def _value_arg_only_decorator(function):
    def wrapper(key, val):
        return function(val)

    return wrapper


def recurse_collections(
    c,
    filter_=None,
    map_=None,
    private=True,
    hash_safe=True,
    keep_nones=False,
    cache=None,
    top_level=False,
    context=None,
    kv_map=None,
):
    """
    Recursively traverse and process nested collections.
    :param c: The collection to be processed.
    :param filter_: A function to filter elements. Defaults to a function that allows all elements.
    :param map_: A function to transform elements. Defaults to a function that returns elements unchanged.
    :param private: If False, exclude keys starting with an underscore ('_') from processing.
        Defaults to True.
    :param hash_safe: If True, raises an exception if the collection has a `__do_not_hash__`
        attribute. Defaults to True.
    :param keep_nones: If True, retains `None` values in the output. Defaults to False.
    :param cache: A RecursionCache instance
    :param top_level: Indicates whether the current call is at the top level of recursion.
        Used internally. Defaults to False.
    :param context: The context (e.g., key) associated with the current value. Used internally.
        Defaults to None.
    :param kv_map: A function to transform elements that also takes the key/context as an argument. Can only be
        provided if map_ is None.
    """

    if filter_ is None:

        def filter_(x):
            return True

    if map_ is not None and kv_map is not None:
        raise ValueError("Only one of map_ or kv_map can be provided")
    elif map_ is not None:
        kv_map = _value_arg_only_decorator(map_)
    elif kv_map is None:

        def kv_map(k, v):
            return v

    if hash_safe and hasattr(c, "__do_not_hash__"):
        raise Exception(f"Do not hash: {type(c)}")

    if isinstance(c, dict):
        id_ = None
        if not top_level and cache is not None:
            if (id_ := id(c)) in cache:
                return cache[id_]

        result = {
            k: recurse_collections(
                v,
                filter_=filter_,
                private=private,
                keep_nones=keep_nones,
                cache=cache,
                context=k,
                kv_map=kv_map,
            )
            for k, v in c.items()
            if not k.startswith("__") and (private or not k.startswith("_"))
        }
        result = {k: v for k, v in result.items() if keep_nones or v is not None}
        if not result and not keep_nones:
            result = None

        if id_ is not None:
            return cache.map(id_, result)

        return result

    elif is_iterable(c):
        id_ = None
        if not top_level and cache is not None:
            if (id_ := id(c)) in cache:
                return cache[id_]

        result = [
            recurse_collections(
                x, filter_=filter_, private=private, keep_nones=keep_nones, cache=cache, context=context, kv_map=kv_map
            )
            for x in c
        ]
        result = [x for x in result if keep_nones or x is not None]
        if not result and not keep_nones:
            result = None

        if id_ is not None:
            return cache.map(id_, result)

        return result

    else:
        if filter_(c):
            return kv_map(context, c)
        else:
            return None


class RecursionCache:
    """if you're likely to be recursing the same items, provide a cache and option mapping of dict/list"""

    def __init__(self, timer=None):
        self._timer = timer
        self._cache = {}

    def map(self, id_, result):
        self._cache[id_] = result
        return result

    def __contains__(self, item):
        return item in self._cache

    def __getitem__(self, item):
        return self._cache[item]

    def __repr__(self):
        return f"RecursionCache({len(self._cache)}): {repr(self._timer)}"

    def begin(self):
        return None if self._timer is None else self._timer.begin()

    def complete(self, name, began):
        if self._timer is not None:
            self._timer.complete(name, began)

    def clear(self):
        self._cache.clear()
        if self._timer is not None:
            self._timer.clear()


def count_tree(t, depth=0, flatten_=None):
    if flatten_ is not None:
        tree = count_tree(t, depth)
        return flatten(tree, to_level=flatten_, sep="/")

    if depth < 0:
        keys_struct = get_keys_struct(t)
        selection = default_tree()
        keys = {}
        for ks in keys_struct:
            sub_keys = ks[:depth]
            key = "__".join(sub_keys)
            keys[key] = sub_keys
            set_by_path(selection[key], ks[depth:], get_by_path(t, ks))
        result = default_tree()
        for key, to_sum in selection.items():
            set_by_path(result, keys[key], count_tree(to_sum, depth=0))
        return dict(result)

    if depth == 0 or not isinstance(t, dict):
        if isinstance(t, dict):
            return sum([count_tree(i) for i in t.values()])
        elif is_iterable(t):
            return sum([count_tree(i) for i in t])
        else:
            return 1 if t else 0
    else:
        depth -= 1
        return {k: count_tree(v, depth=depth) for k, v in t.items()}


def build_filter(f, if_none=True):
    """users can specify a callable, a set, or a regex. this will build the appropriate filter."""
    if f is None:
        return lambda x: if_none
    if isinstance(f, bool):
        return lambda x: f
    if isinstance(f, Callable):
        return f
    if isinstance(f, set):
        return lambda x: x in f
    rx = re.compile(f)
    return lambda x: rx.match(x) is not None


class Preparable:
    def __init__(self):
        self.__preparing__ = False
        self.__prepared__ = False

    def prepare(self):
        assert not (self.__preparing__ or self.__prepared__), "Prepare once"
        self.__preparing__ = True
        self._pre_prepare()
        self._do_prepare()
        self._post_prepare()
        self.__prepared__ = True
        self.__preparing__ = False
        return self

    def _pre_prepare(self):
        pass

    def _do_prepare(self):
        pass

    def _post_prepare(self):
        pass


def get_by_path(root, items):
    """Access a nested object in root by item sequence."""
    return reduce(operator.getitem, items, root)


def set_by_path(root, items, value):
    """Set a value in a nested object in root by item sequence."""
    get_by_path(root, items[:-1])[items[-1]] = value


def select(dd, key, level):
    selected_keys = [el for el in get_keys_struct(dd) if el[level] == key]
    out = {}
    for name, group in itertools.groupby(selected_keys, lambda x: ".".join(x[:level])):
        out[name] = {".".join(path[level + 1 :]): get_by_path(dd, path) for path in group}

    return out


def default_tree(deep_copy=None):
    """defaultdict that will default recursively"""
    result = defaultdict(default_tree)

    if deep_copy is not None:

        def _dc(a, b):
            for k, v in a.items():
                if isinstance(v, dict):
                    _dc(v, b[k])
                else:
                    b[k] = v

        _dc(deep_copy, result)

    return result


def recursively_apply(a, b, op):
    if isinstance(a, dict):
        return {k: recursively_apply(a[k], b[k], op) for k in a.keys() | b.keys()}
    if is_iterable(a):
        return [recursively_apply(a[i], b[i], op) for i in range(max(len(a), len(b)))]
    return op(a, b)


def get_keys_struct(d, parent=None, out=None):
    if out is None:
        out = []
    if parent is None:
        parent = []

    if isinstance(d, dict):
        for key, el in d.items():
            branch_parent = parent + [key]
            if isinstance(el, dict):
                get_keys_struct(el, parent=branch_parent, out=out)
            else:
                out.append(branch_parent)

    return out


def _merge_dict(d1: dict, d2: dict):
    out = d1.copy()
    out.update(d2)
    return out


def merge_dict(*dicts):
    return reduce(_merge_dict, dicts, {})


def _safe_merge(d1: dict, d2: dict):
    if d1.keys().isdisjoint(d2):
        return merge_dict(d1, d2)

    raise AttributeError(f"Dicts have overlapping keys!: {d1.keys() & d2.keys()}")


def safe_merge(*dicts):
    return reduce(_safe_merge, dicts, {})


def _get_pos_idx(el, idx):
    if idx >= 0:
        return idx
    else:
        return len(el) - (abs(idx) - 1)


def max_dict_depth(d):
    if isinstance(d, dict):
        return 1 + (max(map(max_dict_depth, d.values())) if d else 0)
    return 0


def flatten(ds, from_level=0, to_level=-1, sep="__"):
    if max_dict_depth(ds) <= 1:
        return ds
    keys_struct = get_keys_struct(ds)

    new_keys = [
        el[:from_level] + [sep.join(el[from_level : _get_pos_idx(el, to_level)])] + el[_get_pos_idx(el, to_level) :]
        for el in keys_struct
    ]

    out = default_tree()

    for in_keys, out_keys in zip(keys_struct, new_keys):
        set_by_path(root=out, items=out_keys, value=get_by_path(root=ds, items=in_keys))

    return dict(out)


def group_by_key_slice(ds, slice, sep=".", agg=None):
    result = {}
    for k, v in ds.items():
        key = sep.join(k.split(sep)[slice])
        group = result.get(key)
        if group is None:
            result[key] = group = []
        group.append(v)

    if agg is not None:
        result = {k: agg(v) for k, v in result.items()}

    return result


def find_by_inner_key(ds, key):
    inners = {}
    for k, v in ds.items():
        if isinstance(v, dict):
            v = find_by_inner_key(v, key)
            if v is not None:
                inners[k] = v
        elif k == key:
            return v
    return inners if len(inners) > 0 else None


def find_by_inner_keys(ds, keys):
    inners = {}
    for k, v in ds.items():
        if isinstance(v, dict):
            v = find_by_inner_keys(v, keys)
            if v is not None:
                inners[k] = v
        elif k in keys:
            inners[k] = v
    return inners if len(inners) > 0 else None


def compare_collections(a, b, sort_lists=True, summarise_frames=True, epsilon=None, epsilon_frac=None):
    """compare two potentially nested collections, return unique_to_a, in_both, unique_to_b"""

    if isinstance(a, dict) and isinstance(b, dict):
        ar = {k: a[k] for k in a.keys() - b.keys()}
        br = {k: b[k] for k in b.keys() - a.keys()}
        ur = {}
        for uk in a.keys() & b.keys():
            epsilon_i = epsilon[uk] if isinstance(epsilon, dict) else epsilon
            epsilon_frac_i = epsilon_frac[uk] if isinstance(epsilon_frac, dict) else epsilon
            ax, ux, bx = compare_collections(a[uk], b[uk], sort_lists, summarise_frames, epsilon_i, epsilon_frac_i)
            if ax is not None:
                ar[uk] = ax
            if ux is not None:
                ur[uk] = ux
            if bx is not None:
                br[uk] = bx
        return ar if ar else None, ur if ur else None, br if br else None
    elif is_iterable(a) and is_iterable(b):
        if sort_lists:
            if not any(isinstance(x, pd.core.generic.NDFrame) for x in chain(a, b)):
                b = sorted(b)
                a = sorted(a)

        ar, ur, br = [], [], []

        ai = 0
        bi = 0
        while ai < len(a) or bi < len(b):
            if ai == len(a):
                br.append(b[bi])
                bi += 1
            elif bi == len(b):
                ar.append(a[ai])
                ai += 1
            else:
                ax, ux, bx = compare_collections(a[ai], b[bi], sort_lists, summarise_frames, epsilon)
                if ax and not is_collection(ax) and bx and not is_collection(bx):
                    assert ux is None
                    if ax > bx:
                        br.append(bx)
                        bi += 1
                    else:
                        ar.append(ax)
                        ai += 1
                else:
                    if ax is not None:
                        ar.append(ax)
                    if ux is not None:
                        ur.append(ux)
                    if bx is not None:
                        br.append(bx)
                    bi += 1
                    ai += 1
        return ar if ar else None, ur if ur else None, br if br else None
    else:
        if epsilon is not None:
            if isinstance(a, numbers.Number) and type(a) is not float:
                a = float(a)
            if isinstance(b, numbers.Number) and type(b) is not float:
                b = float(b)

        if (a is None) or (b is None) or (type(a) is not type(b)):
            return a, None, b

        if is_frame(a):
            if isinstance(a, np.ndarray):
                equals = np.all(a == b)
            else:
                if isinstance(a, pd.DataFrame):
                    equals = a.index.equals(b.index) and a.columns.equals(b.columns) and a.equals(b)
                else:
                    equals = a.index.equals(b.index) and a.name == b.name and a.equals(b)

            if summarise_frames and not equals:
                return compare_collections(summarise_frame(a), summarise_frame(b), False, False, epsilon)
        else:
            if epsilon is not None and isinstance(a, numbers.Number):
                equals = abs(a - b) <= epsilon
            elif epsilon_frac is not None and isinstance(a, numbers.Number):
                equals = abs(a - b) <= epsilon_frac * abs(a)
            else:
                equals = a == b

        if equals:
            return None, a, None
        else:
            return a, None, b


def get_index(frame):
    if isinstance(frame, pd.Index):
        return frame
    if isinstance(frame, (pd.DataFrame, pd.Series)):
        return frame.index
    return None


def summarise_frame(frame, group_by=None):
    if frame.empty:
        return {"empty": True}

    if group_by is not None:
        return {group: summarise_frame(f) for group, f in frame.groupby(group_by)}

    summary = {
        "hash": const_hash(frame),
        "shape": (shape := frame.shape),
        "nans": np.count_nonzero(np.isnan(frame)),
        "zeros": np.count_nonzero(frame == 0),
    }
    try:
        summary["mean"] = np.mean(frame)
    except Exception as ex:
        summary["mean"] = ex.__class__.__name__

    if len(shape) == 1:
        summary["first_value"] = frame.iloc[0]
        summary["last_value"] = frame.iloc[-1]
    elif shape[1] == 1:
        summary["first_value"] = frame.iloc[(0, 0)]
        summary["last_value"] = frame.iloc[(0, -1)]
    else:
        try:
            summary["sum_first_row"] = np.sum(frame.iloc[0])
            summary["sum_last_row"] = np.sum(frame.iloc[-1])
        except Exception:
            summary["hash_first_row"] = const_hash(frame.iloc[0])
            summary["hash_last_row"] = const_hash(frame.iloc[-1])

    if (index := get_index(frame)) is not None:
        summary["first_index"] = index[0]
        summary["last_index"] = index[-1]
    return summary


class SafeMap:
    def __init__(self, mp):
        self._map = mp

    def __getitem__(self, item):
        return self.get(item)

    def __contains__(self, item):
        return item in self._map

    def get(self, item, dflt=None):
        return self._map.get(item, dflt)


def take_single(iterable, name="i"):
    if len(iterable) == 1:
        return next(iter(iterable))
    else:
        raise Exception(f"{name} expected single element")


class TreeCounter(dict):
    def __init__(self, name="total"):
        super().__init__()
        self.name = name
        self.counter = 0
        self.total = None

    def add(self, value, *tree):
        self._add(value)
        if len(tree) > 0:
            leaf = tree[0]
            if leaf not in self:
                self[leaf] = TreeCounter(leaf)
            self[leaf].add(value, *tree[1:])

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            return super().__getattribute__(item)

    def _add(self, value):
        self.counter += 1
        if self.total is None:
            self.total = value
        else:
            self.total += value

    def __short_repr__(self):
        total = self.total
        if isinstance(total, np.timedelta64):
            from clio import dttms

            total = dttms.format_friendly_time(self.total)

        if self.counter == total:
            return f"{self.name}: {total}"
        else:
            return f"{self.name}[{self.counter}]: {total}"

    def __repr__(self):
        if len(self) == 0:
            return self.__short_repr__()
        else:
            leaves = sorted(self.values(), key=lambda x: x.total, reverse=True)
            inner = "\n".join([f"  {leaf.__short_repr__()}," for leaf in leaves])
            return f"{self.__short_repr__()} {{\n{inner}\n}}"

    def to_frame(self):
        leaves = sorted(self.values(), key=lambda x: x.total, reverse=True)
        data = []
        for leaf in leaves:
            data_i = {"path": leaf.name, "count": leaf.counter}
            if is_dataclass(leaf.total):
                data_i |= asdict(leaf.total)
            else:
                data_i["total"] = leaf.total
            data.append(data_i)
        return pd.DataFrame(data)


class DefaultDictWithKey(defaultdict):
    """
    This class allows one to define a default dict with a function that
    takes the key as argument. Thus, if the key is missing, it
    defaults to a function that operates on the key
    """

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            self[key] = self.default_factory(key)
            return self[key]


class BijectiveMap(UserDict):
    """
    A dictionary where each key maps to a unique value, and
    each value maps back to exactly one key.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._inverse = {}
        self._emtpy_obj = object()
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        # Remove old inverse if this key already existed
        old_value = self.data.get(key, self._emtpy_obj)
        if old_value is not self._emtpy_obj:
            self._inverse.pop(old_value)

        existing_key = self._inverse.get(value)
        if existing_key is not None and existing_key != key:
            raise ValueError(
                f"Value '{value}' is already mapped by key '{existing_key}'. " "BijectiveMap does not allow duplicates."
            )

        # Update both forward and inverse mappings
        self.data[key] = value
        self._inverse[value] = key

    def __delitem__(self, key):
        value = self.data[key]
        self._inverse.pop(value)
        super().__delitem__(key)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def clear(self):
        super().clear()
        self._inverse.clear()

    @property
    def inverse_dict(self):
        return self._inverse

    def inverse(self, value, default=...):
        """Return the key for a given value (reverse lookup)."""
        if default is ...:
            return self._inverse[value]
        else:
            return self._inverse.get(value, default)
