import json
from enum import StrEnum
from typing import Any, Literal

import numpy as np
import tabulate
import re
import random
import string

from core import Keyed


def _header(obj, h):
    return f"{h}*" if Keyed.safe_is_key_field(obj, h) else h


def tabulate_object(obj: Any, tablefmt: str = ...) -> str | None:
    if obj is None:
        return None
    data = [[_header(obj, k), v] for k, v in vars(obj).items() if not k.startswith("__")]
    return tabulate.tabulate(data, tablefmt=tablefmt, headers=["", type(obj).__name__])


def tabulate_objects(objs: list[Any], tablefmt: str = ...) -> str | None:
    """
    Given a list of objects (assumed to be the same type) create a pretty table
    """
    if not objs:
        return None
    obj0 = objs[0]
    cols = {x: [] for x in vars(obj0).keys() if not x.startswith("__")}

    rows = []
    for o in objs:
        rows.append(row := [])
        for c, l in cols.items():
            a = getattr(o, c)
            row.append(str(a) if isinstance(a, np.datetime64) else a)

    return tabulate.tabulate(rows, tablefmt=tablefmt, headers=[_header(obj0, h) for h in cols.keys()])


KB = 1024
MB = KB * KB
GB = MB * KB
TB = GB * KB
PB = TB * KB

memory_suffixes = {"k": KB, "m": MB, "g": GB, "t": TB, "p": PB}
memory_suffixes.update({f"{k}b": v for k, v in memory_suffixes.items()})
memory_suffixes.update({k.upper(): v for k, v in memory_suffixes.items()})


def parse_readable_mem(mem: str, target: Literal["k", "m", "g", "t", "p"] = None) -> int:
    match = re.search(r"^([0-9.]+)([a-zA-Z]*)$", mem)
    num = match.group(1)
    unit = match.group(2)

    if not unit:
        return int(mem)

    mem = float(num)
    unit = memory_suffixes[unit]
    divisor = memory_suffixes[target] if target else 1
    return int(mem * (unit / divisor))


def camel_to_snake(txt: str) -> str:
    txt = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", txt)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", txt).lower()


def snake_to_pascal(txt: str, separator: str = "") -> str:
    return txt.replace("_", " ").title().replace(" ", separator)


def random_str(k=6):
    return "".join(random.choices(string.ascii_letters + string.digits, k=k))


def to_json(obj):
    return json.dumps(obj)


def from_json(obj):
    return json.loads(obj)


def from_jsonl(obj):
    r = []
    with open(obj, "r") as f:
        for line in f:
            line = line.strip()
            if line and line != "[" and line != "]":
                if line[-1] == ",":
                    line = line[:-1]
                r.append(json.loads(line))
    return r


def title(x, preserve_case=True):
    if preserve_case:
        return " ".join([w.title() if w.islower() else w for w in x.split()])
    else:
        return x.title()


def maybe_range(a, format_=None, max_count=5):
    if len(a) == 0:
        return "[]"

    if format_ is None:

        def format_(x):
            return x.__repr__()

    if len(a) == 1:
        return format_(a[0])
    else:
        if len(a) <= max_count:
            return "[" + ",".join([format_(x) for x in a]) + "]"
        return f"[{format_(a[0])},{format_(a[1])},...{len(a) - 3},{format_(a[-1])}]"


def func_args_str(func, *args, **kwargs):
    args = [f"{a!r}" for a in args]
    kwargs = [f"{k}={v!r}" for k, v in kwargs.items()]
    return f"{func}({', '.join(args + kwargs)})"


def progress_bar(progress, total, prefix="", suffix="", decimals=1, length=100, fill="\u2588"):
    percent = ("{0:." + str(decimals) + "f}").format(perc_value := 100 * (progress / float(total)))
    filled_length = int(length * progress // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    color = "92m" if perc_value == 100 else "91m" if perc_value < 50 else "93m"
    return f"\r{prefix} |\033[{color}{bar}\033[0m| {percent}% {suffix}"


class ProgressBar:
    def __init__(self, prefix="", decimals=1, length=100, fill="\u2588", min_step=0.5):
        self._max_len = 0
        self._prefix = prefix
        self._decimals = decimals
        self._length = length
        self._fill = fill
        self._min_step = min_step
        self._last_progress = -1

    def update(self, progress, total, suffix=""):
        perc = 100 * (progress / float(total))
        if perc != 100 and (perc - self._last_progress) < self._min_step:
            return None  # update rate limit!
        self._last_progress = perc

        bar = progress_bar(
            progress,
            total,
            prefix=self._prefix,
            suffix=suffix,
            decimals=self._decimals,
            length=self._length,
            fill=self._fill,
        )
        if (_len := len(bar)) > self._max_len:
            self._max_len = _len
        else:
            bar += " " * (self._max_len - _len)
        return bar

    def print_update(self, progress, total, suffix=""):
        update = self.update(progress, total, suffix)
        if update is not None:
            print(update, end="")


class StringEnum(StrEnum):
    """
    StrEnum that allows instantiation on name
    """

    @classmethod
    def _missing_(cls, value):
        if value in cls.__members__:
            return cls.__members__[value]
        return super()._missing_(value)
