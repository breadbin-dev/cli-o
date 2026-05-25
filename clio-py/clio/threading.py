import logging
import time
from functools import wraps
import numpy as np

from clio import dttms


class Blocking:
    """decorator to turn a function into a block call that waits for data"""

    def __init__(self, periods=...):
        if periods is ...:
            periods = ["3s", "6s", "10s"]
        self.periods = [dttms.parse_period(p) for p in periods]

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, to_dttm=None, **kwargs):
            if to_dttm is None:
                return func(*args, **kwargs)

            to_dttm = dttms.as_dttm(to_dttm)
            result = None
            for period in self.periods:
                wait_until = to_dttm + period

                if (now := dttms.now()) < wait_until:
                    millis_to_wait = (wait_until - now).astype("<m8[ms]").astype(int)
                    logging.info(f"{func.__name__} waiting {millis_to_wait}ms")
                    time.sleep(millis_to_wait / 1_000)

                result = func(*args, to_dttm=to_dttm, **kwargs)

                if (not result.empty) and np.any(result.index.values >= to_dttm):
                    break

            return result

        return wrapper
