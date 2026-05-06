# flake8: noqa
import configparser
import subprocess
import types
import socket
import getpass
import importlib

from IPython import get_ipython

from settings._defaults import *
from settings._defaults import __throw

from settings._logging import *
from settings._patches import *


def _all_settings(_vars=...):
    if _vars is ...:
        _vars = globals().copy()
    return {
        n: v
        for n, v in _vars.items()
        if not n.startswith("__") and not isinstance(v, types.ModuleType) and not isinstance(v, types.FunctionType)
    }


def _get_script_type():
    try:
        _ipy_str = str(type(get_ipython()))
        if "zmqshell" in _ipy_str:
            return "jupyter"
        elif "terminal" in _ipy_str:
            return "ipython"
        else:
            raise Exception(f"Unknown script type {_ipy_str}")
    except:
        return "terminal"


if not globals().get("_settings_recurse"):  # subsequent imports will also get here
    hostname = socket.gethostname().split(".")[0].lower()
    username = getpass.getuser()
    process_name = sys.argv[0].rsplit("/", maxsplit=1)[-1]
    script_type = _get_script_type()

    def _resolve_module(location):
        try:
            module = importlib.import_module(location)
            globals().update(_all_settings(vars(module)))
        except ModuleNotFoundError:
            pass

    def _resolve_config(location):
        try:
            config = configparser.RawConfigParser()
            config.read(location)

            for s in config.sections():
                globals().update({k: v for k, v in config.items(s)})

        except FileNotFoundError:
            pass

    globals()["_settings_recurse"] = True
    _resolve_module(f"settings.consoles.{script_type}")
    _resolve_module(f"settings.hosts.{hostname}")
    _resolve_module(f"settings.users.{username}")
    globals().pop("_settings_recurse")

    _resolve_config(f"{user_home}/.clio/credentials.config")

    def _validate():
        missing = [n for n, v in _all_settings().items() if v == __throw]
        if missing:
            raise SystemError(f"Missing mandatory configuration {missing}")

    if version == __throw:
        try:
            version = (
                subprocess.check_output(["git", "describe", "--always"], stderr=subprocess.DEVNULL)
                .decode("utf-8")
                .strip()
            )
        except:
            version = "unknown"

    if __name__ == "__main__":

        def _main():
            for n, v in _all_settings().items():
                print(f"{n} = {v!r}")

        _main()

    _validate()


def process_descriptor():
    return f"{username}@{hostname}[{env}] {process_name}"
