import numpy as np
import pandas as pd
import pandas.tseries.offsets as pd_offset
import pytest
from numpy.testing import assert_array_equal

from clio import dttms, BDOffset
from clio.clocks import Clock, WeekdayOfMonthOffset
from clio.dttms import weekdays


@pytest.mark.parametrize(
    "dttm, expected",
    [
        (np.datetime64("2024-03-15T15:00"), "20240315_15"),
        (np.datetime64("2024-03-15T15:30"), "20240315_1530"),
        (np.datetime64("2024-03-15T15:30:10"), "20240315_153010"),
        (np.datetime64("2024-03-15T15:30:10.012"), "20240315_153010012"),
        (np.datetime64("2024-03-15T15:30:10.012034"), "20240315_153010012034"),
        (np.datetime64("2024-03-15T15:30:10.012034056"), "20240315_153010012034056"),
    ],
)
def test_dttm_format(dttm: np.datetime64, expected: str):
    dttm = dttm.astype(dttms.dtype_nanos)
    assert dttms.format_dttm(dttm) == expected
    assert dttm == dttms.parse_dttm(expected)


def test_parse_dttm_special():
    now = dttms.parse_dttm("20230301_15")
    assert dttms.parse_dttm("now", _now=now) == now
    assert dttms.parse_dttm("now-1y", _now=now) == dttms.parse_dttm("20220301_15")
    assert dttms.parse_dttm("eod", _now=now) == dttms.parse_dttm("20230301_22")
    assert dttms.parse_dttm("eod", _now=now, from_dttm=True) == dttms.parse_dttm("20230228_22")
    assert dttms.parse_dttm("eod+1Q", _now=now) == dttms.parse_dttm("20230602_22")

    assert dttms.parse_dttm("today", _now=now, from_dttm=True) == dttms.as_date(now)
    assert dttms.parse_dttm("today", _now=now, to_dttm=True) == dttms.as_date(now)
    assert dttms.parse_dttm("yesterday", _now=now) == dttms.as_date(now) - dttms.a_day

    assert dttms.parse_dttm("mon", _now=now, from_dttm=True) == dttms.parse_date("20230227")
    assert dttms.parse_dttm("mon", _now=now, to_dttm=True) == dttms.parse_date("20230306")
    assert dttms.parse_dttm("tuesday", _now=now) == dttms.parse_date("20230228")
    assert dttms.parse_dttm("weds", _now=now) == dttms.parse_date("20230301")
    assert dttms.parse_dttm("thurs", _now=now) == dttms.parse_date("20230223")
    assert dttms.parse_dttm("thurs+1w", _now=now) == dttms.parse_date("20230302")
    assert dttms.parse_dttm("thurs+1w", _now=now, to_dttm=True) == dttms.parse_date("20230309")

    assert dttms.parse_dttm("jan", _now=now, from_dttm=True) == dttms.parse_date("20230101")
    assert dttms.parse_dttm("may", _now=now, to_dttm=True) == dttms.parse_date("20230531")

    assert dttms.parse_dttm("now-2h", _now=now) == dttms.parse_dttm("20230301_13")
    assert dttms.parse_dttm("now-2h+30m", _now=now) == dttms.parse_dttm("20230301_1330")
    assert dttms.parse_dttm("t-3", _now=now) == dttms.as_date(now) - 3 * dttms.a_day
    assert dttms.parse_dttm("t+9am", _now=now) == dttms.parse_dttm("20230301_09")
    assert dttms.parse_dttm("t+9:30", _now=now) == dttms.parse_dttm("20230301_0930")
    assert dttms.parse_dttm("t+2pm", _now=now) == dttms.parse_dttm("20230301_14")
    assert dttms.parse_dttm("t+2:30pm", _now=now) == dttms.parse_dttm("20230301_1430")

    assert dttms.parse_dttm("q", _now=now) == dttms.parse_date("20230101")
    assert dttms.parse_dttm("q", _now=now, to_dttm=True) == dttms.parse_date("20230331")
    assert dttms.parse_dttm("q+2", _now=now) == dttms.parse_date("20230701")
    assert dttms.parse_dttm("q+2", _now=now, to_dttm=True) == dttms.parse_date("20230930")

    assert dttms.parse_dttm("y", _now=now) == dttms.parse_date("20230101")
    assert dttms.parse_dttm("y-1", _now=now, to_dttm=True) == dttms.parse_date("20221231")

    assert dttms.parse_dttm("sod-2BD", _now=now) == dttms.parse_dttm("20230224_22")


def test_timezoned_dttms():
    assert dttms.parse_dttm("2025-06-17T03:50:50.000-04:00") == dttms.parse_dttm("20250617_075050")
    assert dttms.parse_dttm("2025-06-17T03:50:50.000+01:00") == dttms.parse_dttm("20250617_025050")


@pytest.mark.parametrize(
    "dttm, from_tz, to_tz, expected",
    [
        (
            dttms.parse_dttms("20240115_15", "20240315_15", "20240615_15"),
            "America/New_York",
            "UTC",
            dttms.parse_dttms("20240115_20", "20240315_19", "20240615_19"),
        ),
        (
            dttms.parse_dttms("20240115_15", "20240315_15", "20240615_15"),
            "America/New_York",
            "Europe/London",
            dttms.parse_dttms("20240115_20", "20240315_19", "20240615_20"),
        ),
    ],
)
def test_convert_tz(dttm, from_tz, to_tz, expected):
    assert_array_equal(dttms.convert_tz(dttm, from_tz, to_tz), expected)


@pytest.mark.parametrize(
    "tm, expected",
    [
        (dttms.parse_time("15:00"), "15:00"),
        (dttms.parse_time("15:03"), "15:03"),
        (dttms.parse_time("15:03:50"), "15:03:50"),
        (dttms.parse_time("15:03:50.001"), "15:03:50.001"),
        (dttms.parse_time("15:03:50.000001"), "15:03:50.000001"),
        (dttms.parse_time("15:03:50.000000001"), "15:03:50.000000001"),
        (np.timedelta64(101, "h"), "4d05:00"),
    ],
)
def test_friendly_time(tm, expected):
    assert dttms.format_friendly_time(tm) == expected


@pytest.mark.parametrize(
    "dttm, days, roll, output",
    [
        (dttms.parse_date("20240402"), 2, None, dttms.parse_date("20240404")),
        (dttms.parse_date("20240402"), 4, None, dttms.parse_date("20240408")),
        (dttms.parse_date("20240402"), -1, None, dttms.parse_date("20240401")),
        (dttms.parse_date("20240402"), -2, None, dttms.parse_date("20240329")),
        (dttms.parse_date("20240413"), 2, "forward", dttms.parse_date("20240417")),
        (dttms.parse_date("20240413"), 2, None, dttms.parse_date("20240416")),
        (dttms.parse_date("20240413"), -2, "backward", dttms.parse_date("20240410")),
        (dttms.parse_date("20240413"), -2, None, dttms.parse_date("20240411")),
    ],
)
def test_busdays(dttm, days, roll, output):
    assert dttms.plus_busdays(dttm, days=days, roll=roll) == output


def test_weekdays():
    assert_array_equal(
        weekdays(dttms.parse_dttms("20240405_12", "20240406_12", "20240407_12", "20240408_12", "20240409_12")),
        np.asarray([4, 5, 6, 0, 1]),
    )


def test_periods():
    assert dttms.parse_period(dttms.format_period(np.timedelta64(3, "D"))) == np.timedelta64(3, "D")
    assert dttms.parse_period(dttms.format_period(np.timedelta64(100, "ns"))) == np.timedelta64(100, "ns")
    assert dttms.parse_period(dttms.format_period(np.timedelta64(-5, "m"))) == np.timedelta64(-5, "m")
    assert dttms.parse_period("+12y") == np.timedelta64(12, "Y")


def test_to_trade_date():
    dttm = dttms.parse_dttms(
        "20210909_23",  # thursday after close
        "20210910_12",  # friday midday
        "20210910_2201",  # friday after close
        "20210911_12",  # sat
        "20210912_12",  # sun
        "20210913_12",  # mon
        "20210914_12",  # tues (holiday)
        "20210915_12",  # weds (holiday)
        "20210916_12",  # thurs
    )

    cal = np.busdaycalendar(weekmask="1111100", holidays=dttms.parse_dates("20210914", "20210915"))
    dts = dttms.to_trade_date(dttm, cal=cal)

    assert_array_equal(
        dts,
        dttms.parse_dates(
            "20210910",  # thursday after close -> friday
            "20210910",  # friday midday
            "20210913",  # friday after close -> monday
            "20210913",  # sat -> monday
            "20210913",  # sun -> monday
            "20210913",  # mon
            "20210916",  # tues (holiday) -> thurs
            "20210916",  # weds (holiday) -> thurs
            "20210916",  # thurs
        ),
    )


def test_bday_offset():
    bd3 = dttms.parse_period("3BD")
    dt = dttms.parse_date("20231213")  # weds

    assert dt + bd3 == dttms.parse_date("20231218")
    assert dt - bd3 == dttms.parse_date("20231208")

    dts = dttms.parse_dates("20231212", "20231213", "20231214")
    np.testing.assert_array_equal(dts + bd3, dttms.parse_dates("20231215", "20231218", "20231219"))
    np.testing.assert_array_equal(dts - bd3, dttms.parse_dates("20231207", "20231208", "20231211"))


def test_bday_vs_pd():
    holidays = dttms.parse_dates("20201127", "20201224", "20201225", "20210101", "20210118", "20210215")
    cal = np.busdaycalendar(weekmask="MonTueWedThuFri", holidays=holidays)
    dttm = Clock.daily("00:00", calendar=cal).sample(*dttms.parse_dates("20201101", "20210301"))

    for i in range(-5, 5):
        pandas = pd_offset.CustomBusinessDay(i, holidays=holidays)
        offset = BDOffset(i, holidays=holidays)

        pandas_shifted = pd.DatetimeIndex(dttm) + pandas
        shifted = dttm + offset
        np.testing.assert_array_equal(pandas_shifted.values, shifted)

        pandas_shifted = pd.DatetimeIndex(dttm) - pandas
        shifted = dttm - offset
        np.testing.assert_array_equal(pandas_shifted.values, shifted)


def test_weekday_of_month():
    holidays = dttms.parse_dates("20201127", "20201224", "20201225", "20210101", "20210118", "20210215")
    cal = np.busdaycalendar(weekmask="MonTueWedThuFri", holidays=holidays)
    dttm = Clock.daily("00:00", calendar=cal).sample(*dttms.parse_dates("20201101", "20210301"))

    for week in range(3):
        for weekday in range(5):
            pandas = pd_offset.WeekOfMonth(week=week, weekday=weekday)
            offset = WeekdayOfMonthOffset(week, weekday)
            assert str(offset) == f"w{week}d{weekday}"

            pandas_shifted = pd.DatetimeIndex(dttm) + pandas
            shifted = dttm + offset
            np.testing.assert_array_equal(pandas_shifted.values, shifted)

            pandas_shifted = pd.DatetimeIndex(dttm) - pandas
            shifted = dttm - offset
            np.testing.assert_array_equal(pandas_shifted.values, shifted)


def test_round_dttms():
    dttm = dttms.parse_dttm("20231218_113505")
    period = dttms.parse_period("30s")

    assert dttms.round_dttms(dttm, period, "floor") == dttms.parse_dttm("20231218_1135")
    assert dttms.round_dttms(dttm, period, "ceil") == dttms.parse_dttm("20231218_113530")
    assert dttms.round_dttms(dttm, period, "round") == dttms.parse_dttm("20231218_1135")


def test_period_hashable():
    periods = {BDOffset(1): 1, BDOffset(2): 2, BDOffset(1): 3}
    assert len(periods) == 2
    assert periods[BDOffset(1)] == 3


def test_futures_convention_suffix():
    assert dttms.futures_convention_suffix(dttms.parse_dttm("20221202_13")) == "Z22"
    assert dttms.futures_convention_suffix(pd.Timestamp(year=1995, month=3, day=6)) == "H95"
    assert dttms.futures_convention_suffix("20040909") == "U04"
