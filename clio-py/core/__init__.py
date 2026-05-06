import dataclasses
import datetime
import enum
import functools
import hashlib
import inspect
import string
import weakref
from abc import abstractmethod
from argparse import ArgumentTypeError
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, TypeVar, Iterable, Self
from types import MethodType
import re
import io as systemio

import numpy as np
import pandas as pd
from numba import njit


def is_iterable(obj):
    if isinstance(obj, str):
        return False  # while you can iterate on a string, you probably weren't intending to
    if is_frame(obj):
        return False  # we don't want to unintentionally explode a dataframe
    return obj is not None and hasattr(obj, "__iter__")


def is_collection(obj) -> bool:
    return isinstance(obj, dict) or is_iterable(obj)


def is_frame(obj) -> bool:
    return isinstance(obj, (pd.Series, pd.DataFrame, pd.Index, np.ndarray))


def is_pandas(obj) -> bool:
    return isinstance(obj, (pd.Series, pd.DataFrame))


def is_primitive(obj: Any) -> bool:
    return isinstance(obj, (int, float, str, bool))


def empty_series(data_dtype=np.floating, index_dtype="<M8[ns]", name=None):
    return pd.Series(np.asarray([], dtype=data_dtype), index=np.asarray([], dtype=index_dtype), name=name)


def empty_frame(data_dtype=np.floating, index_dtype="<M8[ns]", cols=...):
    if cols is ...:
        cols = ["0"]
    return pd.DataFrame({c: np.asarray([], dtype=data_dtype) for c in cols}, index=np.asarray([], dtype=index_dtype))


format_iso = "%Y-%m-%dT%H:%M:%SZ"

dtype_nanos = "<M8[ns]"
dtype_micros = "<M8[us]"
dtype_seconds = "<M8[s]"
dtype_minutes = "<M8[m]"
dtype_hours = "<M8[h]"
dtype_days = "<M8[D]"
dtype_weeks = "<M8[W]"
dtype_months = "<M8[M]"
dtype_years = "<M8[Y]"

a_nano = np.timedelta64(1, "ns")
a_second = np.timedelta64(1, "s")
a_minute = np.timedelta64(1, "m")
an_hour = np.timedelta64(1, "h")
a_day = np.timedelta64(1, "D")
a_month = np.timedelta64(1, "M")
a_year = np.timedelta64(1, "Y")

EOD = np.timedelta64(22, "h")

hash_chars = string.digits + string.ascii_letters

DttmLike = TypeVar("DttmLike", str, np.datetime64, np.ndarray, datetime.datetime, pd.Timestamp)
TimeLike = TypeVar("TimeLike", str, np.timedelta64, np.ndarray, datetime.time, datetime.timedelta)

NoneResult = "__None__"


def now() -> np.datetime64:
    return pd.Timestamp.utcnow().to_datetime64().astype(dtype_nanos)


def today(_now=..., _shift=0) -> np.datetime64:
    if _now is ...:
        _now = now()
    today = _now.astype(dtype_days)
    if _shift:
        today += _shift * a_day
    return today


def is_midnight(dttm: DttmLike):
    if isinstance(dttm, pd.Index):
        dttm = dttm.values
    return as_time(dttm).astype(int) == 0


def as_date(dt: DttmLike) -> np.datetime64:
    if isinstance(dt, str):
        try:
            return parse_date(dt)
        except ValueError:
            return parse_dttm(dt).astype(dtype_days)
    if isinstance(dt, pd.Index):
        dt = dt.values
    return _as_dtype(dt, dtype_days)


def as_time(time: TimeLike) -> np.timedelta64:
    if isinstance(time, str):
        return parse_time(time)

    if isinstance(time, pd.Index):
        time = time.values

    if isinstance(time, np.timedelta64) or (isinstance(time, np.ndarray) and time.dtype.type == np.timedelta64):
        return time

    if isinstance(time, np.datetime64) or (isinstance(time, np.ndarray) and time.dtype.type == np.datetime64):
        return time - as_date(time)

    if isinstance(time, datetime.time):
        time = datetime.timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)

    if isinstance(time, datetime.timedelta):
        return np.timedelta64(int(time.total_seconds()), "s")

    if isinstance(time, pd.core.arrays.DatetimeArray):
        return time - as_date(time)

    dtype = f"({time.dtype})" if hasattr(time, "dtype") else ""
    raise ArgumentTypeError(f"Unsupported type {type(time)}{dtype}")


def format_dt(dt: np.datetime64, frmt: str = ...):
    assert dt.dtype == dtype_days, "all dates must be explicitly 'D'"
    if frmt is ...:
        frmt = "%Y%m%d"
    return pd.Timestamp(dt).strftime(frmt)


def format_dttm(dttm: np.datetime64, frmt: str = ..., nanos=True, enforce_nanos=True) -> str:
    if enforce_nanos:
        assert dttm.dtype == dtype_nanos, "all dttms must be nanos"
    ts = pd.Timestamp(dttm)

    if frmt is not ...:
        s = ts.strftime(frmt)
        if nanos and frmt.endswith("%f") and ts.nanosecond > 0:
            s = f"{s}{ts.nanosecond:03d}"
        return s

    micros = ts.microsecond % 1_000
    if micros != 0:
        result = ts.strftime("%Y%m%d_%H%M%S%f")
        return f"{result}{ts.nanosecond:03d}" if nanos and ts.nanosecond > 0 else result

    millis = ts.microsecond // 1_000
    if millis != 0:
        return ts.strftime("%Y%m%d_%H%M%S") + f"{millis:03d}"

    if ts.second != 0:
        return ts.strftime("%Y%m%d_%H%M%S")

    if ts.minute != 0:
        return ts.strftime("%Y%m%d_%H%M")

    return ts.strftime("%Y%m%d_%H")


_format_period_pattern = re.compile(r"^<m8\[(\w+)\]$")


def format_period(period: np.timedelta64) -> str:
    units = re.match(_format_period_pattern, period.dtype.str).group(1)
    return f"{period.astype(int)}{units}"


def plus_busdays(dttm: DttmLike, days=1, cal=..., roll=...):
    if roll is ...:
        roll = "forward"

    if roll is None:
        roll = "backward" if days >= 0 else "forward"  # +1/-1 to weekends = monday/friday

    if cal is ...:
        cal = np.busdaycalendar()

    dtype = dttm.dtype
    time = None
    if not np.all(is_midnight(dttm)):
        time = as_time(dttm)
    dttm = as_date(dttm)

    dttm = np.busday_offset(
        dates=dttm,
        offsets=days,
        roll=roll,
        busdaycal=cal,
    ).astype(dtype)
    return dttm if time is None else dttm + time


def sub_busdays(dttm: DttmLike, days=1, cal=..., roll=...):
    if roll is ...:
        roll = "backward"
    return plus_busdays(dttm, days=-days, cal=cal, roll=roll)


class BDOffset:
    def __init__(self, offset: int, cal: np.busdaycalendar = ..., holidays=None, weekmask="MonTueWedThuFri", roll=...):
        self.offset = offset
        if holidays is not None:
            assert cal is ..., "can't have holidays and calendar"
            cal = np.busdaycalendar(weekmask=weekmask, holidays=holidays)
        self.cal = cal
        self.roll = roll

    def __radd__(self, other: np.ndarray) -> np.ndarray:
        return plus_busdays(other, self.offset, cal=self.cal, roll=self.roll)

    def __rsub__(self, other: np.ndarray) -> np.ndarray:
        return sub_busdays(other, self.offset, cal=self.cal, roll=self.roll)

    def __array_ufunc__(self, ufunc, method, *inputs, out=None):
        if method == "__call__" and len(inputs) == 2:
            if ufunc == np.add:
                result = inputs[1].__radd__(inputs[0])
            elif ufunc == np.subtract:
                result = inputs[1].__rsub__(inputs[0])
            else:
                raise NotImplementedError(f"ufunc {ufunc} not implemented")

            if out is not None:
                out[0][:] = result

            return result

        # this can be extended to support more uses
        raise NotImplementedError(f"ufunc {method} {ufunc} not implemented")

    def __repr__(self):
        rl = "" if self.roll is ... else f" roll={self.roll}"
        cal = "" if self.cal is ... else f" cal={self.cal}"
        return f"{self.offset}BD{rl}{cal}"

    def __hash__(self):
        result = hash(self.offset)
        if self.roll is not ...:
            result ^= hash(self.roll)
        if self.cal is not ...:
            result ^= hash(self.cal)
        return result

    def __eq__(self, other):
        if self.offset != other.offset:
            return False
        if self.roll != other.roll:
            return False
        if self.cal != other.cal:
            return False
        return True

    @property
    def dtype(self):
        return "bus_days"


def parse_date(dt, frmt=...):
    if frmt is ...:
        if "-" in dt:
            frmt = "%Y-%m-%d"
        else:
            frmt = "%Y%m%d"

    return as_date(datetime.datetime.strptime(dt, frmt))


def parse_time(time: TimeLike) -> np.timedelta64:
    if isinstance(time, np.timedelta64):
        return time
    if time == "EOD":
        return EOD
    time = time.split(":")
    hours = int(time[0])
    if len(time) == 1:
        return np.timedelta64(hours, "h")
    mins = int(time[1]) + 60 * hours
    if len(time) == 2:
        return np.timedelta64(mins, "m")
    nanos = 0
    if "." in time[2]:
        time[2], nanos = time[2].split(".")
        nanos += (9 - len(nanos)) * "0"
        nanos = int(nanos)
    secs = int(time[2]) + 60 * mins

    if nanos:
        return np.timedelta64(secs * 1_000_000_000 + nanos, "ns")
    else:
        return np.timedelta64(secs, "s")


_period_pattern = re.compile(r"^([+-]?\d+)(\w+)$")


def parse_period(period: str) -> np.timedelta64:
    if isinstance(period, (np.timedelta64, BDOffset)):
        return period

    if period.endswith("am"):
        return parse_time(period[:-2])

    if period.endswith("pm"):
        tm = parse_time(period[:-2])
        h12 = 12 * an_hour
        if tm > h12:
            raise Exception(f"{period} is not valid pm time")
        return tm + h12

    if ":" in period:
        return parse_time(period)

    m = re.match(_period_pattern, period)
    v = int(m[1])
    t = m[2]

    match t:
        case "W" | "w":
            t = "D"
            v *= 7
        case "Q" | "q":
            t = "M"
            v *= 3
        case "y":
            t = "Y"
        case "d":
            t = "D"
        case "bd":
            t = "BD"

    if t == "BD":
        return BDOffset(v)

    return np.timedelta64(v, t)


def dayify_period(period: np.timedelta64) -> np.timedelta64:
    if period.dtype == "<m8[M]":
        return np.timedelta64(period.astype(int) * 31, "D")
    if period.dtype == "<m8[Y]":
        return np.timedelta64(period.astype(int) * 365, "D")
    return period


def _as_dtype(dttm: DttmLike, dttm_dtype):
    if isinstance(dttm, np.datetime64):
        return dttm.astype(dttm_dtype)

    if isinstance(dttm, np.ndarray):
        return dttm.astype(dttm_dtype)

    if isinstance(dttm, datetime.datetime):
        return np.datetime64(dttm).astype(dttm_dtype)

    if isinstance(dttm, pd.Timestamp):
        return dttm.to_datetime64().astype(dttm_dtype)

    if isinstance(dttm, pd.DatetimeIndex):
        return dttm.values.astype(dttm_dtype)

    if isinstance(dttm, pd.core.arrays.DatetimeArray):
        return dttm._ndarray.astype(dttm_dtype)

    if isinstance(dttm, datetime.date):
        return pd.Timestamp(dttm).to_datetime64().astype(dttm_dtype)

    raise Exception(f"Unsupported type {type(dttm)}")


def as_dttm(dttm: DttmLike, from_dttm=False, to_dttm=False, assume_units=False) -> np.datetime64:
    if isinstance(dttm, str):
        dttm = parse_dttm(dttm, from_dttm=from_dttm, to_dttm=to_dttm)
    return _as_dtype(dttm, dtype_nanos) if not assume_units else dttm


def as_dttms(dttms: list[DttmLike] | np.ndarray):
    if isinstance(dttms, list) or not dttms.dtype == np.datetime64:
        return np.asarray([as_dttm(x) for x in dttms])
    return _as_dtype(dttms, dtype_nanos)


days_of_week_names = {
    "mon",
    "monday",
    "tue",
    "tues",
    "tuesday",
    "wed",
    "weds",
    "wednesday",
    "thu",
    "thur",
    "thurs",
    "thursday",
    "fri",
    "friday",
    "sat",
    "saturday",
    "sun",
    "sunday",
}

days_of_week = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def user_day_of_week(may_be_day):
    if may_be_day in days_of_week_names:
        return days_of_week[may_be_day[:3]]
    return -1


months_names = {
    "jan",
    "january",
    "feb",
    "february",
    "mar",
    "march",
    "apr",
    "april",
    "may",
    "june",
    "jun",
    "july",
    "jul",
    "august",
    "aug",
    "september",
    "sept",
    "sep",
    "october",
    "oct",
    "november",
    "nov",
    "december",
    "dec",
}

months_of_the_year = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
months_of_the_month_reversed = {v: k for k, v in months_of_the_year.items()}

month_letters = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}

month_letters_reversed = {v: k for k, v in month_letters.items()}


def contract_month_int(contract_month):
    m, y = contract_month.split("-")
    m = months_of_the_year[m.lower()]
    return (2000 + int(y)) * 100 + m


def user_month_of_year(may_be_month):
    if len(may_be_month) == 1:
        mu = may_be_month.upper()
        if mu in month_letters:
            return month_letters[mu]
    if may_be_month in months_names:
        return months_of_the_year[may_be_month[:3]]
    return -1


def user_year(year):
    if isinstance(year, str):
        year = int(year)

    if year > 1000:
        return year

    if year < 100:
        if year > 50:
            return 1900 + year
        else:
            return 2000 + year

    raise Exception(f"Unable to divine year [{year}]")


def _with_shift(dttm, shift, dtype, multiplier=1, to_dttm=False):
    if to_dttm:
        shift += 1
    if shift != 0:
        dttm += np.timedelta64(shift * multiplier, dtype)
    dttm = dttm.astype(dtype_days)
    if to_dttm:
        dttm -= a_day
    return dttm.astype(dtype_nanos)


def end_of_last_month(today_=..., grace_days=0):
    if today_ is ...:
        today_ = today()
    last_day = (today_ - grace_days * a_day).astype(dtype_months).astype(dtype_days) - a_day
    return as_dttm(last_day) + EOD


def convert_tz(dttms: np.ndarray, from_tz: str, to_tz="UTC"):
    if not (is_frame(dttms) or is_iterable(dttms)):
        return convert_tz([dttms], from_tz, to_tz)[0]

    dti = pd.DatetimeIndex(dttms, tz=from_tz)
    return dti.tz_convert(to_tz).tz_localize(None).values


_dttm_offset_pattern = re.compile(r"(.*)([-+])(\d+[a-zA-Z]{1,2})$")
_dttm_plustime_pattern = re.compile(r"(.*)([-+])(\d+:[\d:]+[ap]?m?|\d+[ap]m)$")
_dttm_periodplus_pattern = re.compile(r"^([tmqy])([-+]\d+)$")
_dttm_monthyear_pattern = re.compile(r"^([a-zA-Z]+)-?(\d+)$")


def parse_dttm(dttm: str, from_dttm=False, to_dttm=False, _now=..., _shift=0, tz=...) -> np.datetime64:
    dttm_lower = dttm.lower()

    if "@" in dttm:
        dttm, tz = dttm.split("@", 1)

    if tz is not ...:
        dttm = parse_dttm(dttm, from_dttm=from_dttm, to_dttm=to_dttm, _now=_now, _shift=_shift)
        return convert_tz(dttm, from_tz=tz)

    match dttm_lower:
        case "now":
            return now() if _now is ... else _now
        case "eod":
            shift = -1 if from_dttm else 0
            return as_dttm(today(_now=_now, _shift=shift) + EOD)
        case "sod":
            return as_dttm(today(_now=_now, _shift=-1) + EOD)
        case "today" | "t":
            return _with_shift(today(_now=_now), _shift, "D")
        case "yesterday" | "yd":
            return _with_shift(today(_now=_now) - a_day, _shift, "D")
        case "thismonth" | "m":
            month = today(_now=_now).astype(dtype_months)
            return _with_shift(month, _shift, "M", to_dttm=to_dttm)
        case "thisquarter" | "q":
            quarter = today(_now=_now).astype(dtype_months)
            quarter -= quarter.astype(int) % 3 * a_month
            return _with_shift(quarter, _shift, "M", 3, to_dttm=to_dttm)
        case "thisyear" | "y":
            year = today(_now=_now).astype(dtype_years)
            return _with_shift(year, _shift, "Y", to_dttm=to_dttm)

    day = user_day_of_week(dttm_lower)
    if day != -1:
        td = today(_now=_now, _shift=_shift)
        tday = (td.astype(int) + 3) % 7
        if to_dttm:
            return as_dttm(td + np.timedelta64((day - tday) % 7, "D"))
        else:
            return as_dttm(td - np.timedelta64((tday - day) % 7, "D"))

    month = user_month_of_year(dttm_lower)
    if month != -1:
        month = today(_now=_now).astype(dtype_years).astype(dtype_months) + a_month * (month - 1)
        return _with_shift(month, _shift, "M", to_dttm=to_dttm)

    for p in [_dttm_offset_pattern, _dttm_plustime_pattern]:
        if m := re.match(p, dttm):
            prefix = m[1]
            if ":" not in prefix:  # guard against dttm with tz offset
                prefix = parse_dttm(prefix, _now=_now, from_dttm=from_dttm, to_dttm=to_dttm)
                match m[2]:
                    case "+":
                        return as_dttm(prefix + dayify_period(parse_period(m[3])))
                    case "-":
                        return as_dttm(prefix - dayify_period(parse_period(m[3])))

    if m := re.match(_dttm_periodplus_pattern, dttm_lower):
        return parse_dttm(m[1], _now=_now, _shift=int(m[2]), from_dttm=from_dttm, to_dttm=to_dttm)

    if m := re.match(_dttm_monthyear_pattern, dttm_lower):
        month = user_month_of_year(m[1])
        if month != -1:
            year = user_year(m[2])
            month = as_dttm(pd.Timestamp(f"{months_of_the_month_reversed[month]}-{year}")).astype(dtype_months)
            return _with_shift(month, _shift, "M", to_dttm=to_dttm)

    if "-" in dttm:
        return as_dttm(pd.Timestamp(dttm))

    return parse_formatted_dttm(dttm)


def parse_formatted_dttm(dttm):
    match len(dttm):
        case 11:
            return as_dttm(datetime.datetime.strptime(dttm, "%Y%m%d_%H"))
        case 13:
            return as_dttm(datetime.datetime.strptime(dttm, "%Y%m%d_%H%M"))
        case 15:
            return as_dttm(datetime.datetime.strptime(dttm, "%Y%m%d_%H%M%S"))
        case 18:
            return as_dttm(datetime.datetime.strptime(dttm, "%Y%m%d_%H%M%S%f"))
        case 21:
            return as_dttm(datetime.datetime.strptime(dttm, "%Y%m%d_%H%M%S%f"))
        case 24:
            nanos = np.timedelta64(int(dttm[-3:]), "ns")
            return as_dttm(datetime.datetime.strptime(dttm[:-3], "%Y%m%d_%H%M%S%f")) + nanos

    raise SyntaxError(f"Unable to parse dttm [{dttm}]")


@dataclass
class Stamped:
    dttm: np.datetime64


@functools.cache
def _key_format_dttm(dttm):
    if dttm.dtype == dtype_days:
        return format_dt(dttm)
    else:
        return format_dttm(dttm)


@functools.cache
def _key_parse_dttm(dttm):
    return parse_formatted_dttm(dttm)


def _key_str(key: Any) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, np.datetime64):
        return _key_format_dttm(key)
    if is_primitive(key):
        return str(key)
    if is_iterable(key):
        return "__".join([_key_str(i) for i in key])
    raise Exception(f"Unsupported key type {type(key)}")


class Key:
    def __init__(self, *fields):
        self.fields = fields

    def __repr__(self):
        return _key_str(self.fields)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.fields == other.fields
        else:
            return False

    def __lt__(self, other):
        return self.__repr__() < other.__repr__()

    def __hash__(self):
        return hash(self.fields)

    def __getitem__(self, item):
        return self.fields[item]

    @property
    def name(self):
        name = ""
        for value in self.fields:
            name += f"_{value}"
        return name


class Keyed:
    @abstractmethod
    def key(self) -> Key:
        pass

    def __short_repr__(self):
        """special method for params/hashing - should uniquely identify the asset"""
        return str(self.key())

    def __repr__(self):
        return f"{self.__class__.__name__}[{self.__short_repr__()}]"

    @classmethod
    def is_key_field(cls, field) -> bool:
        return field in cls.get_key_fields()

    @staticmethod
    def safe_is_key_field(obj, field):
        try:
            return obj.is_key_field(field)
        except:  # noqa: E722
            return False

    @staticmethod
    def group_by_key(items, indexer):
        keys_to_keyed = {}
        keys_to_items = defaultdict(list)
        for item in items:
            keyed = indexer(item)
            key = keyed.key()
            keys_to_keyed[key] = keyed
            keys_to_items[key].append(item)
        return zip(keys_to_keyed.values(), keys_to_items.values())

    @classmethod
    @functools.cache
    def get_key_fields(cls, key_name: str = "key"):
        with AttributeTracker(cls) as t:
            t.got_fields.clear()
            getattr(t.obj, key_name)()

        return {k: None for k in t.got_fields.keys() if k != "key"}

    @staticmethod
    def __accessor__(obj):
        if isinstance(obj, str):
            return obj
        if isinstance(obj, Key):
            return str(obj)
        if isinstance(obj, Keyed):
            return str(obj.key())
        raise Exception(f"Can not key by type {type(obj)}")


class Keyable:
    def __init__(self, write_once=False, **kwargs):
        super().__init__(**kwargs)
        self.__write_once = write_once
        self.__aliased = {}

    def __setitem__(self, key: str | Key | Keyed, value):
        setattr(self, Keyed.__accessor__(key), value)

    def __setattr__(self, key, value):
        if not key.startswith("_"):
            self.__checkattr__(key, value)
        super().__setattr__(key, value)

    def __checkattr__(self, key, value):
        if self.__write_once and key in self.__dict__ and self.__dict__[key] is not ...:
            raise Exception(f"Write once collection, not allowed to overwrite value [{key}]")

    def alias(self, item: Any, key: str | Key | Keyed):
        self.__aliased[Keyed.__accessor__(key)] = item
        return item

    def __getitem__(self, key: str | Key | Keyed):
        key = Keyed.__accessor__(key)
        if key in self.__aliased:
            return self.__aliased[key]
        return getattr(self, key)

    def __contains__(self, key):
        key = Keyed.__accessor__(key)
        return key in self.__dict__ or key in self.__aliased

    def get(self, item, default_value=None):
        if item in self:
            return self[item]
        return default_value


class HasPath:
    def __init__(self, path=..., set_child_path=False, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.__parent__ = None
        self.__set_child_path__ = set_child_path

    @property
    def name(self):
        assert self.path is not ..., "path not set"
        return self.path.rsplit("/", maxsplit=1)[-1]

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if isinstance(value, HasPath) and self.__set_child_path__ and self.path is not ...:
            self._set_child_path(key, value)

    def _set_child_path(self, key, value):
        if not key.startswith("_") and isinstance(value, HasPath):
            path = f"{self.path}/{key}" if self.path else key
            if value.path is not ...:
                assert value.path == path, "HasPath should only have one public location (use '_' for reference)"
            else:
                value._set_path(path, self)

    def _set_path(self, path, parent):
        assert self.path is ..., "Path should be set once"
        self.path = path
        self.__parent__ = parent
        if self.__set_child_path__:
            for k, v in self.__dict__.items():
                self._set_child_path(k, v)

    def resolve_from_path(self, path: str):
        if path == self.path:
            return self
        ps = path.split("/", maxsplit=1)
        item = self.__getattribute__(ps[0])
        return item if len(ps) == 1 else item.resolve_from_path(ps[1])

    def __root_parent__(self):
        if self.__parent__ is None:
            return self
        else:
            return self.__parent__.__root_parent__()

    def __repr__(self):
        return f"{self.__class__.__name__}[{'...' if self.path is ... else self.path}]"


@njit()
def bytes_to_chars(digest, len_):
    r = [0] * len_
    for i in range(len(digest)):
        r[i % len_] += digest[i]
    return "".join([hash_chars[i % len(hash_chars)] for i in r])


def hash_collections(item, lib):
    if isinstance(item, (pd.DataFrame, pd.Series)):
        item.to_pickle(bts := systemio.BytesIO())
        bts.seek(0)
        lib.update(bts.getvalue())
    elif isinstance(item, pd.Index):
        hash_collections(item.values, lib)
        for n in item.names:
            lib.update(("_none_" if n is None else n).encode("utf-8"))
    elif isinstance(item, np.ndarray):
        if item.dtype == np.object_:
            item = item.astype(str)
        lib.update(item.tobytes())
    else:
        raise Exception(f"Unsupported type {type(item)}")


class AttributeTracker:
    """you can use this to the track the inner gets/sets on an object for testing or inspection purposes"""

    def __init__(self, cls, *args, include_hidden=False, **kwargs):
        self.cls = cls
        self.args = args
        self.kwargs = kwargs
        self.got_fields = {}
        self.set_fields = {}
        self.obj = None
        self.include_hidden = include_hidden

    def __enter__(outer_self):
        class _AttributeTracker(outer_self.cls):
            def __getattribute__(inner_self, name):
                result = super().__getattribute__(name)
                if outer_self.include_hidden or not name.startswith("__"):
                    gets = outer_self.got_fields.get(name)
                    if gets is None:
                        outer_self.got_fields[name] = gets = []
                    gets.append(super().__getattribute__(name))
                return result

            def __setattr__(inner_self, name, value):
                super().__setattr__(name, value)
                if outer_self.include_hidden or not name.startswith("__"):
                    sets = outer_self.set_fields.get(name)
                    if sets is None:
                        outer_self.set_fields[name] = sets = []
                    sets.append(value)

        try:
            instance = _AttributeTracker(*outer_self.args, **outer_self.kwargs)
        except TypeError as e:
            args = int(re.search(r"missing ([0-9]+) required", e.args[0]).group(1))
            instance = _AttributeTracker(*([None] * args))

        outer_self.obj = instance
        return outer_self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.obj = None


@dataclass
class ToDictDef:
    short_repr: bool = False
    frames: bool = False
    private: bool = False
    cls_names: bool = True
    dttm_format: str = ...
    none_format: str = ...


def _sanitise_dict_key(key):
    if isinstance(key, str) or isinstance(key, int):
        return key

    if hasattr(key, "name"):
        return key.name

    raise Exception(f"Unsupported key: {key}")


def _field_to_dict(item, ddef):
    if is_primitive(item):
        return item
    if item is None:
        return NoneResult
    if item is ...:
        return "..."
    if isinstance(item, np.datetime64):
        if ddef.dttm_format is ...:
            return {"_M8_": _key_format_dttm(item)}
        else:
            return format_dttm(item, ddef.dttm_format, enforce_nanos=False)
    if isinstance(item, np.timedelta64):
        return {"_m8_": format_period(item)}
    if isinstance(item, datetime.datetime):
        if ddef.dttm_format is ...:
            return {"__datetime__": _key_format_dttm(as_dttm(item))}
        else:
            return format_dttm(as_dttm(item), ddef.dttm_format, nanos=False)

    if isinstance(item, enum.Enum):
        if ddef.cls_names:
            return {item.__class__.__name__: item.value}
        else:
            return item.value

    if is_frame(item):
        if ddef.frames:
            if ddef.frames == "hash":
                hash_collections(item, lib := hashlib.md5())
                return bytes_to_chars(lib.digest(), len_=8)
            else:
                return item
        else:
            raise Exception(f"Unsupported field type (frames=False): {type(item)}")

    if hasattr(item, "__do_not_hash__"):
        raise Exception(f"Do not hash: {type(item)}")

    if hasattr(item, "__to_dict__"):
        return item.__to_dict__(_ddef=ddef)

    if isinstance(item, dict):
        if ddef.none_format == "__drop__":
            item = {k: v for k, v in item.items() if v is not None}
        return {
            _sanitise_dict_key(k): _field_to_dict(v, ddef)
            for k, v in item.items()
            if ddef.private or not isinstance(k, str) or not k.startswith("_")
        }

    if is_iterable(item):
        return [_field_to_dict(i, ddef) for i in item]

    if ddef.short_repr and hasattr(item, "__short_repr__"):
        if ddef.cls_names:
            return {item.__class__.__name__: item.__short_repr__()}
        else:
            return item.__short_repr__()

    try:
        obj = item.__dict__
        if "version" not in obj and hasattr(item.__class__, "version"):
            obj["version"] = getattr(item.__class__, "version")
        if ddef.cls_names:
            obj = {item.__class__.__name__: obj}
        return _field_to_dict(obj, ddef)
    except Exception as e:
        raise Exception(f"Unsupported field type: {type(item)}") from e


@functools.cache
def _parse_dict_period(dttm):
    return parse_period(dttm)


def _field_from_dict(item, field):
    if field is not None and hasattr(field.type, "__from_dict__"):
        return field.type.__from_dict__(item)
    if isinstance(item, dict):
        if len(item) == 1 and "_M8_" in item:
            return _key_parse_dttm(item["_M8_"])
        elif len(item) == 1 and "_m8_" in item:
            return _parse_dict_period(item["_m8_"])
        else:
            return {k: _field_from_dict(v, None) for k, v in item.items()}
    if is_iterable(item):
        return [_field_from_dict(x, None) for x in item]
    if isinstance(item, str):
        if item == NoneResult:
            return None
        if item == "...":
            return ...
    if item is ...:
        return ...
    assert is_primitive(item)
    return item


class ToDict:
    @staticmethod
    def convert(obj, _ddef=None, **kwargs):
        if _ddef is None:
            _ddef = ToDictDef(**kwargs)
        return _field_to_dict(obj, _ddef)

    @staticmethod
    def revert(obj):
        return _field_from_dict(obj, None)

    def __to_dict__(self, _ddef=None, **kwargs):
        if _ddef is None:
            _ddef = ToDictDef(**kwargs)
        obj = self.__dict__
        if _ddef.cls_names:
            obj = {self.__class__.__name__: obj}
        return ToDict.convert(obj, _ddef=_ddef)

    def __to_rest_dict__(self):
        return self.__to_dict__(cls_names=False, dttm_format=format_iso, none_format="__drop__")

    @classmethod
    def __from_dict__(cls, d, helpers=None) -> Self:
        if cls.__name__ in d:
            d = d[cls.__name__]
        fields = {f.name: f for f in dataclasses.fields(cls)} if dataclasses.is_dataclass(cls) else {}
        expected_kwargs = inspect.signature(cls.__init__).parameters
        kwargs = {}
        for k, v in d.items():
            if k in expected_kwargs:
                if isinstance(v, str) and v == NoneResult:
                    kwargs[k] = None
                elif helpers is not None and k in helpers:
                    kwargs[k] = helpers[k](v)
                else:
                    kwargs[k] = _field_from_dict(v, fields.get(k))
        return cls(**kwargs)

    @classmethod
    def __from_dicts__(cls, d) -> list[Self]:
        return [cls.__from_dict__(i) for i in d]


class kwargs_default:
    """
    provide a reach around for a value to default to an object property
    *** for use only with kwargs_expand/registered_function ***

    for example this:
    def my_func(b=kwargs_default()):
        foo(b)

    is equivalent to:
    def my_func(b=...):
        if b is ...:
            b = self.b
        foo(b)

    except that with kwargs_expand b=1 is treated the same as b=... where 1 is the default
    """

    def __init__(self, value=None, attr_name=...):
        self._attr_name = attr_name
        self._value = value

    def __call__(self, item, key):
        if self._value is not None:
            return self._value
        else:
            attr_name = key if self._attr_name is ... else self._attr_name
            return getattr(item, attr_name)

    @staticmethod
    def resolve(item, key, value, kwd):
        if isinstance(value, kwargs_default) or value is ...:
            return kwd(item, key)
        else:
            return value


def kwargs_expand(func, inner_func=...):
    """canonical kwargs to help lru_cache"""

    sig = inspect.signature(func.__wrapped__ if inner_func is ... else inner_func)
    kwargs_defaults = {k: v.default for k, v in sig.parameters.items() if isinstance(v.default, kwargs_default)}

    def _wrapper(self, *args, **kwargs):
        params = sig.bind(self, *args, **kwargs)
        params.apply_defaults()
        kwargs = params.arguments
        while "kwargs" in kwargs:
            kw = kwargs.pop("kwargs")
            kwargs.update(kw)

        for k, v in kwargs_defaults.items():
            kwargs[k] = kwargs_default.resolve(self, k, kwargs[k], v)
        return func(**kwargs)

    return _wrapper


def user_aliases(email: str):
    email = email.lower()
    name, surname = email.split("@", 1)[0].split(".", 1)
    return {
        name,
        surname,
        f"{name}.{surname}",
        name[0] + surname,
        name[0] + surname[0],
        name[:3],
        name[:4],
    }


def users_aliases(emails: Iterable[str]):
    aliases = {}
    for email in emails:
        for alias in user_aliases(email):
            aliases[alias] = email
    return aliases


class InstanceCache:
    def __init__(self, fcn=None, *, maxsize=None):
        self.maxsize = maxsize
        self.attr_name = None
        if fcn is not None:
            self._init_fcn(fcn)

    def _init_fcn(self, fcn):
        functools.update_wrapper(self, fcn)
        self.fcn = fcn

    def __call__(self, fcn):
        # if no args provided on init. Emulate functools.cache behaviour
        self._init_fcn(fcn)
        return self

    def __set_name__(self, owner, name):
        self.attr_name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        obj_ref = weakref.ref(obj)

        @functools.lru_cache(maxsize=self.maxsize)
        def cached(*args, **kwargs):
            # keep weakref to instance so it can get gc'ed
            instance = obj_ref()
            if instance is None:
                raise ReferenceError("Instance has been garbage collected. Must keep reference to parent object.")
            return MethodType(self.fcn, instance)(*args, **kwargs)

        # this is the magic. replace reference to instance in __dict__ so __get__ does not get called again
        obj.__dict__[self.attr_name] = cached
        return cached
