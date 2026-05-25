import argparse
import inspect
import typing
from types import UnionType, NoneType
from typing import NoReturn, Literal, get_args, get_origin

from clio import DttmLike, TimeLike


_special_types = {DttmLike: "dttm", TimeLike: "time"}


def doc_to_desc(desc: str, arg_dfns):
    args = _Flags()

    def desc_type(arg_dfn):
        if arg_dfn is None:
            return ""
        _, dflt, required, clz = arg_dfn

        dflt = "" if dflt is None or dflt is ... else f"={repr(dflt)}"
        type_ = _special_types.get(clz, simplified_type(clz))

        if type_ == bool:
            return " [flag]"

        if not isinstance(type_, str):
            type_ = type_.__name__

        if get_origin(clz) == list:
            return f" list[{type_}{dflt}]"
        else:
            return f" [{type_}{dflt}]"

    def parse_arg(line: str):
        if not line.startswith(":param"):
            return line
        arg, comment = line[7:].split(":", 1)
        if arg.startswith("_"):
            return None
        flags = " ".join(args.flags(arg))
        return f" {flags}{desc_type(arg_dfns.get(arg))}:{comment}"

    desc = [line.strip() for line in desc.split("\n")]
    desc = [parse_arg(line) for line in desc if line]

    return "\n".join([d for d in desc if d])


def simplified_type(type_):
    if get_origin(type_) is UnionType or get_origin(type_) is typing.Union:
        type_ = next(x for x in get_args(type_) if x is not NoneType)

    if get_origin(type_) == Literal:
        type_ = get_args(type_)[0].__class__

    if get_origin(type_) == list:
        type_ = get_args(type_)[0]

    return type_


def dir_functions(obj):
    functions = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        fun = getattr(obj, name)
        desc = doc_to_desc(fun.__doc__, dir_args(fun)) if fun.__doc__ else "not documented"
        functions[name] = name, desc, fun
    return functions


def dir_args(fun):
    sig = inspect.signature(fun)
    args = {}
    for k, v in sig.parameters.items():
        if k.startswith("_") or k == "self":
            continue
        required = v.default is v.empty
        args[k] = k, (None if required else v.default), required, v.annotation
    return args


def hidden_args(fun):
    sig = inspect.signature(fun)
    args = {}
    for k, v in sig.parameters.items():
        if (not k.startswith("_")) or k == "self":
            continue
        args[k] = k, (None if v.default is v.empty else v.default), v.annotation
    return args


def split_args(args: str):
    try:
        result = []
        i, esc = 0, False
        for j in range(len(args)):
            if j < i:
                continue
            if args[j] == " " and not esc:
                result.append(args[i:j])
                i = j + 1
            elif args[j] == '"':
                if esc:
                    result.append(args[i:j])
                    i = j + 2
                    esc = False
                else:
                    assert i == j, '" should be start of token'
                    i = j + 1
                    esc = True

        assert not esc, '" not terminated'

        if i < len(args):
            result.append(args[i:])

        return result
    except Exception as ex:
        raise SyntaxError(f"unable to split [{args}]") from ex


def is_optional(type_):
    return isinstance(type_, typing._UnionGenericAlias) and type_._name == "Optional"


class ArgParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(exit_on_error=False)

    def parse(self, args: str | list[str]):
        if isinstance(args, str):
            args = split_args(args)
        return self.parse_args(args).__dict__

    def error(self, message: str) -> NoReturn:
        raise Exception(message)  # instead of exit


class _Flags:
    def __init__(self, include_hidden=False):
        self.seen = {"_"}

    def flags(self, arg):
        if arg[0] in self.seen:
            return [f"--{arg}"]
        else:
            self.seen.add(arg[0])
            return [f"-{arg[0]}", f"--{arg}"]


def function_arg_parser(fun) -> ArgParser:
    ap = ArgParser()
    args = _Flags()

    for arg, default_, required, type_ in dir_args(fun).values():
        if is_optional(type_):
            type_ = simplified_type(type_)
        if type_ == bool:
            ap.add_argument(*args.flags(arg), action="store_true")
        elif type_ == DttmLike:
            ap.add_argument(*args.flags(arg), type=str, default=default_, required=required)
        elif type_ == TimeLike:
            ap.add_argument(*args.flags(arg), type=str, default=default_, required=required)
        elif get_origin(type_) == list:
            ap.add_argument(
                *args.flags(arg), nargs="+" if required else "*", type=simplified_type(type_), default=default_
            )
        else:
            assert type_ != inspect._empty, f"type must be provided for {fun.__name__}({arg})"
            ap.add_argument(*args.flags(arg), type=simplified_type(type_), default=default_, required=required)

    class WrappedArgParser(ArgParser):
        def parse(self, args):
            kwargs = ap.parse(args)
            for k, v in kwargs.items():
                if v == "None":
                    kwargs[k] = None
                elif v == "...":
                    kwargs[k] = ...
            return kwargs

    return WrappedArgParser()
