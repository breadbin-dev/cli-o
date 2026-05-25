import functools
from abc import abstractmethod
from typing import Tuple

import numpy as np
import pandas as pd

from clio import TimeLike, arrays, BDOffset, dttms, ToDict
from clio.arrays import is_sorted, asof_align, merge_series, union_align, drop_consecutive_duplicates
from clio.dttms import (
    a_day,
    parse_time,
    parse_period,
    format_period,
    select,
    as_date,
    as_time,
    convert_tz,
    dtype_years,
    dtype_months,
    dtype_nanos,
    dtype_days,
    format_friendly_time,
    to_trade_date,
    sub_busdays,
    plus_busdays,
)
from clio.expr import Expr, DttmContext
from clio.hashing import const_hash


class Clock(Expr, ToDict):
    def __init__(self, time_of_day=None):
        if time_of_day is not None:
            self._time_of_day_str = time_of_day if isinstance(time_of_day, str) else format_friendly_time(time_of_day)
            self.time_of_day = parse_time(time_of_day)
        else:
            self._time_of_day_str = None
            self.time_of_day = time_of_day

    @staticmethod
    @functools.cache
    def periodic(period: str, calendar=..., session=None):
        return PeriodicClock(period, calendar=calendar, session=session)

    @staticmethod
    @functools.cache
    def daily(time_of_day: str, tz: str = "UTC", calendar=..., start_date=None):
        return DailyClock(time_of_day, tz=tz, calendar=calendar, start_date=start_date)

    @staticmethod
    @functools.cache
    def weekday_of_month(week: int, weekday: int, time_of_day="EOD"):
        return WeekDayOfMonth(week, weekday, time_of_day=time_of_day)

    @staticmethod
    @functools.cache
    def daily_eod(calendar=..., start_date=None):
        return DailyClock("EOD", calendar=calendar, start_date=start_date)

    @staticmethod
    @functools.cache
    def monthly(day_of_month=-1, time_of_day="EOD", month_count=1):
        return MonthlyClock(day_of_month, time_of_day=time_of_day, month_count=month_count)

    @staticmethod
    @functools.cache
    def quarterly(day_of_month=-1, time_of_day="EOD"):
        return MonthlyClock(day_of_month, time_of_day=time_of_day, month_count=3)

    @staticmethod
    @functools.cache
    def annual(day_of_month=-1, time_of_day="EOD", year_count=1, year_offset=0):
        return AnnualClock(day_of_month, time_of_day=time_of_day, year_count=year_count, year_offset=year_offset)

    @staticmethod
    def from_hours(hours, period="5m", calendar=...):
        return Clock.periodic(period, calendar=calendar, session=Session.from_config_hours(hours, calendar=calendar))

    @staticmethod
    def as_chunks(dttms):
        if len(dttms) == 0:
            return []
        else:
            return list(zip(dttms[:-1], dttms[1:]))

    @staticmethod
    def first_by_day(clocks):
        return FirstByDayClock(clocks)

    @staticmethod
    def last_by_day(clocks):
        return LastByDayClock(clocks)

    @abstractmethod
    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        """
        Generate dttms between to points
        :param from_dttm: from (default exclusive)
        :param to_dttm: to (default inclusive)
        :param left_inc: include the left value if == from_dttm
        :param right_inc: include the right value if == to_dttm
        :param left_extra: extra samples before from_dttm
        :param right_extra: extra samples after to_dttm
        """
        pass

    def outer_sample(self, from_dttm, to_dttm):
        # outer sample inclusive of both from_dttm, to_dttm
        return self.sample(from_dttm, to_dttm, right_inc=False, left_extra=1, right_extra=1)

    @abstractmethod
    def __short_repr__(self):
        """special method for __repr__ and also hashing - should uniquely identify the clock"""
        pass

    def __repr__(self):
        return f"Clock[{self.__short_repr__()}]"

    def __to_dict__(self, **kwargs):
        return {"Clock": self.__short_repr__()}

    def execute(self, ctx: DttmContext):
        return self.sample(ctx.from_dttm, ctx.to_dttm)

    @functools.cache
    def sample_chunks(self, from_dttm, to_dttm, as_of_dttm, earliest_dttm=None, latest_dttm=None, intraday=False):
        dttms = self.outer_sample(from_dttm, to_dttm)
        assert len(dttms) >= 2, "at least 2 dttms needed to chunk"

        if earliest_dttm is not None and dttms[0] < earliest_dttm:
            dttms[0] = earliest_dttm

        if latest_dttm is not None and dttms[-1] > latest_dttm:
            dttms[-1] = latest_dttm

        if dttms[-1] > as_of_dttm:
            assert self.time_of_day is not None

            last_sample = as_date(as_of_dttm) + self.time_of_day
            if last_sample > as_of_dttm:
                if intraday:
                    last_sample = as_of_dttm
                else:
                    last_sample -= a_day

            if last_sample == dttms[-2]:
                if len(dttms) == 2:
                    # this is the only case you'd expect to be empty
                    # (when you haven't ticked yet at the start of a chunk)
                    dttms = []
                else:
                    dttms = dttms[:-1]
            else:
                dttms[-1] = last_sample
                assert dttms[-1] > dttms[-2]

        return Clock.as_chunks(dttms)

    def resample_index(self, idx: pd.Index | pd.Series, cal=None, from_dttm=..., to_dttm=...):
        if idx.empty:
            return idx
        if from_dttm is ...:
            from_dttm = idx[0]

        right_inc = True
        right_extra = 0
        if to_dttm is ...:
            to_dttm = idx[-1]  # as we're just picking last dttm, allow step right
            right_inc = False
            right_extra = 1

        dttms = self.sample(from_dttm, to_dttm, left_inc=True, right_inc=right_inc, right_extra=right_extra)
        if cal is not None:
            dttms = dttms[np.is_busday(to_trade_date(dttms), busdaycal=cal)]
        return dttms

    def resample(self, data: pd.DataFrame | pd.Series, missing=..., cal=None, from_dttm=..., to_dttm=...):
        dttms = self.resample_index(data.index, cal=cal, from_dttm=from_dttm, to_dttm=to_dttm)
        return asof_align(data, pd.Index(data=dttms, name="dttm"), missing=missing)

    def next(self, dttms):
        samples = self.sample(dttms[0], dttms[-1], right_extra=1)
        return samples[np.searchsorted(samples, dttms)]

    def previous(self, dttms):
        samples = self.sample(dttms[0], dttms[-1], left_extra=1)
        return samples[np.searchsorted(samples, dttms) - 1]

    def __hash__(self):
        """we need this for the lru_cache only"""
        return hash(self.__short_repr__())

    def __eq__(self, other) -> bool:
        return self.__short_repr__() == other.__short_repr__()


def open_close_to_bool(open, close):
    open = pd.Series(data=True, index=open)
    close = pd.Series(data=False, index=close)
    return merge_series(open, close)


class Session:
    @staticmethod
    def fixed(
        open: TimeLike,
        close: TimeLike,
        tz: str = "UTC",
        open_tz: str = ...,
        close_tz: str = ...,
        calendar=...,
        open_calendar=...,
        close_calendar=...,
        left_inc=False,
        right_inc=True,
    ):
        if open_calendar is ... and calendar is not ...:
            open_calendar = calendar
        if close_calendar is ... and calendar is not ...:
            close_calendar = calendar
        if close_calendar is open_calendar is ...:
            close_calendar, open_calendar = calendar, calendar
        if close_tz is ...:
            close_tz = tz
        if open_tz is ...:
            open_tz = tz
        return Session(
            Clock.daily(open, tz=open_tz, calendar=open_calendar),
            Clock.daily(close, tz=close_tz, calendar=close_calendar),
            left_inc=left_inc,
            right_inc=right_inc,
        )

    @staticmethod
    def from_config_hours(hours, calendar=..., left_inc=False, right_inc=True):
        kwargs = dict(left_inc=left_inc, right_inc=right_inc)
        if "intersect" in hours:
            sessions = [Session.from_config_hours(h, **kwargs) for h in hours["intersect"].values()]
            return Session.inner(*sessions)

        if "union" in hours:
            sessions = [Session.from_config_hours(h, **kwargs) for h in hours["union"].values()]
            return Session.outer(*sessions)

        if "disjoint_union" in hours:
            sessions = [Session.from_config_hours(h, **kwargs) for h in hours["disjoint_union"].values()]
            return Session.union(*sessions)

        open_tz = hours.get("start_tz", hours.get("tz"))
        close_tz = hours.get("end_tz", hours.get("tz"))

        assert open_tz is not None and close_tz is not None, "tz not specified correctly"

        return Session.fixed(
            hours["start"], hours["end"], open_tz=open_tz, close_tz=close_tz, calendar=calendar, **kwargs
        )

    @staticmethod
    def inner(*sessions):
        opens = [s.open for s in sessions]
        closes = [s.close for s in sessions]
        return Session(LastByDayClock(opens), FirstByDayClock(closes))

    @staticmethod
    def outer(*sessions):
        opens = [s.open for s in sessions]
        closes = [s.close for s in sessions]
        return Session(FirstByDayClock(opens), LastByDayClock(closes))

    @staticmethod
    def union(*sessions):
        opens = [s.open for s in sessions]
        closes = [s.close for s in sessions]
        return Session(UnionClock(opens), UnionClock(closes))

    def __init__(self, open: Clock, close: Clock, left_inc=False, right_inc=True):
        self.open = open
        self.close = close
        self.left_inc = left_inc
        self.right_inc = right_inc

    def __short_repr__(self):
        return f"{self.open.__short_repr__()} -> {self.close.__short_repr__()}"

    def __repr__(self):
        return f"Session[{self.__short_repr__()}]"

    def sample(self, from_dttm, to_dttm) -> Tuple[np.ndarray, np.ndarray]:
        """
        get the open and close times for any sessions within the range including the previous/next sessions
        """
        return self._sample(self.open, self.close, from_dttm, to_dttm)

    def _sample(self, open, close, from_dttm, to_dttm) -> Tuple[np.ndarray, np.ndarray]:
        open = open.sample(from_dttm, to_dttm, left_extra=1)
        close = close.sample(open[0], open[-1], right_inc=False, right_extra=1)
        assert len(open) == len(close), "every open session must close"
        assert np.all(open < close), "every open session must be before close"
        assert np.all(close[:-1] <= open[1:]), "every open session should not be before subsequent close"

        if self.left_inc:
            in_range = (close >= from_dttm) & (open <= to_dttm)
        else:
            in_range = (close > from_dttm) & (open < to_dttm)
        return open[in_range], close[in_range]

    def sample_out_of_session(self, from_dttm, to_dttm) -> Tuple[np.ndarray, np.ndarray]:
        """
        get the open and close times for any sessions within the range including the previous/next sessions
        """
        return self._sample(self.close, self.open, from_dttm, to_dttm)

    def contains(self, dttms, from_dttm=..., to_dttm=...) -> np.ndarray:
        """
        check which dttms are within the sessions (left exclusive, right inclusive)
        """
        assert is_sorted(dttms), "dttms must be sorted"
        if from_dttm is ...:
            from_dttm = dttms[0]
        if to_dttm is ...:
            to_dttm = dttms[-1]
        open_, close_ = self.sample(from_dttm, to_dttm)
        return within_open_close(dttms, open_, close_, left_inc=self.left_inc, right_inc=self.right_inc)

    def as_open_close_bool(self, from_dttm, to_dttm):
        o, c = self.sample(from_dttm, to_dttm)
        return open_close_to_bool(o, c)

    def constrain(self, open_close, session=...):
        if open_close is None or open_close.empty:
            return open_close

        if session is ...:
            session = self.as_open_close_bool(open_close.index[0], open_close.index[-1])

        session, open_close = union_align(session, open_close)
        return drop_consecutive_duplicates(session & open_close)

    def __contains__(self, item: dttms.DttmLike):
        np_item = np.atleast_1d(item)
        contains = self.contains(np_item)
        return contains[0]


def within_open_close(dttms, open, close, left_inc=False, right_inc=True):
    if len(open) == 0:
        return np.full(dttms.shape, False)

    idx = np.searchsorted(open, dttms, side="right" if left_inc else "left") - 1

    if right_inc:
        return (idx != -1) & (dttms <= close[idx])
    else:
        return (idx != -1) & (dttms < close[idx])


class MonthlyClock(Clock):
    def __init__(self, day_of_month=-1, time_of_day="EOD", month_count=1):
        """
        Clock that fires once a month
        :param day_of_month: day of month 1 is 1st (-1 is last day of month)
        :param time_of_day: time of day
        :month_count: how many months in each chunk (3 for quarterly)
        """
        super().__init__(time_of_day)
        self.day_of_month = day_of_month
        self.month_count = month_count

    def __short_repr__(self):
        suffix = "" if self.month_count == 1 else f"_{self.month_count}"
        return f"Monthly_{self.day_of_month}_{self._time_of_day_str}{suffix}"

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        # given the day offset & time of day, widen range of interest (filtered later)
        lookleft = 31 * self.month_count * (left_extra + 1) + 1
        from_month = (from_dttm - lookleft * a_day).astype(dtype_months)
        lookright = 31 * self.month_count * (right_extra + 1) + 1
        to_month = (to_dttm + lookright * a_day).astype(dtype_months)

        months = [from_month + i for i in range(int(to_month - from_month) + 1)]
        if self.month_count != 1:
            months = [m for m in months if m.astype(int) % self.month_count == 0]

        day_offset = self.day_of_month if self.day_of_month < 0 else self.day_of_month - 1
        dttms = np.asarray([m.astype(dtype_nanos) + (a_day * day_offset) + self.time_of_day for m in months])

        return select(
            dttms,
            from_dttm,
            to_dttm,
            left_inc=left_inc,
            right_inc=right_inc,
            left_extra=left_extra,
            right_extra=right_extra,
        )


class WeekDayOfMonth(Clock):
    def __init__(self, week, weekday, time_of_day="EOD", month_count=1):
        """
        Clock that fires once a month
        :param week: week of month (0-4)
        :param weekday: day of week (0-6)
        :time_of_day: the time of day
        :month_count: how many months in each chunk (3 for quarterly)
        """
        super().__init__(time_of_day)
        self._week = week
        self._weekday = weekday
        self._months = Clock.monthly(1, time_of_day="00:00", month_count=month_count)

    def __short_repr__(self):
        return f"WeekDayOfMonth_{self._week}_{self._weekday}"

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        month_1st = (
            self._months.sample(
                from_dttm - 32 * a_day, to_dttm + 32 * a_day, left_extra=left_extra + 1, right_extra=right_extra + 1
            )
            .astype(dtype_days)
            .astype(int)
        )

        result = month_1st - ((month_1st + 3) % 7)  # monday
        result += self._weekday  # target day
        result[result < month_1st] += 7  # handle month boundary
        result += 7 * self._week  # target week

        result = result.astype(dtype_days).astype(dtype_nanos)
        result += self.time_of_day

        return select(
            result,
            from_dttm,
            to_dttm,
            left_inc=left_inc,
            right_inc=right_inc,
            left_extra=left_extra,
            right_extra=right_extra,
        )


class PeriodicClock(Clock):
    def __init__(self, period, calendar=..., session=None):
        super().__init__()
        self.period = parse_period(period)
        self.calendar = np.busdaycalendar() if calendar is ... else calendar
        self.session = session

    def _from_dttm(self, from_dttm, left_extra):
        from_dttm -= as_time(from_dttm) % self.period
        from_dttm -= self.period * left_extra
        if self.session is not None:
            from_dttm = sub_busdays(from_dttm)
        if self.calendar is not None:
            from_dttm = sub_busdays(from_dttm, cal=self.calendar)
        return from_dttm

    def _to_dttm(self, to_dttm, right_extra):
        to_dttm -= as_time(to_dttm) % self.period
        to_dttm += self.period * (1 + right_extra)
        if self.session is not None:
            to_dttm = plus_busdays(to_dttm)
        if self.calendar is not None:
            to_dttm = plus_busdays(to_dttm, cal=self.calendar)
        return to_dttm

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        dttms = np.arange(
            self._from_dttm(from_dttm, left_extra), self._to_dttm(to_dttm, right_extra), self.period, dtype=dtype_nanos
        )

        if self.session is not None:
            dttms = dttms[self.session.contains(dttms)]

        if self.calendar is not None:
            dttms = dttms[np.is_busday(as_date(dttms), busdaycal=self.calendar)]

        return select(
            dttms,
            from_dttm,
            to_dttm,
            left_inc=left_inc,
            right_inc=right_inc,
            left_extra=left_extra,
            right_extra=right_extra,
        )

    def __short_repr__(self):
        if self.session is None:
            return format_period(self.period)
        else:
            return f"{format_period(self.period)}__{self.session.__short_repr__()}"


class DailyClock(Clock):
    def __init__(self, time_of_day, tz="UTC", start_date=None, calendar=...):
        super().__init__(time_of_day)
        self.tz = tz
        self.start_date = start_date
        self.calendar = np.busdaycalendar() if calendar is ... else calendar

    def __short_repr__(self):
        suffix = f"_{self.tz}" if self.tz != "UTC" else ""
        return f"Daily_{self._time_of_day_str}{suffix}"

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        from_dt = as_date(from_dttm) - (left_extra + 4) * a_day
        to_dt = as_date(to_dttm) + (right_extra + 4) * a_day
        dates = np.arange(np.datetime64(from_dt), np.datetime64(to_dt), dtype=dtype_days).astype(dtype_nanos)
        dttm = dates + self.time_of_day

        if self.tz != "UTC":
            if self.tz.startswith("America") and self.time_of_day <= dttms.parse_time("03:00"):
                # Daylight Savings, this is safe because sunday not a business day
                dttm = dttm[~dttms.is_sunday(dttm)]
            dttm = convert_tz(dttm, self.tz)

        if self.calendar is not None:
            dttm = dttm[
                np.is_busday(
                    dttms.to_trade_date(dttm, cal=np.busdaycalendar("1111111")),
                    busdaycal=self.calendar,
                )
            ]

        if self.start_date is not None:
            dttm = dttm[dttm > self.start_date]

        return select(
            dttm,
            from_dttm,
            to_dttm,
            left_inc=left_inc,
            right_inc=right_inc,
            left_extra=left_extra,
            right_extra=right_extra,
        )


class AggregateClock(Clock):
    def __init__(self, clocks):
        super().__init__()
        self.clocks = clocks

    def __short_repr__(self):
        return ", ".join([c.__short_repr__() for c in self.clocks])

    def _pad_from_dttm(self, from_dttm):
        return from_dttm

    def _pad_to_dttm(self, to_dttm):
        return to_dttm

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        result = None
        for clock in self.clocks:
            r = clock.sample(
                self._pad_from_dttm(from_dttm),
                self._pad_to_dttm(to_dttm),
                left_inc=left_inc,
                right_inc=right_inc,
                left_extra=left_extra,
                right_extra=right_extra,
            )
            if result is None:
                result = r
            else:
                result = self._aggregate(result, r)

        overrun = sum(result > to_dttm if right_inc else result >= to_dttm)
        if overrun > right_extra:
            result = result[: -(overrun - right_extra)]

        underrun = sum(result < from_dttm if left_inc else result <= from_dttm)
        if underrun > left_extra:
            result = result[(underrun - left_extra) :]

        return result

    @abstractmethod
    def _aggregate(self, a, b):
        pass


class UnionClock(AggregateClock):
    def _aggregate(self, a, b):
        return np.union1d(a, b)


class FirstByDayClock(AggregateClock):
    def _pad_from_dttm(self, from_dttm):
        return dttms.to_sod(from_dttm)

    def _aggregate(self, a, b):
        return arrays.combine_by_index(a, as_date(a), b, as_date(b), arrays.min_)


class LastByDayClock(AggregateClock):
    def _pad_to_dttm(self, to_dttm):
        return dttms.to_eod(to_dttm)

    def _aggregate(self, a, b):
        return arrays.combine_by_index(a, as_date(a), b, as_date(b), arrays.max_)


class AnnualClock(Clock):
    def __init__(self, day_of_year=-1, time_of_day="EOD", year_count=1, year_offset=0):
        """
        Clock that fires once a year
        :param day_of_year: day of year 1 is 1st (-1 is last day of year)
        :param time_of_day: time of day
        :year_count: how many years in each chunk
        """
        super().__init__(time_of_day)
        self.day_of_year = day_of_year
        self.year_count = year_count
        self.year_offset = year_offset

    def __short_repr__(self):
        suffix = "" if self.year_count == 1 else f"_{self.year_count}"
        return f"Annual_{self.day_of_year}_{self._time_of_day_str}{suffix}"

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        # given the day offset & time of day, widen range of interest (filtered later)
        lookleft = 366 * self.year_count * (left_extra + 1) + 1
        from_year = (from_dttm - lookleft * a_day).astype(dtype_years)
        lookright = 366 * self.year_count * (right_extra + 1) + 1
        to_year = (to_dttm + lookright * a_day).astype(dtype_years)

        years = [from_year + i for i in range(int(to_year - from_year) + 1)]
        if self.year_count != 1:
            years = [y for y in years if y.astype(int) % self.year_count == self.year_offset]

        day_offset = self.day_of_year if self.day_of_year < 0 else self.day_of_year - 1
        dttms = np.asarray([y.astype(dtype_nanos) + (a_day * day_offset) + self.time_of_day for y in years])

        return select(
            dttms,
            from_dttm,
            to_dttm,
            left_inc=left_inc,
            right_inc=right_inc,
            left_extra=left_extra,
            right_extra=right_extra,
        )


class AdhocClock(Clock):
    def __init__(self, dttms):
        super().__init__()
        self._dttms = dttms
        self.dhash = const_hash(dttms)

    def __short_repr__(self):
        return f"Adhoc-{self.dhash}"

    def sample(self, from_dttm, to_dttm, left_inc=False, right_inc=True, left_extra=0, right_extra=0):
        return select(
            self._dttms,
            from_dttm,
            to_dttm,
            left_inc=left_inc,
            right_inc=right_inc,
            left_extra=left_extra,
            right_extra=right_extra,
            left_extra_enforced=False,
            right_extra_enforced=False,
        )


class WeekdayOfMonthOffset(BDOffset):
    def __init__(self, week: int, weekday: int, time_of_day="00:00"):
        super().__init__(0)
        self._clock = Clock.weekday_of_month(week, weekday, time_of_day)

    def __radd__(self, other: np.ndarray) -> np.ndarray:
        from_dttm = dttms.as_dttm(other[0])
        to_dttm = dttms.as_dttm(other[-1])
        dttm = self._clock.sample(from_dttm, to_dttm, left_inc=True, right_inc=True, right_extra=1)
        return dttm[np.searchsorted(dttm, other, side="right")]

    def __rsub__(self, other: np.ndarray) -> np.ndarray:
        from_dttm = dttms.as_dttm(other[0])
        to_dttm = dttms.as_dttm(other[-1])
        dttm = self._clock.sample(from_dttm, to_dttm, left_inc=True, right_inc=True, left_extra=1)
        return dttm[np.searchsorted(dttm, other, side="left") - 1]

    def __repr__(self):
        return f"w{self._clock._week}d{self._clock._weekday}"

    @property
    def dtype(self):
        return "weekday_of_month"
