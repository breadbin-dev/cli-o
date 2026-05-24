import numpy as np
import pandas as pd

from numpy.testing import assert_array_equal
from pandas.testing import assert_series_equal, assert_frame_equal


def assert_explicit_equals(a, b):
    """
    assert that a, b are the exact same (same type, and equal)
    iterate lists / dicts
    use pandas/numpy to compare
    """
    assert isinstance(a, type(b))
    assert isinstance(b, type(a))
    if isinstance(a, np.ndarray):
        assert_array_equal(a, b)
    elif isinstance(a, pd.Series):
        assert_series_equal(a, b)
    elif isinstance(a, pd.DataFrame):
        assert_frame_equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        [assert_explicit_equals(v, b[k]) for k, v in a.items()]
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        [assert_explicit_equals(a[i], b[i]) for i in range(len(a))]
    else:
        assert a == b
