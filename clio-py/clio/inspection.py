import inspect


def get_all_arguments(func, *args, **kwargs):
    """
    Utility function that extracts the arguments passed to a function, including default arguments not explicitly
    passed.
    https://codereview.stackexchange.com/questions/174090/decorator-to-return-default-argument-values/174105#174105

    Args:
        func:
        *args:
        **kwargs:

    Returns:
        dictionary {argument: value}
    """
    bound_arguments = inspect.signature(func).bind(*args, **kwargs)
    bound_arguments.apply_defaults()
    return bound_arguments.arguments
