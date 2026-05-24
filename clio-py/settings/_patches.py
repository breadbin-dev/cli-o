import numpy as np
from datetime import datetime

from clickhouse_driver.columns import boolcolumn

boolcolumn.BoolColumn.null_value = False


def _as_np(x: datetime):
    return np.datetime64(x).astype("<M8[ns]")
