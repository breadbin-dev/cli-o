import grp
import json
import os
import ssl
import types

import mpld3
import numpy as np
import pandas as pd
import requests
import urllib3

from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from websocket import create_connection, WebSocketConnectionClosedException, WebSocketBadStatusException
from typing import Callable, Literal
import plotly.graph_objs as go
import plotly.io as pio
import logging

import settings
from core import services, strs
from core.args import function_arg_parser, dir_functions, hidden_args
from core.arrays import display_dttms
from settings import no_scan_logger


_no_scan_logger = no_scan_logger(f"{__name__}.no_scan")
_logger = logging.getLogger(__name__)


class RouterClient:
    def __init__(self, url: str, api_token: str):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.url = url
        self._ws = "ws" + url[4:]
        self._api_token = api_token

    def _header(self):
        return {"Authorization": f"Token {self._api_token}"}

    def subscribe(self, queue: str, desc: dict, callback: Callable):
        ws = create_connection(
            f"{self._ws}/subscribe/{queue}", sslopt={"certs_reqs": ssl.CERT_NONE}, header=self._header()
        )
        ws.send(json.dumps(desc))
        try:
            while r := ws.recv():
                callback(**json.loads(r))
        finally:
            ws.close()

    def call(self, function: str, args: str, args_type: str = "json", raw=False):
        queue = function.split(".", 1)[0]
        args = {
            "function": function,
            "args": args,
            "args_type": args_type,
        }
        result = requests.get(f"{self.url}/call/{queue}", data=strs.to_json(args), verify=False, headers=self._header())
        if result.status_code != 200:
            raise Exception(f"[{result.status_code}]: {result.reason}")
        else:
            result = result.text
            if raw:
                return result

            try:
                result = strs.from_json(result)
            except Exception:
                raise Exception(f"unhandled result: {result}")

            if result["type"] == "text":
                return result["result"]
            elif result["type"] == "err":
                raise Exception(result["result"])
            else:
                raise Exception(f"unknown result type: {result}")

    def respond(self, queue: str, caller_id: str, response: str):
        result = requests.get(
            f"{self.url}/respond/{queue}",
            params={"CallerID": caller_id},
            data=response,
            verify=False,
            headers=self._header(),
        )
        if result.status_code != 200:
            raise Exception(f"[{result.status_code}]: {result.reason}")


def _result(type_: str, result):
    return json.dumps({"type": type_, "result": result})


_prompts = {}


class DFDecorator:
    def __init__(self):
        self._cols = {}

    def _default(self, df, col, is_index=False, header=...):
        if col in self._cols:
            return self._cols[col]

        dfn = {"field": str(col).replace(".", "__"), "headerName": str(col) if header is ... else header}

        cv = df[col]
        if np.issubdtype(cv.dtype, np.integer):
            dfn["type"] = "numericColumn"
            dfn["valueFormatter"] = "int"
        elif np.issubdtype(cv.dtype, np.floating):
            dfn["type"] = "numericColumn"
            if cv.abs().mean() < 10:
                dfn["valueFormatter"] = "float5"
            else:
                dfn["valueFormatter"] = "float"
        elif np.issubdtype(cv.dtype, bool):
            dfn["cellDataType"] = "string"

        if is_index:
            dfn["cellClass"] = "index-col"
            dfn["headerClass"] = "index-header"

        self._cols[col] = dfn
        return dfn

    def add(
        self,
        df,
        col,
        html=False,
        filter=False,
        group_by=False,
        hide=...,
        formatter: Literal["int", "float", "float5"] = ...,
        agg_func: Literal["sum", "min", "max", "count", "countNonZero", "avg", "first", "last"] = None,
    ):
        dfn = self._default(df, col)
        if filter:
            dfn["filter"] = True

        if html:
            dfn["cellRenderer"] = "html"

        if hide is not ...:
            dfn["hide"] = hide

        if group_by:
            dfn["rowGroup"] = True
            if hide is ...:
                dfn["hide"] = True

        if formatter is not ...:
            dfn["valueFormatter"] = formatter

        if agg_func is not None:
            dfn["aggFunc"] = agg_func

    def ensure(self, df):
        if df.columns[0] == "index":
            self._default(df, "index", is_index=True, header="")

        return [self._default(df, c) for c in df.columns]

    def link(self, df: pd.DataFrame, url_pattern: str, target_col: str, src_func: Callable = None, target="_blank"):
        if target_col not in df:
            return

        self.add(df, target_col, html=True)
        df[target_col] = df[target_col].astype("str")

        col_i = df.columns.get_loc(target_col)
        for row_i, (_, row) in enumerate(df.iterrows()):
            url = url_pattern % (row[target_col] if src_func is None else src_func(row))
            df.iloc[row_i, col_i] = f'<a title="{url}" href="{url}" target="{target}">{row[target_col]}</a>'

    def drill(self, df: pd.DataFrame, command_pattern: str, target_col: str, src_func: Callable = None):
        if settings.script_type == "jupyter" or target_col not in df:
            return

        self.add(df, target_col, html=True)
        df[target_col] = df[target_col].astype("str")

        col_i = df.columns.get_loc(target_col)
        for row_i, (_, row) in enumerate(df.iterrows()):
            content = row[target_col]
            cmd = command_pattern % (content if src_func is None else src_func(row))
            if "href=" in cmd:
                raise Exception("nested link, consider reordering")
            df.iloc[row_i, col_i] = f'<a class="command-link" {decorate_command_link(cmd)}>{content}</a>'

    def text_filter(self, df: pd.DataFrame, cols: list[str]):
        for c in cols:
            self.add(df, c, filter=True)


def decorate_command_link(cmd):
    jscript = f"clickCommand('{cmd}', $event)"
    return f'href="{cmd}" title="{cmd}" @click="{jscript}"'


def _confirm(action: str, id: str):
    """user confirm for yielded prompt"""
    generator = _prompts.pop(id)
    try:
        r = yield generator.send(action)
        yield generator.send(r)
    except StopIteration as e:
        yield e.value


class WidgetWrapper:
    def __init__(self, router: RouterClient, queue: str, name: str, function: Callable):
        self.router = router
        self.queue = queue
        self.name = name
        self.function = function
        self.arg_parser = function_arg_parser(self.function)
        self._hidden_args = hidden_args(self.function)

    @staticmethod
    def wrap_object(queue, obj, router: RouterClient):
        functions = {}
        descriptions = {queue: obj.__doc__.strip()}
        for name, desc, func in dir_functions(obj).values():
            name = f"{queue}.{name}"
            functions[name] = WidgetWrapper(router, queue, name, func)
            descriptions[name] = desc

        # add yield confirm functionality
        confirm = f"{queue}._confirm"
        functions[confirm] = WidgetWrapper(router, queue, confirm, _confirm)

        def _call(function, call_id, **args):
            try:
                f = functions.get(function)
                if f is None:
                    router.respond(queue, call_id, _result("err", f"No such function: {function}"))
                else:
                    functions[function].call(call_id, **args)
            except Exception as ex:
                try:
                    router.respond(queue, call_id, _result("err", f"Unexpected [{function}]: {ex}"))
                except Exception as ex2:
                    _logger.exception(f"Failed to respond to caller: {ex2}")

        _logger.info(f"subscribing to [{queue}]...")
        router.subscribe(queue, descriptions, _call)

    @staticmethod
    def host_object(queue, obj, router: RouterClient):
        if settings.chart_context == "plotly":
            pd.options.plotting.backend = "plotly"
            pio.templates.default = "simple_white"

        shutdown = services.shutdown_handler()

        while True:
            try:
                WidgetWrapper.wrap_object(queue, obj, router)
            except (WebSocketConnectionClosedException, WebSocketBadStatusException, ConnectionRefusedError):
                _logger.exception("socket closed..")
                shutdown.sleep(5)
            except ConnectionResetError:
                _logger.warning("socket reset..")
                shutdown.sleep(1)
            except Exception:
                if not shutdown.killed:
                    _logger.exception("unhandled ex")
                return

    def call(self, call_id: str, args: str, username: str, args_type="text"):
        try:
            _no_scan_logger.info(f"call to {self.name} [{username}:{call_id}]: {args}")
            if args_type == "json":
                kwargs = json.loads(args)
            else:
                kwargs = self.arg_parser.parse(args)
            if "_username" in self._hidden_args:
                kwargs["_username"] = username

            _decorator = DFDecorator()
            if "_decorator" in self._hidden_args:
                kwargs["_decorator"] = _decorator

            result = self.function(**kwargs)
            result = self.convert_result(result, call_id, username, _decorator)
            self.router.respond(self.queue, call_id, result)
            _no_scan_logger.info(f"responded to {self.name} [{username}:{call_id}]: {len(result)}")
        except Exception as ex:
            _no_scan_logger.exception(f"problem on {self.name} [{username}:{call_id}]: {args}")
            self.router.respond(self.queue, call_id, _result("err", f"Problem: {ex}"))

    def convert_frame_to_ag(self, df, decorator: DFDecorator):
        if isinstance(df.index, pd.MultiIndex):
            df.columns = [" ".join(col).strip() for col in df.columns.values]

        if df.index.name is not None or not np.issubdtype(df.index.dtype, int):
            df = df.reset_index()
        else:
            df = df.reset_index(drop=True)

        cols = decorator.ensure(df)

        df.columns = [str(c).replace(".", "__") for c in df.columns]
        rows = display_dttms(df, dttm_format="%Y-%m-%d %H:%M:%S.%f").fillna("").to_dict(orient="index")
        rows["__cols__"] = cols
        return rows

    def convert_result(self, result, call_id, username, decorator):
        generator = None
        if isinstance(result, types.GeneratorType):
            generator = result
            try:
                result = next(generator)
            except StopIteration as e:
                result = e.value
        if result is None:
            return _result("text", "None")
        if isinstance(result, go.Figure):
            result.update_layout(
                {"paper_bgcolor": "rgba(0,0,0,0)"},
                legend={"font": {"size": 11}},
                font={"family": "Consolas", "size": 12},
            )
            return _result("chart", result.to_html(full_html=False, include_plotlyjs="cdn"))
        if isinstance(result, dict):
            if result.keys() == {"prompt", "options"}:
                if isinstance(result["options"], list) and generator is not None:
                    result["options"] = {v: f'{self.queue}._confirm -a "{v}" -i {call_id}' for v in result["options"]}
                    _prompts[call_id] = generator
                return _result("confirm", result)
            result = pd.DataFrame({k: [v] for k, v in result.items()})
        if isinstance(result, pd.Series):
            result = result.to_frame()
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return _result("text", "[]")
            return _result("table", self.convert_frame_to_ag(result, decorator))
        if isinstance(result, str):
            if result.startswith("<"):
                return _result("html", result)
            else:
                return _result("text", result)
        if isinstance(result, Axes):
            is_mpld3 = settings.chart_context == "mpld3"
            fig = result.figure
            plt.tight_layout()
            if is_mpld3:
                margin = 0.05
                fig.set_size_inches(12 - margin, 4.5 - margin)
                html = mpld3.fig_to_html(fig, template_type="simple")
                plt.close(fig)
                return _result("chart", html)
            else:
                fig.set_size_inches(16, 6)
                fig.set_dpi(96)
                image_id = f"{username}_{call_id}"
                image_name = f"{image_id}.png"
                fig.patch.set_alpha(0)
                fig.savefig(file := f"{settings.artifact_loc}{image_name}", dpi=72)

                img_attrs = f"src='{settings.artifact_url}{image_name}'"
                img_contents = ""

                plt.close(fig)
                if settings.usergroup:
                    os.chown(file, -1, grp.getgrnam(settings.usergroup)[2])
                os.chmod(file, 0o755)
                return _result("html", f"<center><img {img_attrs}/>{img_contents}</center>")

        raise Exception(f"Unknown result type: {type(result)}")

    def clickable_image(self, locations, image_id):
        areas = [f"<area shape='rect' coords='{v[0]},{v[1]},{v[2]},{v[3]}' {k}/>" for k, v in locations.items()]
        return f"<map name='{image_id}'>{''.join(areas)}</map>"


if __name__ == "__main__":

    def main():
        class Demo:
            """
            some demo functions
            """

            def test_func(self, an_arg: str = "", _username: str = None):
                """
                test function description
                :param an_arg: an example string arg
                """
                return f"'{an_arg}' is {len(an_arg)} long from [{_username}]"

            def test_chart(self):
                """
                a random scatter plot
                """

                df = pd.DataFrame(
                    {"a": np.random.normal(loc=1, scale=2, size=100), "b": np.random.normal(loc=2, scale=1, size=100)}
                )
                return df.plot.scatter(x="a", y="b")

            def test_df(self):
                """
                a dataframe
                """
                df = pd.DataFrame({"a": ["a", "b", "c"], "b": [1.0, 2.444, 444.0]})
                return df

        router = services.router_client()
        WidgetWrapper.host_object("demo", Demo(), router)

    main()
