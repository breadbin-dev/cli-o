import functools
import hashlib

from clio import is_primitive, is_iterable, bytes_to_chars, hash_collections, is_frame, ToDict


class ConstHash(ToDict):
    """
    python hashing has some limitations, not least of which:
        - you can't hash lists/dicts
        - hashes aren't guaranteed to be the same in different procs (string change for instance)
    this is purposefully an alternative implementation that does not interfere/interaction with __hash__
    """

    @functools.cached_property
    def _const_of_dict(self):
        return {self.__class__.__name__: const_hash(super().__to_dict__())}

    def __to_dict__(self, **kwargs):
        return self._const_of_dict

    def __const_hash__(self, lib):
        _hash(self._const_of_dict, lib)


class ConstDict(dict):
    """fixed dict that is also hashable"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__const_hash__ = const_hash(kwargs)

    @property
    def name(self):
        return self.__const_hash__

    def __setitem__(self, key, value):
        raise Exception("const")

    def update(self, __m, **kwargs):
        raise Exception("const")

    def __hash__(self):
        return self.__const_hash__.__hash__()

    def __eq__(self, other):
        return self.__const_hash__ == other.__const_hash__


def const_hash(data, len_=6, lib=..., prefix="") -> str:
    """
    recursively hash an object/dict/list
    will hash None and sort dictionary keys
    """
    if lib is ...:
        lib = hashlib.md5()
    _hash(data, lib)
    return prefix + bytes_to_chars(lib.digest(), len_=len_)


def _hash(item, lib):
    if item is None:
        lib.update("_none_".encode())
    elif item is ...:
        lib.update("...".encode())
    elif item is str:
        lib.update(item.encode())
    elif is_frame(item):
        hash_collections(item, lib)
    elif isinstance(item, ConstHash):
        item.__const_hash__(lib)
    elif isinstance(item, ConstDict):
        lib.update(item.__const_hash__.encode())
    elif isinstance(item, ToDict):
        _hash(item.__to_dict__(), lib)
    elif isinstance(item, dict):
        for k in sorted(item.keys()):
            _hash(k, lib)
            _hash(item[k], lib)
    elif is_iterable(item):
        for i in item:
            _hash(i, lib)
    elif is_primitive(item):
        lib.update(str(item).encode())
    else:
        raise Exception(f"Unsupported type [{type(item)}]")
