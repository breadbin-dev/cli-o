import pytest
import numpy as np
import pandas as pd

from numpy.testing import assert_array_equal

from clio import dttms, clocks
from clio.clocks import DailyClock, Session, Clock
from clio.dttms import parse_dttms


@pytest.mark.parametrize(
    "clock, from_dttm, to_dttm, left_inc, right_inc, left_extra, right_extra, expected",
    [
        # base case end of month
        (
            clocks.MonthlyClock(),
            "20220315_15",
            "20220615_15",
            False,
            True,
            0,
            0,
            ["20220331_22", "20220430_22", "20220531_22"],
        ),
        # base case end of month find right
        (
            clocks.MonthlyClock(),
            "20220315_15",
            "20220615_15",
            False,
            False,
            0,
            1,
            ["20220331_22", "20220430_22", "20220531_22", "20220630_22"],
        ),
        # end of month with extra left and right
        (
            clocks.MonthlyClock(),
            "20220315_15",
            "20220615_15",
            False,
            True,
            2,
            1,
            ["20220131_22", "20220228_22", "20220331_22", "20220430_22", "20220531_22", "20220630_22"],
        ),
        # check right inclusivity
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            False,
            True,
            0,
            0,
            ["20220404_15", "20220504_15", "20220604_15"],
        ),
        # check right exclusivity
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            False,
            False,
            0,
            0,
            ["20220404_15", "20220504_15"],
        ),
        # check extra right with exclusivity
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            False,
            False,
            0,
            1,
            ["20220404_15", "20220504_15", "20220604_15"],
        ),
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            False,
            False,
            0,
            2,
            ["20220404_15", "20220504_15", "20220604_15", "20220704_15"],
        ),
        # check right inclusivity with steps
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            False,
            True,
            1,
            1,
            ["20220304_15", "20220404_15", "20220504_15", "20220604_15", "20220704_15"],
        ),
        # check left inclusivity
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            True,
            False,
            0,
            0,
            ["20220304_15", "20220404_15", "20220504_15"],
        ),
        # check extra left with exclusivity
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            False,
            False,
            1,
            0,
            ["20220304_15", "20220404_15", "20220504_15"],
        ),
        # check extra left with inclusivity
        (
            clocks.MonthlyClock(4, "15:00"),
            "20220304_15",
            "20220604_15",
            True,
            False,
            1,
            0,
            ["20220204_15", "20220304_15", "20220404_15", "20220504_15"],
        ),
        # check empty range
        (clocks.MonthlyClock(), "20220315_15", "20220316_15", False, True, 0, 0, []),
        # test quarterly
        (
            clocks.MonthlyClock(month_count=3),
            "20220215_15",
            "20220615_15",
            False,
            True,
            2,
            2,
            ["20210930_22", "20211231_22", "20220331_22", "20220630_22", "20220930_22"],
        ),
    ],
)
def test_monthly_clock(clock, from_dttm, to_dttm, left_inc, right_inc, left_extra, right_extra, expected):
    from_dttm = dttms.parse_dttm(from_dttm)
    to_dttm = dttms.parse_dttm(to_dttm)
    expected = dttms.parse_dttms(*expected)
    assert_array_equal(
        expected,
        clock.sample(
            from_dttm, to_dttm, left_inc=left_inc, right_inc=right_inc, left_extra=left_extra, right_extra=right_extra
        ),
    )


@pytest.mark.parametrize(
    "time, tz, from_dttm, to_dttm, expected",
    [
        (
            "09:00",
            "UTC",
            "20240313_15",
            "20240319_15",
            dttms.parse_dttms("20240314_09", "20240315_09", "20240318_09", "20240319_09"),
        ),
        (
            "09:00",
            "America/New_York",
            "20240307_15",
            "20240312_15",
            dttms.parse_dttms("20240308_14", "20240311_13", "20240312_13"),
        ),
    ],
)
def test_daily_clock(time, tz, from_dttm, to_dttm, expected):
    from_dttm = dttms.parse_dttm(from_dttm)
    to_dttm = dttms.parse_dttm(to_dttm)
    clock = DailyClock(time, tz)
    assert_array_equal(expected, clock.sample(from_dttm, to_dttm))


def test_sessions():
    session = Session(DailyClock("09:00"), DailyClock("10:00"))
    dttm = dttms.parse_dttms(
        "20240308_08",
        "20240308_09",
        "20240308_0930",
        "20240308_10",
        "20240308_11",
        "20240311_08",
        "20240311_0930",
        "20240311_11",
    )
    dttm = dttm[session.contains(dttm)]
    assert_array_equal(dttm, dttms.parse_dttms("20240308_0930", "20240308_10", "20240311_0930"))


def test_inverted_session():
    session = Session(DailyClock("10:00"), DailyClock("09:00"))
    dttm = dttms.parse_dttms(
        "20240308_08",
        "20240308_09",
        "20240308_0930",
        "20240308_10",
        "20240308_11",
        "20240311_08",
        "20240311_0930",
        "20240311_11",
    )
    dttm = dttm[session.contains(dttm)]
    assert_array_equal(
        dttm, dttms.parse_dttms("20240308_08", "20240308_09", "20240308_11", "20240311_08", "20240311_11")
    )
    assert str(session) == "Session[Daily_10:00 -> Daily_09:00]"


def test_daily_tz_weekends():
    clock = clocks.DailyClock("16:00", tz="America/Chicago")
    assert (
        clock.sample(
            np.datetime64("2012-11-29T23:00:00"), np.datetime64("2012-12-28T23:00:00"), right_inc=False, right_extra=1
        )
        is not None
    )


@pytest.mark.parametrize(
    "clock, from_dttm, to_dttm, left_inc, right_inc, left_extra, right_extra, expected",
    [
        # base case end of year
        (
            clocks.AnnualClock(),
            "20220315_15",
            "20230615_15",
            False,
            True,
            0,
            0,
            ["20221231_22"],
        ),
        # end or year either side
        (
            clocks.AnnualClock(),
            "20220315_15",
            "20230615_15",
            False,
            True,
            1,
            1,
            ["20211231_22", "20221231_22", "20231231_22"],
        ),
        # right inclusive
        (
            clocks.AnnualClock(),
            "20211231_22",
            "20231231_22",
            False,
            True,
            0,
            0,
            ["20221231_22", "20231231_22"],
        ),
        # bi-annual, 3rd of jan
        (
            clocks.AnnualClock(day_of_year=3, time_of_day="12:00", year_count=2),
            "20211231_22",
            "20231231_22",
            False,
            True,
            1,
            1,
            ["20200103_12", "20220103_12", "20240103_12"],
        ),
    ],
)
def test_annual_clock(clock, from_dttm, to_dttm, left_inc, right_inc, left_extra, right_extra, expected):
    from_dttm = dttms.parse_dttm(from_dttm)
    to_dttm = dttms.parse_dttm(to_dttm)
    expected = dttms.parse_dttms(*expected)
    assert_array_equal(
        clock.sample(
            from_dttm, to_dttm, left_inc=left_inc, right_inc=right_inc, left_extra=left_extra, right_extra=right_extra
        ),
        expected,
    )


def test_daily_chunking_walk_forward():
    clock = Clock.monthly()

    # historical sample
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220304_22", "20220504_22", "20240605_1015"))
    assert chunks == Clock.as_chunks(parse_dttms("20220228_22", "20220331_22", "20220430_22", "20220531_22"))

    # end of month
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220228_22", "20220531_22", "20220430_22"))
    assert chunks == Clock.as_chunks(parse_dttms("20220228_22", "20220331_22", "20220430_22"))

    # walking forward
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220228_22", "20220531_22", "20220501_01"))
    assert chunks == Clock.as_chunks(parse_dttms("20220228_22", "20220331_22", "20220430_22"))
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220228_22", "20220531_22", "20220502_01"))
    assert chunks == Clock.as_chunks(parse_dttms("20220228_22", "20220331_22", "20220430_22", "20220501_22"))
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220228_22", "20220531_22", "20220505_01"))
    assert chunks == Clock.as_chunks(parse_dttms("20220228_22", "20220331_22", "20220430_22", "20220504_22"))
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220228_22", "20220531_22", "20220531_01"))
    assert chunks == Clock.as_chunks(parse_dttms("20220228_22", "20220331_22", "20220430_22", "20220530_22"))

    # not ready yet
    chunks = clock.sample_chunks(*dttms.parse_dttms("20220430_22", "20220531_22", "20220501_01"))
    assert chunks == []


def test_periodic():
    cal = np.busdaycalendar(weekmask="1111100", holidays=dttms.parse_dates("20220304"))
    clock = Clock.periodic("2h", calendar=cal)

    dttm = clock.sample(*dttms.parse_dttms("20220307_03", "20220307_09"))
    assert_array_equal(
        dttm,
        dttms.parse_dttms(
            "20220307_04",
            "20220307_06",
            "20220307_08",
        ),
    )

    dttm = clock.sample(*dttms.parse_dttms("20220307_03", "20220307_09"), left_extra=1, right_extra=1)
    assert_array_equal(
        dttm, dttms.parse_dttms("20220307_02", "20220307_04", "20220307_06", "20220307_08", "20220307_10")
    )

    dttm = clock.sample(*dttms.parse_dttms("20220307_03", "20220307_09"), left_extra=3)
    assert_array_equal(
        dttm,
        dttms.parse_dttms("20220303_22", "20220307_00", "20220307_02", "20220307_04", "20220307_06", "20220307_08"),
    )


def test_clock_with_session():
    cal = np.busdaycalendar(weekmask="1111100", holidays=dttms.parse_dates("20220304"))
    clock = Clock.from_hours({"start": "07:00", "end": "14:00", "tz": "Europe/London"}, period="2h", calendar=cal)

    dttm = clock.sample(*dttms.parse_dttms("20220307_03", "20220307_09"))
    assert_array_equal(dttm, dttms.parse_dttms("20220307_08"))

    dttm = clock.sample(*dttms.parse_dttms("20220307_03", "20220307_09"), left_extra=1, right_extra=1)
    assert_array_equal(dttm, dttms.parse_dttms("20220303_14", "20220307_08", "20220307_10"))


def test_next():
    clock = Clock.periodic("10m")
    dttm = clock.next(dttms.parse_dttms("20220307_0301", "20220307_0309", "20220307_0310", "20220307_0312"))
    assert_array_equal(dttm, dttms.parse_dttms("20220307_0310", "20220307_0310", "20220307_0310", "20220307_0320"))


def test_prev():
    clock = Clock.periodic("10m")
    dttm = clock.previous(dttms.parse_dttms("20220307_0301", "20220307_0309", "20220307_0310", "20220307_0312"))
    assert_array_equal(dttm, dttms.parse_dttms("20220307_0300", "20220307_0300", "20220307_0300", "20220307_0310"))


@pytest.mark.parametrize(
    "clocks_list, from_dttm, to_dttm, left_inc, right_inc, left_extra, right_extra, expected",
    [
        # basic case - combine two daily clocks with different times
        (
            [
                clocks.DailyClock("09:00"),
                clocks.DailyClock("17:00"),
            ],
            "20220307_08",
            "20220309_18",
            False,
            True,
            0,
            0,
            ["20220307_09", "20220307_17", "20220308_09", "20220308_17", "20220309_09", "20220309_17"],
        ),
        # test with overlapping times (should deduplicate)
        (
            [
                clocks.DailyClock("09:00"),
                clocks.DailyClock("09:00"),
                clocks.DailyClock("17:00"),
            ],
            "20220307_08",
            "20220308_18",
            False,
            True,
            0,
            0,
            ["20220307_09", "20220307_17", "20220308_09", "20220308_17"],
        ),
        # test with periodic clocks
        (
            [
                clocks.PeriodicClock("2h", calendar=None),
                clocks.DailyClock("09:00"),
            ],
            "20220307_08",
            "20220307_11",
            True,
            True,
            0,
            0,
            ["20220307_08", "20220307_09", "20220307_10"],
        ),
        # test with left and right inclusivity
        (
            [
                clocks.DailyClock("09:00"),
                clocks.DailyClock("17:00"),
            ],
            "20220307_09",
            "20220307_17",
            True,
            False,
            0,
            0,
            ["20220307_09"],
        ),
        # test with extra left and right
        (
            [
                clocks.DailyClock("09:00"),
                clocks.DailyClock("17:00"),
            ],
            "20220307_10",
            "20220307_16",
            False,
            True,
            0,
            1,
            ["20220307_17"],
        ),
        # test with monthly and daily clocks
        (
            [
                clocks.MonthlyClock(15, "12:00"),
                clocks.DailyClock("09:00"),
            ],
            "20220314_08",
            "20220316_10",
            False,
            True,
            0,
            0,
            ["20220314_09", "20220315_09", "20220315_12", "20220316_09"],
        ),
        # test with empty result from one clock
        (
            [
                clocks.DailyClock("09:00"),
                clocks.MonthlyClock(15, "12:00"),  # won't fire in the range
            ],
            "20220307_08",
            "20220307_10",
            False,
            True,
            0,
            0,
            ["20220307_09"],
        ),
    ],
)
def test_disjoint_union_clock(clocks_list, from_dttm, to_dttm, left_inc, right_inc, left_extra, right_extra, expected):
    from_dttm = dttms.parse_dttm(from_dttm)
    to_dttm = dttms.parse_dttm(to_dttm)
    expected = dttms.parse_dttms(*expected)

    union_clock = clocks.UnionClock(clocks_list)
    result = union_clock.sample(
        from_dttm, to_dttm, left_inc=left_inc, right_inc=right_inc, left_extra=left_extra, right_extra=right_extra
    )

    assert_array_equal(expected, result)


def test_intraday_intersection():
    session = Session.from_config_hours(
        {
            "intersect": {
                "1": {"start": "08:00", "end": "17:00", "tz": "Europe/London"},
                "2": {"start": "08:00", "end": "16:00", "tz": "America/Montreal"},
            }
        }
    )

    clock = Clock.periodic("20m")

    from_dttm, to_dttm1, to_dttm2 = dttms.parse_dttms("20260120_08", "20260120_10", "20260120_22")

    intra = clock.sample(from_dttm, to_dttm1)
    daily = clock.sample(from_dttm, to_dttm2)

    intra = pd.Series(index=intra, data=session.contains(intra))
    daily = pd.Series(index=daily, data=session.contains(daily))

    assert_array_equal(daily[:to_dttm1], intra)
