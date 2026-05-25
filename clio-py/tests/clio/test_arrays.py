from io import StringIO

from pytest import fixture
import numpy as np
import pandas as pd

from clio import arrays, dttms, empty_series, empty_frame
from clio.arrays import search_sorted_exact, union1d_mapped, compile_arrays


@fixture(scope="module", autouse=True)
def compile_():
    compile_arrays()


def test_is_sorted():
    assert arrays.is_sorted(np.asarray([1, 2, 3, 4]))
    assert arrays.is_sorted(np.asarray([1.0, 2.0, 2.0, 4.0]))
    assert arrays.is_sorted(np.asarray(["2026-01-01", "2026-01-02", "2026-01-07", "2026-01-10"], dtype="datetime64"))
    assert arrays.is_sorted(
        np.asarray(["2026-01-01", "2026-01-02", "2026-01-07", "2026-01-10"], dtype="datetime64[ns]")
    )
    assert not arrays.is_sorted(np.asarray([3, 2, 2, 4]))


def test_asof_align():
    a = pd.Series(
        data=[1, 2, 3, 4, 5],
        index=dttms.parse_dttms("20220101_01", "20220101_02", "20220101_03", "20220101_04", "20220101_04"),
    )

    b = pd.Series(
        data=[6, 7, 8, 9], index=dttms.parse_dttms("20220101_0130", "20220101_02", "20220101_0230", "20220101_03")
    )

    pd.testing.assert_series_equal(
        arrays.asof_align(a, b.index),
        pd.Series(data=[1, 2, 2, 3], index=b.index),
    )

    pd.testing.assert_series_equal(
        arrays.asof_align(b, a.index, missing=-1), pd.Series(data=[-1, 7, 9, 9, 9], index=a.index)
    )


def test_asof_operation():
    a = pd.Series(
        data=[1, 2, 3, 4, 5],
        index=dttms.parse_dttms("20220101_01", "20220101_02", "20220101_03", "20220101_04", "20220101_04"),
    )

    b = pd.Series(
        data=[6, 7, 8, 9], index=dttms.parse_dttms("20220101_0130", "20220101_02", "20220101_0230", "20220101_03")
    )

    pd.testing.assert_series_equal(
        arrays.asof_operation(b, a, arrays.add),
        pd.Series(data=[6 + 1, 7 + 2, 8 + 2, 9 + 3], index=b.index),
    )

    pd.testing.assert_series_equal(
        arrays.asof_operation(a, b, arrays.mul, missing=0),
        pd.Series(data=[0, 2 * 7, 3 * 9, 4 * 9, 5 * 9], index=a.index),
    )


def test_search_sorted_exact():
    np.testing.assert_array_equal(search_sorted_exact(np.asarray([1, 2, 3, 4]), np.asarray([2, 3])), np.asarray([1, 2]))
    np.testing.assert_array_equal(search_sorted_exact(np.asarray([1, 2, 4, 5]), np.asarray([2, 3])), np.asarray([1, 4]))
    np.testing.assert_array_equal(
        search_sorted_exact(np.asarray([2, 4, 5]), np.asarray([1, 2, 3, 7])), np.asarray([3, 0, 3, 3])
    )


def test_union1d_mapped():
    np.testing.assert_array_equal(
        union1d_mapped(np.asarray([10, 22, 42, 52]), np.asarray([23, 33, 43, 63]), lambda x: x - (x % 10)),
        np.asarray([10, 22, 33, 42, 52, 63]),
    )


def test_cumsum_nonzero():
    np.testing.assert_array_equal(
        arrays.cumsum_nonzero(np.asarray([0, 1, 5, 0, 4, 3, 2, 0])),
        np.asarray([0, 1, 6, 0, 4, 7, 9, 0]),
    )


def test_slice_op_gaps():
    values = np.asarray([2, 1, 6, -1, 4, 7, 9, -3])
    idx = np.asarray(range(len(values)))

    result, idx = arrays.slice_op(idx, np.asarray([1, 5]), np.asarray([3, 6]), values, arrays.np_sum)
    np.testing.assert_array_equal(result, np.asarray([5, 9]))


def test_slice_op_gaps_mean():
    values = np.asarray([2, 1, 6, -1, 4, 7, 9, -3])
    idx = np.asarray(range(len(values)))

    result, idx = arrays.slice_op(idx, np.asarray([1, 5]), np.asarray([3, 6]), values, arrays.np_mean)
    np.testing.assert_array_equal(result, np.asarray([2.5, 9.0]))


def test_slice_op_gaps_max():
    values = np.asarray([2, 1, 6, -1, 4, 7, 9, -3])
    idx = np.asarray(range(len(values)))

    result, idx = arrays.slice_op(idx, np.asarray([1, 5]), np.asarray([3, 6]), values, arrays.np_max)
    np.testing.assert_array_equal(result, np.asarray([6.0, 9.0]))


def test_slice_op_gaps_min():
    values = np.asarray([2, 1, 6, -1, 4, 7, 9, -3])
    idx = np.asarray(range(len(values)))

    result, idx = arrays.slice_op(idx, np.asarray([1, 5]), np.asarray([3, 6]), values, arrays.np_min)
    np.testing.assert_array_equal(result, np.asarray([-1, 9]))


def test_slice_op_gaps_filled():
    values = np.asarray([2.0, 1.0, 6.0, -1.0, 4.0, 7.0, 9.0, -3.0])
    idx = np.asarray(range(len(values)), dtype=np.float64)

    result, idx = arrays.slice_op(
        idx, np.asarray([1.0, 5.0]), np.asarray([3.0, 6.0]), values, arrays.np_sum, fill_gaps=np.nan
    )
    np.testing.assert_array_equal(result, np.asarray([np.nan, 5.0, np.nan, 9.0]))


def test_slice_op_overrun():
    values = np.asarray([2, 1, 6, -1, 4, 7, 9, -3])
    idx = np.asarray(range(len(values)))

    result, idx = arrays.slice_op(idx, np.asarray([-8, -3, 5, 14]), np.asarray([-7, 3, 9, 16]), values, arrays.np_sum)
    np.testing.assert_array_equal(result, np.asarray([np.nan, 8, 6, np.nan]))


def test_slice_empty_slice():
    values = np.asarray([2, 1, 6, -1, 4, 7, 9, -3])
    idx = np.asarray(range(len(values)))

    result, idx = arrays.slice_op(idx, np.asarray([20]), np.asarray([20]), values, arrays.np_sum)
    np.testing.assert_array_equal(result, np.asarray([np.nan]))


def test_slice_op_start_chunk():
    inputs = {
        "20220101_1501": 0.5,
        "20220101_1502": 0.6,
        "20220101_1503": np.nan,
        "20220101_1504": 0.7,
        "20220101_1505": 0.8,
        # chunk with only first value
        "20220101_1506": 0.9,
        "20220101_1507": np.nan,
        "20220101_1508": np.nan,
        "20220101_1509": np.nan,
        "20220101_1510": np.nan,
        # chunk with only last value
        "20220101_1511": np.nan,
        "20220101_1512": np.nan,
        "20220101_1513": np.nan,
        "20220101_1514": np.nan,
        "20220101_1515": 1.0,
    }
    inputs = pd.Series(inputs.values(), index=dttms.parse_dttms(*inputs.keys()))
    starts = dttms.parse_dttms("20220101_1500", "20220101_1505", "20220101_1510")
    ends = dttms.parse_dttms("20220101_1505", "20220101_1510", "20220101_1515")

    inputs = inputs[np.isfinite(inputs)]
    result = arrays.slice_frame(inputs, starts, ends, arrays.last, fill_gaps=np.nan)
    pd.testing.assert_series_equal(
        result,
        pd.Series(
            data=[np.nan, 0.8, 0.9, 1.0],
            index=dttms.parse_dttms("20220101_1500", "20220101_1505", "20220101_1510", "20220101_1515"),
        ),
    )


def _slice_op_expected():
    expected = """dttm,close
    2012-03-09 11:00:00,
    2012-03-09 11:05:00,107.33
    2012-03-09 11:10:00,107.31
    2012-03-09 11:15:00,107.25
    2012-03-09 11:20:00,
    2012-03-09 11:25:00,107.3
    2012-03-09 11:30:00,107.34"""
    return pd.read_csv(StringIO(expected), parse_dates=["dttm"], index_col="dttm")["close"]


def _slice_op_inputs():
    inputs = """dttm,close
    2012-03-09 11:01:00,107.32
    2012-03-09 11:02:00,107.34
    2012-03-09 11:03:00,
    2012-03-09 11:04:00,107.33
    2012-03-09 11:05:00,107.33
    2012-03-09 11:06:00,107.4
    2012-03-09 11:07:00,107.37
    2012-03-09 11:08:00,
    2012-03-09 11:09:00,
    2012-03-09 11:10:00,107.31
    2012-03-09 11:11:00,107.31
    2012-03-09 11:12:00,107.3
    2012-03-09 11:13:00,107.25
    2012-03-09 11:14:00,
    2012-03-09 11:15:00,
    2012-03-09 11:16:00,
    2012-03-09 11:17:00,
    2012-03-09 11:18:00,
    2012-03-09 11:19:00,
    2012-03-09 11:20:00,
    2012-03-09 11:21:00,107.3
    2012-03-09 11:22:00,
    2012-03-09 11:23:00,
    2012-03-09 11:24:00,
    2012-03-09 11:25:00,
    2012-03-09 11:26:00,
    2012-03-09 11:27:00,
    2012-03-09 11:28:00,107.33
    2012-03-09 11:29:00,
    2012-03-09 11:30:00,107.34"""
    return pd.read_csv(StringIO(inputs), parse_dates=["dttm"], index_col="dttm")["close"]


def test_slice_op_example():
    expected = _slice_op_expected()
    inputs = _slice_op_inputs()

    starts = expected.index.values[:-1]

    result = arrays.slice_frame(
        inputs[np.isfinite(inputs)], starts, expected.index.values[1:], arrays.last, fill_gaps=np.nan
    )
    result.index.name = "dttm"
    pd.testing.assert_series_equal(result, expected)


def test_slice_op_2d_scratch():
    from numba import njit

    idx = np.array([6, 50], dtype=np.int64)
    ends = np.array([3, 5], dtype=np.int64)
    starts = np.array([0, 4], dtype=np.int64)

    values = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0], [11.0, 12.0], [13.0, 14.0]])

    @njit()
    def op(x):
        return np.sum(x, axis=0)

    result, new_idx = arrays.slice_op_2d(idx, starts, ends, values, op)
    assert len(result) == 2


def test_slice_frame():
    expected = _slice_op_expected()
    inputs = _slice_op_inputs()
    inputs = pd.DataFrame({"x1": inputs, "x2": inputs * 2})

    starts = expected.index.values[:-1]
    result = arrays.slice_frame(
        inputs[np.isfinite(inputs).any(axis=1)], starts, expected.index.values[1:], arrays.last, fill_gaps=np.nan
    )
    result.index.name = "dttm"
    pd.testing.assert_frame_equal(result, pd.DataFrame({"x1": expected, "x2": expected * 2}))


def test_merge_series():
    a = pd.Series([1.1, 2.2, 5.5], index=[1, 2, 5])
    b = pd.Series([3.3, 4.4, 6.6], index=[3, 4, 6])
    expected = pd.Series([1.1, 2.2, 3.3, 4.4, 5.5, 6.6], index=[1, 2, 3, 4, 5, 6])
    pd.testing.assert_series_equal(arrays.merge_series(a, b), expected)


def test_merge_series_overlapping():
    a = pd.Series([1.1, 2.2, 5.5], index=[1, 2, 5])
    b = pd.Series([2.3, 4.4, 6.6], index=[2, 4, 6])
    expected = pd.Series([1.1, 2.2, 4.4, 5.5, 6.6], index=[1, 2, 4, 5, 6])
    pd.testing.assert_series_equal(arrays.merge_series(a, b, drop_duplicates=True), expected)


def test_combine_by_index():
    a = np.asarray([1.1, 1.3, 1.6, 3.3, 3.4])
    b = np.asarray([1.5, 1.8, 2.2, 3.1, 4.1])

    expected = np.asarray([1.1, 2.2, 3.1, 4.1])
    np.testing.assert_array_equal(arrays.combine_by_index(a, a.astype(int), b, b.astype(int), arrays.min_), expected)

    expected = np.asarray([1.8, 2.2, 3.4, 4.1])
    np.testing.assert_array_equal(arrays.combine_by_index(a, a.astype(int), b, b.astype(int), arrays.max_), expected)


def test_reduce_by_index():
    data = pd.Series(np.asarray([1.1, 1.3, 1.6, 3.3, 3.4, 4.5, 4.1]))

    expected = np.asarray([1.1, 3.3, 4.1])
    np.testing.assert_array_equal(arrays.reduce_by_index(data, data.values.astype(int), arrays.min_), expected)

    expected = np.asarray([1.1 + 1.3 + 1.6, 3.3 + 3.4, 4.5 + 4.1])
    np.testing.assert_array_equal(arrays.reduce_by_index(data, data.values.astype(int), arrays.add), expected)


def test_interp():
    a = pd.Series([1.0, 2.0, 3.0], index=[10, 20, 30])
    idx = np.asarray([5, 10, 15, 20, 22, 28, 30, 31])

    expected = pd.Series(data=[np.nan, 1.0, 1.5, 2.0, 2.2, 2.8, 3.0, np.nan], index=idx)
    pd.testing.assert_series_equal(arrays.interp_align(a, idx, regularize=False), expected)


def test_target_interp():
    a = pd.Series([1.0, 2.0, 3.0, 4.0], index=[10, 20, 30, 40])
    idx = np.asarray([13, 16, 23, 26, 33, 36])

    expected = pd.Series(data=[np.nan, 1.0, 1.5, 2.0, 2.5, 3.0], index=idx)
    pd.testing.assert_series_equal(arrays.interp_target_align(a, idx), expected)


def test_target_interp_gaps():
    a = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0, 5.0], index=[0, 10, 20, 30, 40, 50])

    idx = np.asarray([5, 6, 15, 16, 45, 46])

    expected = pd.Series(data=[np.nan, 0.0, 0.5, 1.0, 2.5, 4.0], index=idx)
    pd.testing.assert_series_equal(arrays.interp_target_align(a, idx), expected)


def test_deduplicate_by_column_adjacent():
    df = pd.DataFrame(
        {"a": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0], "b": [0.1, 2.1, 1.1, 4.1, 3.1, 5.1]}, index=[0, 10, 10, 20, 20, 30]
    )
    by_a = df[arrays.deduplicate_index_by_column(df.index, df["a"])]
    pd.testing.assert_frame_equal(by_a, df[[True, False, True, False, True, True]])

    by_b = df[arrays.deduplicate_index_by_column(df.index, df["b"])]
    pd.testing.assert_frame_equal(by_b, df[[True, True, False, True, False, True]])


def test_deduplicate_by_column_ends():
    df = pd.DataFrame(
        {"a": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "b": [6, 5, 4, 3, 2, 1, 0]}, index=[0, 0, 0, 20, 30, 30, 30]
    )
    by_a = df[arrays.deduplicate_index_by_column(df.index, df["a"])]
    pd.testing.assert_frame_equal(by_a, df[[False, False, True, True, False, False, True]])

    by_b = df[arrays.deduplicate_index_by_column(df.index, df["b"])]
    pd.testing.assert_frame_equal(by_b, df[[True, False, False, True, True, False, False]])


def test_apply_non_nan():
    df1 = pd.DataFrame({"a": [0.0, np.nan, np.nan], "b": [2.0, 2.1, 2.2]}, index=[1, 2, 3])

    df2 = pd.DataFrame({"a": [1.0, 1.1, 1.2, 1.3], "b": [3.0, 3.1, 3.2, 3.3]}, index=[1, 2, 3, 4])

    result = arrays.apply_non_nan(df2, df1)

    expected = pd.DataFrame({"a": [0.0, 1.1, 1.2, 1.3], "b": [2.0, 2.1, 2.2, 3.3]}, index=[1, 2, 3, 4])

    pd.testing.assert_frame_equal(result, expected)


def test_slice_op_2d_boundary_case():
    idx = np.array([5, 6, 7, 8], dtype=np.int64)
    starts = np.array([5], dtype=np.int64)
    ends = np.array([8], dtype=np.int64)
    values = np.array([[5.0, 50.0], [6.0, 60.0], [7.0, 70.0], [8.0, 80.0]])

    result, new_idx = arrays.slice_op_2d(idx, starts, ends, values, arrays.np_sum)
    assert np.allclose(result, [21.0, 210.0])

    result, new_idx = arrays.slice_op_2d(idx, starts, ends, values, arrays.first)
    assert np.allclose(result, [6.0, 60.0])

    result, new_idx = arrays.slice_op_2d(idx, starts, ends, values, arrays.last)
    assert np.allclose(result, [8.0, 80.0])


def test_slice_op_2d_gaps():
    idx = np.array([1, 2, 3, 4, 6, 7, 8, 9, 11, 12], dtype=np.int64)
    starts = np.array([0, 5, 10], dtype=np.int64)
    ends = np.array([4, 9, 15], dtype=np.int64)
    values = np.array([[1, 10], [2, 20], [3, 30], [4, 40], [6, 60], [7, 70], [8, 80], [9, 90], [11, 110], [12, 120]])

    result, new_idx = arrays.slice_op_2d(idx, starts, ends, values, arrays.np_sum, fill_gaps=np.nan)
    assert np.all(np.isnan(result[0]))
    assert np.allclose(result[1], [10, 100])
    assert np.all(np.isnan(result[2]))
    assert np.allclose(result[3], [30, 300])
    assert np.all(np.isnan(result[4]))
    assert np.allclose(result[5], [23, 230])


def test_slice_op_2d_out_of_bounds():
    idx = np.array([6, 50], dtype=np.int64)
    ends = np.array([3, 5], dtype=np.int64)
    starts = np.array([0, 4], dtype=np.int64)

    values = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0], [11.0, 12.0], [13.0, 14.0]])

    result, new_idx = arrays.slice_op_2d(idx, starts, ends, values, arrays.np_sum)
    assert len(result) == 2


def test_concat_series():
    df = arrays.concat(pd.Series([1, 2, 3]), pd.Series([4, 5, 6]))
    pd.testing.assert_series_equal(df, pd.concat([pd.Series([1, 2, 3]), pd.Series([4, 5, 6])]))

    df = arrays.concat(pd.Series([1, 2, 3]), pd.Series())
    pd.testing.assert_series_equal(df, pd.Series([1, 2, 3]))

    df = arrays.concat(pd.Series(), pd.Series([4, 5, 6]))
    pd.testing.assert_series_equal(df, pd.Series([4, 5, 6]))

    df = arrays.concat(pd.Series(), pd.Series())
    pd.testing.assert_series_equal(df, empty_series())


def test_concat_frame():
    df = arrays.concat(pd.DataFrame({"a": [1, 2, 3]}), pd.DataFrame({"a": [4, 5, 6]}))
    pd.testing.assert_frame_equal(df, pd.concat([pd.DataFrame({"a": [1, 2, 3]}), pd.DataFrame({"a": [4, 5, 6]})]))

    df = arrays.concat(pd.DataFrame({"a": [1, 2, 3]}), pd.DataFrame())
    pd.testing.assert_frame_equal(df, pd.DataFrame({"a": [1, 2, 3]}))

    df = arrays.concat(pd.DataFrame(), pd.DataFrame({"a": [4, 5, 6]}))
    pd.testing.assert_frame_equal(df, pd.DataFrame({"a": [4, 5, 6]}))

    df = arrays.concat(pd.DataFrame(), pd.DataFrame())
    pd.testing.assert_frame_equal(df, empty_frame())
