import datetime
from typing import Callable

import numpy as np
import pandas as pd
import numba as nb
from numba import njit

from core import dttms, is_primitive, empty_frame, empty_series


@njit()
def is_sorted(a):
    for i in range(a.size - 1):
        if a[i + 1] < a[i]:
            return False
    return True


def nan_equals(a, b):
    return (a == b) | (np.isnan(a) & np.isnan(b))


def asof_operation(
    x: pd.Series | pd.DataFrame,
    y: pd.Series | pd.DataFrame,
    ufunc: Callable,
    out: pd.Series | pd.DataFrame = None,
    missing=np.nan,
):
    """
    apply operation using the latest/current value of y to each index of x
    :param x: data to which operation will be aligned (result will have x index)
    :param y: data on different alignment
    :param ufunc: operation to apply (must be njit)
    :param out: if specified will do inplace, otherwise will create new array (np convention)
    :param missing: fill with this value when no alignment (x starts before y)
    """
    if out is None:
        out = x.copy()
    _asof_operation(x.values, x.index.values, y.values, y.index.values, ufunc, out=out.values, missing=missing)
    return out


def nan_for_type(dtype):
    if np.issubdtype(dtype, np.floating):
        return np.nan
    if np.issubdtype(dtype, np.integer):
        return 0
    if np.issubdtype(dtype, bool):
        return False
    if np.issubdtype(dtype, np.datetime64):
        return np.datetime64("NaT")
    return np.nan


def asof_align(data: float | pd.Series | pd.DataFrame, idx: pd.Index, missing=..., primitive_index=None):
    """
    using np/pd to align to index
    (asof_operation above is likely to be faster)
    """
    if is_primitive(data):
        if primitive_index is not None:
            if primitive_index is ...:
                primitive_index = idx
            return pd.Series(index=primitive_index, data=[data] * len(primitive_index))
        return data

    lookleft = np.searchsorted(data.index, idx, side="right") - 1
    missed = lookleft < 0

    if np.all(missed):
        if missing is ...:
            missing = nan_for_type(data.values.dtype)
        values = missing
    else:
        values = data.values[lookleft]

    if isinstance(data, pd.Series):
        result = pd.Series(index=idx, data=values)
    else:
        result = pd.DataFrame(index=idx, data=values, columns=data.columns)

    if np.any(missed):
        if missing is ...:
            missing = nan_for_type(result.values.dtype)
        result[missed] = missing
    return result


def interp_align(data: pd.Series | pd.DataFrame, idx: pd.Index, missing=np.nan, regularize=True):
    """
    align by interpolating between points
    this is explicitly looking forward, so should only be done on already shifted/aligned ata
    """
    if regularize:
        idx_b = np.searchsorted(idx, data.index.values)
        idx_a = np.arange(len(idx))
    else:
        assert data.index.values.dtype == idx.dtype
        idx_a = idx.astype(int)
        idx_b = data.index.values.astype(int)

    result = np.interp(idx_a, idx_b, data.values, left=missing, right=missing)
    if isinstance(data, pd.Series):
        return pd.Series(index=idx, data=result)
    else:
        return pd.DataFrame(index=idx, data=result)


def interp_target_align(data: pd.Series, idx: pd.Index, missing=np.nan, regularize=True):
    """
    align targets to their penultimate sample, then interpolate to them
    """
    if len(data) == 0:
        return data

    if len(ext_idx := idx[idx > data.index.values[-1]]) > 0:
        # extend data to end of each day
        eods = dttms.to_eod(np.unique(dttms.to_trade_date(ext_idx)))
        data = pd.concat([data, pd.Series(data=data.values[-1], index=eods)])

    penultimate_idx = np.searchsorted(idx, data.index.values, side="left") - 1
    penultimate_value = np.roll(data.values, 1)
    penultimate_value[0] = missing

    missed = penultimate_idx == -1
    aligned = pd.Series(penultimate_value[~missed], index=idx[penultimate_idx[~missed]])
    aligned = aligned[~aligned.index.duplicated(keep="first")]

    return interp_align(aligned, idx, missing=missing, regularize=regularize)


def union_align(
    a: pd.Series | pd.DataFrame, b: pd.Series | pd.DataFrame, missing=...
) -> (pd.Series | pd.DataFrame, pd.Series | pd.DataFrame):
    idx = np.union1d(a.index.values, b.index.values)
    return asof_align(a, idx, missing=missing), asof_align(b, idx, missing=missing)


@njit()
def add(a, b):
    return a + b


@njit()
def min_(a, b):
    return min(a, b)


@njit()
def max_(a, b):
    return max(a, b)


@njit()
def np_sum(a):
    return np.sum(a, axis=0)


@njit()
def np_mean(a):
    if a.ndim == 1:
        return np.mean(a)
    elif a.ndim == 2:
        output = np.full(a.shape[1], fill_value=np.nan, dtype=np.float64)
        for i in range(a.shape[1]):
            output[i] = np.mean(a[:, i])
        return output
    else:
        raise ValueError("Input must be 1D or 2D array")


@njit()
def np_max(a):
    if a.ndim == 1:
        return np.max(a)
    elif a.ndim == 2:
        output = np.full(a.shape[1], fill_value=np.nan, dtype=a.dtype)
        for i in range(a.shape[1]):
            output[i] = np.max(a[:, i])
        return output
    else:
        raise ValueError("Input must be 1D or 2D array")


@njit()
def np_min(a):
    if a.ndim == 1:
        return np.min(a)
    elif a.ndim == 2:
        output = np.full(a.shape[1], fill_value=np.nan, dtype=a.dtype)
        for i in range(a.shape[1]):
            output[i] = np.min(a[:, i])
        return output
    else:
        raise ValueError("Input must be 1D or 2D array")


@njit()
def mul(a, b):
    return a * b


@njit()
def first(a):
    if a.ndim == 1:
        return a[0]
    elif a.ndim == 2:
        return a[0, :]
    else:
        raise ValueError("Input must be 1D or 2D array")


@njit()
def last(a):
    if a.ndim == 1:
        return a[-1]
    elif a.ndim == 2:
        return a[-1, :]
    else:
        raise ValueError("Input must be 1D or 2D array")


@njit()
def _asof_operation(x, xx, y, yx, ufunc, out=None, missing=np.nan):
    if out is None:
        out = x.copy()
    xi = 0
    yi = 0

    while xx[xi] < yx[yi] and xi < len(xx):
        out[xi] = missing
        xi += 1

    while xi < len(xx):
        while yi + 1 < len(yx) and xx[xi] >= yx[yi + 1]:
            yi += 1
        out[xi] = ufunc(x[xi], y[yi])
        xi += 1

    return out


def search_sorted_exact(a, b, map_=None):
    """find the index of b within a (out of bounds if not found)"""
    if map_ is not None:
        a = map_(a)
        b = map_(b)
    idx = np.searchsorted(a, b, side="right") - 1
    idx[a[idx] != b] = len(a)
    return idx


def union1d_mapped(a, b, map_):
    """returns unmapped items from unique-after-mapping indexes from a then b, assuming both are sorted"""
    idx = np.union1d(ma := map_(a), mb := map_(b))
    idx_b = np.in1d(idx, mb)
    idx_a = np.in1d(idx, ma)
    idx = idx.astype(a.dtype)
    idx[idx_b] = b
    idx[idx_a] = a
    return idx


def slice_frame(frame: pd.DataFrame | pd.Series, starts, ends, op, fill=np.nan, fill_gaps=None):
    if isinstance(frame, pd.DataFrame):
        result, idx = slice_op_2d(frame.index.values, starts, ends, frame.values, op, fill=fill, fill_gaps=fill_gaps)
        return pd.DataFrame(index=idx, data=result, columns=frame.columns)
    else:
        result, idx = slice_op(frame.index.values, starts, ends, frame.values, op, fill=fill, fill_gaps=fill_gaps)
        return pd.Series(index=idx, data=result, name=frame.name)


def compile_slice_frame():
    from core.clocks import Clock

    _clocks = [Clock.daily("07:00"), Clock.daily_eod()]
    _dttms = dttms.parse_dttm("sod-20D"), dttms.parse_dttm("eod")

    opens = Clock.first_by_day(_clocks).sample(*_dttms)
    closes = Clock.last_by_day(_clocks).sample(*_dttms)

    # price slicer
    df = pd.Series(data=[1.0] * len(opens), index=opens)
    slice_frame(df, opens, closes, first)
    slice_frame(df, opens, closes, last, fill_gaps=1.0)
    slice_frame(df, opens, closes, np_mean)
    slice_frame(df, opens, closes, np_max)
    slice_frame(df, opens, closes, np_min)
    slice_frame(df, opens, closes, np_sum)

    # price slicer
    df = pd.DataFrame({"a": df, "b": df})
    slice_frame(df, opens, closes, first)
    slice_frame(df, opens, closes, last, fill_gaps=1.0)
    slice_frame(df, opens, closes, np_mean)
    slice_frame(df, opens, closes, np_max)
    slice_frame(df, opens, closes, np_min)
    slice_frame(df, opens, closes, np_sum)


@njit()
def slice_op(idx, starts, ends, values, op, fill=np.nan, fill_gaps=None):
    """
    returns the result of "op" on a series of slices aligned to "ends"
    :param idx: the index of values (to compare to starts/ends)
    :param starts: the start of the slices (exclusive)
    :param ends: the end of the slices (inclusive)
    :param values: the values to be operated on
    :param op: the operation to perform (must be njit)
    :param fill: the fill value for when no value between start/end
    :param fill_gaps: if the starts/ends are not contiguous; mark the end of the unsampled period (start of the sampled
    period). This is useful later as it allows you to align things to the unsampled period (i.e. probably dropped them)
    """

    result = np.full(ends.shape, fill)
    range_i = 0
    range_start = -1

    i = 0
    while i < len(idx):
        if range_start == -1:
            while idx[i] > ends[range_i]:
                range_i += 1
                if range_i >= len(result):
                    break

            if range_i >= len(starts):
                i = len(idx)
                range_start = -1
            else:
                if idx[i] <= starts[range_i]:
                    i += 1
                    continue
                range_start = i

        if range_start != -1:
            if idx[i] >= ends[range_i]:
                end_range = i if idx[i] > ends[range_i] else i + 1
                result[range_i] = op(values[range_start:end_range])
                range_start = -1
                range_i += 1

                if range_i >= len(result):
                    break

                continue

        i += 1

    if range_start != -1:
        result[range_i] = op(values[range_start:])

    if fill_gaps is not None:  # work out where the gaps are and merge "fill_gaps" into result
        isrange = starts != ends
        rstarts = starts[isrange]
        rends = ends[isrange]
        if len(rends) > 0:
            gap_ends = np.roll(rends, 1)
            gap_ends[0] = rstarts[0]
            gap_ends = rstarts[(rstarts > gap_ends) | (gap_ends == rstarts[0])]

            if len(gap_ends) > 0:
                return array_merge(ends, result, gap_ends, None, fill_gaps)

    return result, ends


@njit()
def slice_op_2d(idx, starts, ends, values, op, fill=np.nan, fill_gaps=None):
    """
    copy of slice_op for 2d arrays
    """

    result = np.full((ends.shape[0], values.shape[1]), fill)

    range_i = 0
    range_start = -1

    i = 0
    while i < len(idx):
        if range_start == -1:
            while idx[i] > ends[range_i]:
                range_i += 1
                if range_i >= len(result):
                    break

            if range_i >= len(starts):
                i = len(idx)
                range_start = -1
            else:
                if idx[i] <= starts[range_i]:
                    i += 1
                    continue
                range_start = i

        if range_start != -1:
            if idx[i] >= ends[range_i]:
                end_range = i if idx[i] > ends[range_i] else i + 1
                result[range_i] = op(values[range_start:end_range])
                range_start = -1
                range_i += 1

                if range_i >= len(result):
                    break

                continue

        i += 1

    if range_start != -1:
        result[range_i] = op(values[range_start:])

    if fill_gaps is not None:  # work out where the gaps are and merge "fill_gaps" into result
        isrange = starts != ends
        rstarts = starts[isrange]
        rends = ends[isrange]
        if len(rends) > 0:
            gap_ends = np.roll(rends, 1)
            gap_ends[0] = rstarts[0]
            gap_ends = rstarts[(rstarts > gap_ends) | (gap_ends == rstarts[0])]

            if len(gap_ends) > 0:
                return array_merge_2d(ends, result, gap_ends, None, fill_gaps)

    return result, ends


@njit()
def array_merge(idx_a, values_a, idx_b, values_b, fill_b=None):
    """
    merge two arrays based on their relative indexes (allow values_b to be a const)
    """
    result = np.full(len(idx_a) + len(idx_b), values_a[0])
    result_idx = np.full(result.shape, idx_a[0])

    ia = 0
    ib = 0

    for i in range(len(result)):
        if ib == len(idx_b) or (ia != len(idx_a) and idx_a[ia] <= idx_b[ib]):
            result_idx[i] = idx_a[ia]
            result[i] = values_a[ia]
            ia += 1
        else:
            result_idx[i] = idx_b[ib]
            result[i] = fill_b if values_b is None else values_b[ib]
            ib += 1
    return result, result_idx


@njit()
def array_merge_2d(idx_a, values_a, idx_b, values_b, fill_b=None):
    """
    copy of array_merge for 2d arrays
    """
    result = np.full((len(idx_a) + len(idx_b), values_a.shape[1]), values_a[0, 0])
    result_idx = np.full(len(result), idx_a[0])

    ia = 0
    ib = 0

    for i in range(len(result)):
        if ib == len(idx_b) or (ia != len(idx_a) and idx_a[ia] <= idx_b[ib]):
            result_idx[i] = idx_a[ia]
            result[i] = values_a[ia]
            ia += 1
        else:
            result_idx[i] = idx_b[ib]
            result[i] = fill_b if values_b is None else values_b[ib]
            ib += 1
    return result, result_idx


def merge_series(a: pd.Series, b: pd.Series, drop_duplicates=False) -> pd.Series:
    x, x_idx = array_merge(a.index.values, a.values, b.index.values, b.values)
    result = pd.Series(data=x, index=x_idx)
    if drop_duplicates:
        result = result[~result.index.duplicated(keep="first")]
    return result


@njit()
def cumsum_nonzero(x):
    """cumsum non-zero values, resetting when zero is found"""
    r = x.copy()
    cs = 0
    for i in range(len(x)):
        if x[i] == 0:
            cs = 0
        else:
            cs += x[i]
        r[i] = cs
    return r


def reduce_by_index(data: pd.Series | np.ndarray, idx: np.ndarray, func: Callable) -> pd.Series:
    """reduce data by idx (where idx values are equal)"""
    ridx = np.unique(idx)

    if not isinstance(data, np.ndarray):
        data = data.values
        series = True
    else:
        series = False

    result = _reduce_by_index(data, idx, ridx, func)
    return pd.Series(result, index=ridx) if series else result


@njit()
def _reduce_by_index(data, idx, ridx, func: Callable):
    result = np.full(len(ridx), data[0])

    ri, di = 0, 0
    while di < len(idx):
        found = False
        while di < len(idx) and ridx[ri] == idx[di]:
            if not found:
                result[ri] = data[di]
                found = True
            else:
                result[ri] = func(result[ri], data[di])
            di += 1
        ri += 1

    return result


@njit()
def combine_by_index(a: np.ndarray, a_idx: np.ndarray, b: np.ndarray, b_idx: np.ndarray, func) -> np.ndarray:
    """
    combine two arrays based on some index
    can be used as group-by across multiple arrays
    """

    idx = np.union1d(a_idx, b_idx)
    result = np.full(len(idx), a[0])
    i, ai, bi = 0, 0, 0
    while i < len(idx):
        found = False
        while ai < len(a_idx) and a_idx[ai] <= idx[i]:
            if a_idx[ai] == idx[i]:
                if found:
                    result[i] = func(result[i], a[ai])
                else:
                    found = True
                    result[i] = a[ai]
            ai += 1

        while bi < len(b_idx) and b_idx[bi] <= idx[i]:
            if b_idx[bi] == idx[i]:
                if found:
                    result[i] = func(result[i], b[bi])
                else:
                    found = True
                    result[i] = b[bi]
            bi += 1

        i += 1
    return result


def take_single(f: pd.DataFrame, col: str, ensure: str = None):
    if len(f) == 1:
        item = f[col][0]
        if hasattr(item, "tolist"):
            item = item.tolist()
        return item

    if ensure:
        raise Exception(f"{len(f)} rows for {ensure}")

    return None


def deduplicate_index_by_column(index, column):
    if not isinstance(index, np.ndarray):
        index = index.values

    if not isinstance(column, np.ndarray):
        column = column.values

    result = np.full(len(index), False)
    _deduplicate_index_by_column(index, column, result)
    return result


@njit()
def _deduplicate_index_by_column(index, column, result):
    """
    given an index that has duplicates, deduplicate by max value of different column
    faster version of: data.loc[data.groupby(data.index)["column_name"].idxmax().values]
    """
    max_index = 0
    for i in range(1, len(index)):
        if index[max_index] != index[i]:
            result[max_index] = True
            max_index = i
        else:
            if column[i] > column[max_index]:
                result[max_index] = False
                max_index = i
            else:
                result[i] = False
    result[max_index] = True


def ensure_numpy(collection, target_dtype):
    """
    Ensures that the object is a NumPy array with the specified dtype.
    If the object is not of the correct type, it is converted.
    """
    if not isinstance(collection, np.ndarray):
        collection = np.array(collection, dtype=target_dtype)
    elif collection.dtype != target_dtype:
        collection = collection.astype(target_dtype)
    return collection


def apply_non_nan(source, target):
    """
    where target is nan or missing, apply values from source
    """
    prefix = target[target.index < source.index[0]]
    target = target.reindex(source.index)
    target[missing] = source[missing := target.isna()]
    return pd.concat([prefix, target], axis=0)


def floor_toward_zero(df: pd.Series | pd.DataFrame, inplace=False):
    if not inplace:
        df = df.copy()
    positive = df.values > 0
    df[positive] = np.floor(df[positive].values)
    df[~positive] = np.ceil(df[~positive].values)
    return df


def is_dttm(col):
    if col.dtype.kind == "M":
        return True

    if col.dtype.kind == "O":
        for v in col.values:
            if v is not None:
                return isinstance(v, (datetime.date, datetime.datetime))

    return False


def display_dttm(col, dttm_format="%Y-%m-%d %H:%M", dt_format="%Y-%m-%d"):
    if col.dtype.kind == "O":
        col = col.astype(dttms.dtype_nanos)

    if isinstance(col, pd.DatetimeIndex):
        strftime = col.strftime
    else:
        strftime = col.dt.strftime

    is_nan = np.isnan(col.values)
    if np.all(dttms.is_midnight(col.values) | is_nan):
        result = strftime(dt_format)
    else:
        result = strftime(dttm_format)

    is_epoc = col.values == dttms.epoc
    if np.any(to_empty := (is_epoc | is_nan)):
        result = result.copy()
        result[to_empty] = ""

    return result


def display_dttms(df: pd.DataFrame, dttm_format="%Y-%m-%d %H:%M", dt_format="%Y-%m-%d", exclude_columns=None):
    if isinstance(df, pd.Series):
        df = df.to_frame()

    if len(df) == 0:
        return df

    if exclude_columns is None:
        exclude_columns = []

    if is_dttm(df.index) and "index" not in exclude_columns:
        df.index = display_dttm(df.index, dttm_format, dt_format)

    for k in df.columns:
        if k not in exclude_columns:
            col = df[k]
            if is_dttm(col):
                df[k] = display_dttm(col, dttm_format, dt_format)
    return df


def concat(*tseries, axis=0):
    if len(tseries) == 1 and isinstance(tseries[0], dict):
        tseries = {k: v for k, v in tseries[0].items() if len(v) != 0}
        return pd.concat(tseries, axis=axis)

    _cls = tseries[0].__class__

    tseries = [t for t in tseries if t is not None and len(t) != 0]
    if len(tseries) == 0:
        return empty_frame() if _cls == pd.DataFrame else empty_series()

    if len(tseries) == 1:
        return tseries[0]

    return pd.concat(tseries, axis=axis)


def decode_byte_columns(df):
    for c in df.columns:
        col = df[c]
        if col.dtype == "O":
            df[c] = col.str.decode("utf-8")
    return df


def drop_consecutive_duplicates(ts: pd.Series):
    values = ts.values
    return ts[np.concatenate(([True], values[1:] != values[:-1]))]


def compile_arrays():
    # https://numba.pydata.org/numba-doc/dev/reference/types.html#arrays
    def make_readonly(a: nb.types.Array):
        # take an existing Array type and make a readonly clone
        return nb.types.Array(
            a.dtype,
            a.ndim,
            a.layout,
            readonly=True,
            aligned=a.aligned,
        )

    # is_sorted
    is_sorted.compile(nb.boolean(nb.types.NPDatetime("ns")[::1]))
    is_sorted.compile(nb.boolean(nb.types.NPDatetime("D")[::1]))
    is_sorted.compile(nb.boolean(nb.types.int64[::1]))
    is_sorted.compile(nb.boolean(nb.types.float64[::1]))

    # --- arithmetic operations ---
    # binary
    for func in [max_, min_, add, mul]:
        func.compile(nb.int64(nb.int64, nb.int64))
        func.compile(nb.float64(nb.float64, nb.float64))
        func.compile(nb.float64(nb.int64, nb.float64))

    # unary aggregators
    for func in [np_mean]:
        # float only output
        func.compile(nb.float64(nb.int64[::1]))
        func.compile(nb.float64[::1](nb.int64[:, ::1]))
        func.compile(nb.float64[:](nb.int64[::1, :]))
        func.compile(nb.float64(nb.float64[::1]))
        func.compile(nb.float64[::1](nb.float64[:, ::1]))
        func.compile(nb.float64[:](nb.float64[::1, :]))
    for func in [first, last, np_sum, np_max, np_min]:
        # same input and output types
        func.compile(nb.int64(nb.int64[::1]))
        func.compile(nb.int64[::1](nb.int64[:, ::1]))
        func.compile(nb.int64[:](nb.int64[::1, :]))
        func.compile(nb.float64(nb.float64[::1]))
        func.compile(nb.float64[::1](nb.float64[:, ::1]))
        func.compile(nb.float64[:](nb.float64[::1, :]))

    # --- series/dfs ---
    # array_merge
    idx_type_in = nb.types.NPDatetime("ns")[::1]
    val_type_in = nb.boolean[::1]
    out_type = nb.types.Tuple((val_type_in, idx_type_in))
    array_merge.compile(out_type(idx_type_in, val_type_in, idx_type_in, val_type_in, nb.types.Omitted(None)))
    array_merge.compile(
        out_type(make_readonly(idx_type_in), val_type_in, idx_type_in, val_type_in, nb.types.Omitted(None))
    )

    # slice op
    idx_type = nb.types.NPDatetime("ns")[::1]
    values_type = nb.float64[::1]
    output_type = nb.types.Tuple((values_type, idx_type))
    slice_op.compile(
        output_type(
            idx_type,
            idx_type,
            idx_type,
            values_type,
            nb.typeof(np_sum),
            values_type.dtype,
            values_type.dtype,
        )
    )

    # slice op 2d
    idx_type = nb.types.NPDatetime("ns")[::1]
    values_type = nb.float64[::1, :]
    output_type = nb.types.Tuple((nb.float64[:, ::1], idx_type))
    slice_op_2d.compile(
        output_type(
            idx_type,
            idx_type,
            idx_type,
            values_type,
            nb.typeof(np_sum),
            values_type.dtype,
            values_type.dtype,
        )
    )

    # as of operation
    for dtm_type in (nb.types.NPDatetime("ns")[::1], make_readonly(nb.types.NPDatetime("ns")[::1])):
        _asof_operation.compile(
            nb.float64[::1](
                nb.float64[::1],
                dtm_type,
                nb.float64[::1],
                nb.types.NPDatetime("ns")[::1],
                nb.typeof(add),
                nb.float64[::1],
                nb.float64,
            )
        )


if __name__ == "__main__":
    compile_arrays()
    compile_slice_frame()
