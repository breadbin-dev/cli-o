from typing import Literal
import numpy as np
import pandas as pd

import datetime

from clio import (
    dtype_nanos,
    dtype_days,
    format_dttm,
    format_dt,
    DttmLike,
    TimeLike,
    parse_dttm,
    parse_date,
    as_dttm,
    as_date,
    as_time,
    plus_busdays,
    _as_dtype,
    is_iterable,
    is_midnight,
    EOD,
    today,
    a_day,
    month_letters_reversed,
    NoneResult,
)
from clio import dtype_micros, dtype_minutes, dtype_hours  # noqa: F401, E501 useful to also expose through dttms
from clio import dtype_weeks, dtype_months, dtype_years  # noqa: F401, E501
from clio import as_dttms, now, format_period, parse_period, parse_time, format_iso, sub_busdays  # noqa: F401, E501
from clio import a_nano, a_second, a_minute, an_hour, a_month, a_year  # noqa: F401, E501
from clio import convert_tz, user_month_of_year, user_day_of_week, user_year, month_letters  # noqa: F401, E501

from clio.collections import recurse_collections

seconds_in_a_day = 60 * 60 * 24
epoc = np.datetime64("1970-01-01T00:00")


def to_trade_date(dt: DttmLike, cal=...) -> DttmLike:
    if isinstance(dt, str):
        dt = parse_date(dt)
    elif isinstance(dt, pd.Index):
        dt = dt.values

    if isinstance(dt, np.ndarray):
        dt = dt.copy()
        dt[as_time(dt) > EOD] += a_day
    elif isinstance(dt, np.datetime64) and as_time(dt) > EOD:
        dt += a_day

    days = _as_dtype(dt, dtype_days)
    return plus_busdays(days, days=0, cal=cal)


def trade_date_diff(from_dttm, to_dttm, busdaycal=...):
    from_dttm = to_trade_date(from_dttm)
    to_dttm = to_trade_date(to_dttm)
    if busdaycal is ...:
        return np.busday_count(from_dttm, to_dttm)
    else:
        return np.busday_count(from_dttm, to_dttm, busdaycal=busdaycal)


def weekdays(dttm: DttmLike):
    return (as_date(dttm).astype(int) + 3) % 7


def is_weekday(dttm: DttmLike):
    return weekdays(dttm) < 5


def is_sunday(dttm: DttmLike):
    return weekdays(dttm) == 6


def is_friday(dttm: DttmLike):
    return weekdays(dttm) == 4


def is_weekend(dttm: DttmLike):
    return ~is_weekday(dttm)


def monthdays(dttm: DttmLike):
    dttm = as_date(dttm)
    month_dt = dttm.astype(dtype_months)
    return (dttm - month_dt.astype(dtype_days) + 1).astype(int)


def is_eod(dttm: DttmLike, or_after=False) -> bool:
    if or_after:
        return as_time(dttm) >= EOD
    else:
        return as_time(dttm) == EOD


def from_dttm_as_date(from_dttm):
    from_date = as_date(as_dttm(from_dttm, from_dttm=True))
    if is_eod(from_dttm, or_after=True):
        # as left_inclusive = False
        from_date += a_day
    return from_date


def to_dttm_as_date(to_dttm):
    to_date = as_date(as_dttm(to_dttm, to_dttm=True))
    if not is_eod(to_dttm, or_after=True):
        # before eod, no eod value for you
        to_date -= a_day
    return to_date


def to_prev_close(dts: np.datetime64 | np.ndarray):
    dts = as_dttm(dts)
    assert np.all(is_midnight(dts))
    return (dts - a_day) + EOD


def to_eod(
    has_dts: np.datetime64 | np.ndarray | pd.DataFrame | pd.Series | pd.Timestamp | datetime.datetime | dict | list,
    minus_bdays=0,
):
    if isinstance(has_dts, dict):
        return {k: to_eod(v, minus_bdays=minus_bdays) for k, v in has_dts.items()}

    if is_iterable(has_dts):
        return [to_eod(i, minus_bdays=minus_bdays) for i in has_dts]

    if isinstance(has_dts, (pd.DataFrame, pd.Series)):
        has_dts = has_dts.copy()
        if has_dts.empty:
            has_dts.index.name = "dttm"
        else:
            has_dts.index = index_to_eod(has_dts.index, minus_bdays=minus_bdays)
        return has_dts

    if isinstance(has_dts, (pd.Timestamp, datetime.datetime)):
        return to_eod(as_dttm(has_dts), minus_bdays=minus_bdays)

    r = (as_date(has_dts) + EOD).astype(dtype_nanos)
    if minus_bdays != 0:
        r = sub_busdays(r, minus_bdays)
    return r


def to_sod(
    has_dts: np.datetime64 | np.ndarray | pd.DataFrame | pd.Series | pd.Timestamp | datetime.datetime | dict | list,
):
    return to_eod(has_dts) - a_day


def index_to_eod(idx: pd.Index, minus_bdays=0):
    return pd.Index(to_eod(idx.values, minus_bdays=minus_bdays), name="dttm")


def as_start_end_times(start_time: TimeLike, end_time: TimeLike) -> (np.timedelta64, np.timedelta64):
    start_time = as_time(start_time)
    end_time = as_time(end_time)
    if end_time < start_time:
        # when start is after end, assume you mean the previous day
        start_time -= a_day
    return start_time, end_time


def bus_date_range(from_dt, to_dt, step=1, cal=...):
    dt = from_dt.astype(dtype_days)
    while dt <= to_dt:
        yield dt
        dt = plus_busdays(dt, days=step, cal=cal)


def parse_dttms(*args):
    return np.asarray([parse_dttm(a) for a in args])


def parse_dates(*args):
    return np.asarray([parse_date(a) for a in args])


def format_any_dttm(*args, **kwargs):
    return format_dttm(*args, enforce_nanos=False, **kwargs)


def format_dttm_sql(dttm) -> str:
    return format_dttm(dttm, frmt="%Y-%m-%d %H:%M:%S.%f", enforce_nanos=False)


def format_dt_sql(dt) -> str:
    return format_dt(dt, frmt="%Y-%m-%d")


def format_dttm_iso(dttm, **kwargs):
    return format_dttm(dttm, frmt=format_iso, nanos=False, **kwargs)


def _div_mod(a, b):
    return a // b, a % b


def format_time(time: TimeLike, frmt="%H:%M:%S") -> str:
    dttm = today().astype(dtype_nanos) + as_time(time)
    return format_dttm(dttm, frmt=frmt, enforce_nanos=False)


def format_friendly_time(time: TimeLike) -> str:
    time = as_time(time)
    if time < 0:
        return f"-{format_friendly_time(-time)}"
    nanos = int(time.astype("timedelta64[ns]"))
    seconds, nanos = _div_mod(nanos, 1_000_000_000)
    minutes, seconds = _div_mod(seconds, 60)
    hours, minutes = _div_mod(minutes, 60)
    days, hours = _div_mod(hours, 24)
    days = f"{days}d" if days else ""

    if nanos:
        return f"{days}{hours:02}:{minutes:02}:{seconds:02}{format_friendly_nanos(nanos)}"
    if seconds:
        return f"{days}{hours:02}:{minutes:02}:{seconds:02}"
    return f"{days}{hours:02}:{minutes:02}"


def format_friendly_nanos(nanos):
    if nanos % 1_000 != 0:
        return f".{nanos:09}"

    if nanos % 1_000_000 != 0:
        return f".{nanos // 1_000:06}"

    if nanos % 1_000_000_000 != 0:
        return f".{nanos // 1_000_000:03}"

    return ""


def select(
    dttms: np.ndarray,
    from_dttm: DttmLike,
    to_dttm: DttmLike,
    left_inc=False,
    right_inc=True,
    left_extra=0,
    left_extra_enforced=True,
    right_extra=0,
    right_extra_enforced=True,
):
    """
    filter to from/to and optionally preserve a desired amount of over|under run
    :param dttms: array[np.datetime64]
    :param from_dttm: from (default exclusive)
    :param to_dttm: to (default inclusive)e
    :param left_inc: include the left value if == from_dttm
    :param right_inc: include the right value if == to_dttm
    :param left_extra: extra samples before from_dttm
    :param left_extra_enforced: throw if unable to find extra samples
    :param right_extra: extra samples after to_dttm
    :param right_extra_enforced: throw if unable to find extra samples
    """

    # sanity checks
    assert len(dttms) > 0, "empty list is not filterable"

    from_dttm = as_dttm(from_dttm)
    to_dttm = as_dttm(to_dttm)

    i = np.searchsorted(dttms, from_dttm, side="left" if left_inc else "right")
    if left_extra_enforced:
        assert i >= left_extra, "required extra left dttms"
    if i > left_extra:
        dttms = dttms[(i - left_extra) :]

    i = np.searchsorted(dttms, to_dttm, side="right" if right_inc else "left")
    if right_extra_enforced:
        assert i + right_extra <= len(dttms), "required extra right dttms"
    if i + right_extra < len(dttms):
        dttms = dttms[: (i + right_extra)]

    return dttms


def trim_to_span(item, from_dttm, to_dttm):
    if item is None or len(item) == 0 or (isinstance(item, str) and item == NoneResult):
        return item

    if isinstance(item, np.ndarray):
        if np.issubdtype(item.dtype, np.datetime64):
            item = item[(item > from_dttm) & (item <= to_dttm)]
    else:
        if type(item.index) is not pd.core.indexes.multi.MultiIndex:
            item = item[(item.index > from_dttm) & (item.index <= to_dttm)]
        else:
            item.sort_index(inplace=True)
            item = item.loc[pd.IndexSlice[:, pd.to_datetime(from_dttm) : pd.to_datetime(to_dttm)], :]
    return item


def trim_collection_to_span(collection, from_dttm, to_dttm):
    def _trim(x):
        return trim_to_span(x, from_dttm, to_dttm)

    return recurse_collections(collection, map_=_trim)


def to_daily(data: pd.DataFrame | pd.Series | np.ndarray):
    if len(data) == 0:
        return data

    if isinstance(data, np.ndarray):
        return as_date(data)
    elif isinstance(data, pd.DataFrame):
        return pd.DataFrame(data=data.values, index=as_date(data.index.values), columns=data.columns)
    elif isinstance(data, pd.Series):
        return pd.Series(data=data.values, index=as_date(data.index.values))
    else:
        raise Exception(f"Unsupported type {type(data)}")


def drop_trade_dates(data, days, index=...):
    return drop_dates(data, days, trade_dates=True, index=index)


def drop_dates(data, days, trade_dates=False, index=...):
    if len(days) == 0 or len(data) == 0:
        return data
    return data[is_not_dates(data, days, trade_dates=trade_dates, index=index)]


def is_not_trade_dates(data, days, index=...):
    return is_not_dates(data, days, trade_dates=True, index=index)


def is_not_dates(data, days, trade_dates=False, index=...):
    if index is ...:
        if isinstance(data, (pd.DataFrame, pd.Series)):
            index = data.index.values
        elif isinstance(data, pd.Index):
            index = data.values
        else:
            index = data

    if trade_dates:
        dates = to_trade_date(index)
    else:
        dates = index.astype(dtype_days)

    return np.in1d(dates, days, invert=True)


def round_dttms(dttm, period, direction: Literal["ceil", "floor", "round"] = "floor"):
    assert dttm.dtype == dtype_nanos
    period = period.astype("<m8[ns]").astype(int)
    result = dttm.astype(int) / period
    if direction == "ceil":
        result = np.ceil(result)
    elif direction == "floor":
        result = np.floor(result)
    elif direction == "round":
        result = np.round(result)
    else:
        raise Exception(f"Unsupported direction {direction}")
    return (result * period).astype(dtype_nanos)


def is_month_end(dttm):
    return np.asarray([pd.Timestamp(d).is_month_end for d in dttm])


def max_dttm(*dttms: DttmLike | None):
    """gives max dttm, filtering None, preserves special strings"""
    dttms = {as_dttm(d): d for d in dttms if d is not None}
    if not dttms:
        return None
    return dttms[max(dttms.keys())]


def min_dttm(*dttms: DttmLike | None):
    """gives min dttm, filtering None, preserves special strings"""
    dttms = {as_dttm(d): d for d in dttms if d is not None}
    if not dttms:
        return None
    return dttms[min(dttms.keys())]


def futures_convention_suffix(dttm: DttmLike):
    """convert a date into 2d futures suffix e.g. 12-Dec-2022 -> Z22"""
    if isinstance(dttm, str):
        dttm = as_date(dttm)
    else:
        dttm = as_dttm(dttm)
    month = to_months(dttm)
    year = to_years(dttm)
    return f"{month_letters_reversed[month]}{year % 100:02d}"


def from_unix(unix_dttm: float) -> np.datetime64:
    return np.datetime64(int(unix_dttm * 1e9), "ns")


def add_term(dttm, term):
    delta = parse_period(term)
    if delta.dtype == a_year.dtype:
        return as_date(dttm + pd.DateOffset(years=delta.astype(int)))
    elif delta.dtype == a_month.dtype:
        return as_date(dttm + pd.DateOffset(months=delta.astype(int)))
    else:
        return dttm + delta


def to_months(dttm: DttmLike):
    return dttm.astype(dtype_months).astype(int) % 12 + 1


def to_years(dttm: DttmLike):
    return dttm.astype(dtype_years).astype(int) + 1970


def parse_schedule_dttms(from_dttm: DttmLike, to_dttm: DttmLike, now_dttm=...):
    """special handling for support rota away dttms"""
    if isinstance(from_dttm, str):
        if from_dttm.endswith("PM") or from_dttm.endswith("AM"):
            if not ("+" in from_dttm or ":" in from_dttm or from_dttm.count("-") == 1):
                if now_dttm is ...:
                    now_dttm = now()

                am_pm = from_dttm[-2:]
                date = parse_dttm(from_dttm[:-2], _now=now_dttm, to_dttm=True)
                if am_pm == "AM":
                    from_dttm = to_eod(date) - a_day
                    if to_dttm is ...:
                        to_dttm = date + parse_time("12:00")
                else:
                    from_dttm = date + parse_time("12:00")
                    if to_dttm is ...:
                        to_dttm = to_eod(date)

                if from_dttm < now_dttm:
                    from_dttm += 7 * a_day
                    to_dttm += 7 * a_day

                return from_dttm, to_dttm
    return from_dttm, to_dttm


def is_on_hour(dttm: np.datetime64) -> bool:
    return dttm == dttm.astype(dtype_hours)
