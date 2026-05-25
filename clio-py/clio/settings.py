def get_script_type():
    try:
        from IPython import get_ipython

        _ipy_str = str(type(get_ipython()))
        if "zmqshell" in _ipy_str:
            return "jupyter"
        elif "terminal" in _ipy_str:
            return "ipython"
        else:
            raise Exception(f"Unknown script type {_ipy_str}")
    except Exception:
        return "terminal"
