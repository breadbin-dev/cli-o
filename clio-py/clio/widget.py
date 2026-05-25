import grp
import json
import logging
import os
import types
from typing import Literal, Callable

import numpy as np
import pandas as pd

from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.io as pio

from websocket import WebSocketConnectionClosedException, WebSocketBadStatusException

from clio.args import function_arg_parser, hidden_args, dir_functions
from clio.arrays import display_dttms
from clio.process import ShutdownHandler
from clio.router import RouterClient


_logger = logging.getLogger(__name__)


# settings
chart_context: Literal["mpl", "mpld3", "plotly"] = "plotly"
artifact_location = None
artifact_url = None
artifact_ugroup = None


_prompts = {}


def _result(type_: str, result):
    return json.dumps({"type": type_, "result": result})


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
        if target_col not in df:
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
        doc = obj.__doc__
        if doc is None:
            doc = obj.__class__.__name__ + " functions"
        else:
            doc = doc.strip()
        descriptions = {queue: doc}
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
        if chart_context == "plotly":
            pd.options.plotting.backend = "plotly"
            pio.templates.default = "simple_white"

        shutdown = ShutdownHandler()

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
            _logger.info(f"call to {self.name} [{username}:{call_id}]: {args}")
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
            _logger.info(f"responded to {self.name} [{username}:{call_id}]: {len(result)}")
        except Exception as ex:
            _logger.exception(f"problem on {self.name} [{username}:{call_id}]: {args}")
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
                font={"family": "Courier New", "size": 12},
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
            fig = result.figure
            plt.tight_layout()
            if chart_context == "mpld3":
                import mpld3

                margin = 0.05
                fig.set_size_inches(12 - margin, 4.5 - margin)
                html = mpld3.fig_to_html(fig, template_type="simple")
                plt.close(fig)
                return _result("chart", html)
            else:
                if artifact_url is None or artifact_location is None:
                    raise Exception("artifact_url or artifact_location not provided")

                fig.set_size_inches(16, 6)
                fig.set_dpi(96)
                image_id = f"{username}_{call_id}"
                image_name = f"{image_id}.png"
                fig.patch.set_alpha(0)
                fig.savefig(file := f"{artifact_location}{image_name}", dpi=72)

                img_attrs = f"src='{artifact_url}{image_name}'"
                img_contents = ""

                plt.close(fig)
                if artifact_ugroup:
                    os.chown(file, -1, grp.getgrnam(artifact_ugroup)[2])
                os.chmod(file, 0o755)
                return _result("html", f"<center><img {img_attrs}/>{img_contents}</center>")

        raise Exception(f"Unknown result type: {type(result)}")

    def clickable_image(self, locations, image_id):
        areas = [f"<area shape='rect' coords='{v[0]},{v[1]},{v[2]},{v[3]}' {k}/>" for k, v in locations.items()]
        return f"<map name='{image_id}'>{''.join(areas)}</map>"


if __name__ == "__main__":

    def main():
        import plotly.express as px

        class Demo:
            """demo functions docstring"""

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
                df1 = px.data.gapminder().query("country in ['Canada']")
                df2 = px.data.gapminder().query("country in ['Italy']")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df1["lifeExp"], y=df1["gdpPercap"], mode="lines", name="Canada"))
                fig.add_trace(go.Scatter(x=df2["lifeExp"], y=df2["gdpPercap"], mode="lines", name="Italy"))
                return fig

            def test_df(self):
                """
                a dataframe
                """
                df = pd.DataFrame({"a": ["a", "b", "c"], "b": [1.0, 2.444, 444.0]})
                return df

        router = RouterClient("http://localhost:4010", "dev-token")
        WidgetWrapper.host_object("demo", Demo(), router)

    main()
