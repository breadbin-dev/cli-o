from math import ceil, floor


def floor_to_zero(n, step=1.0, epsilon=0.001):
    if n < 0:
        return -1 * floor_to_zero(-n, step=step, epsilon=epsilon)

    n += epsilon
    if step != 1.0:
        return floor(n / step) * step
    else:
        return floor(n)


def ceil_to_zero(n, step=1.0, epsilon=0.001):
    if n < 0:
        return -1 * ceil_to_zero(-n, step=step, epsilon=epsilon)

    n -= epsilon
    if step != 1.0:
        return ceil(n / step) * step
    else:
        return ceil(n)
