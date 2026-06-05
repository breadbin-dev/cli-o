import logging
import sys
from typing import Literal

import plotly.express as px
import plotly.graph_objs as go

from matplotlib import pyplot as plt

import clio
from clio.router import RouterClient
from clio.widget import WidgetWrapper, DFDecorator


"""
Demo Widget to show basic cli-o functionality.

When hosted as a widget these functions will automatically become command line functions on the 'demo' queue.
The pydocs will serve as the documentation of the cli functions and their args.
Hidden args are optionally used to provide additional functionality.
"""


class Demo:
    """demo functions docstring - [use to describe your component]"""

    def func(self, an_arg: str = "", _username: str = None):
        """
        test function takes a string as argument, uses the hidden property _username to get the calling user
        :param an_arg: an example string arg
        """
        return f"'{an_arg}' is {len(an_arg)} long from [{_username}]"

    def chart(
        self,
        mode: Literal["plotly", "mpl", "mpld3"] = "plotly",
        country: str = "United Kingdom",
        vs: str = "United States",
    ):
        """
        return a demo chart using different charting libraries
        :param mode: 'plotly' (preferred), 'mpl' (images/artifacts), or 'mpld3' (conversion for mpl)
        :param country: country of interest
        :param vs: comparison country
        """
        df = px.data.gapminder()
        df1 = df[df["country"] == country]
        df2 = df[df["country"] == vs]

        if mode == "plotly":  # plotly is generally nicer in a web page that matplotlib
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df1["lifeExp"], y=df1["gdpPercap"], mode="lines", name=country))
            fig.add_trace(go.Scatter(x=df2["lifeExp"], y=df2["gdpPercap"], mode="lines", name=vs))
            fig.update_layout(
                margin={"l": 30, "r": 30, "t": 30, "b": 30},
            )
            return fig
        elif mode == "mpld3" or mode == "mpl":
            clio.widget.chart_context = mode
            fig, ax = plt.subplots()
            ax.plot(df1["gdpPercap"], df1["lifeExp"], color="green")
            ax.plot(df2["gdpPercap"], df2["lifeExp"], color="red")
            return ax
        else:
            raise Exception(f"Invalid mode [{mode}]")

    def dataframe(
        self,
        groups: bool = False,
        aggregation: bool = False,
        links: bool = False,
        drilldown: bool = False,
        _decorator: DFDecorator = None,
    ):
        """
        return a demo dataframe, flags to enable different cli-o functionality
        :param groups: group data by continent
        :param aggregation: aggregate by continent
        :param links: provide external links (to google)
        :param drilldown: provide links to command functions
        """
        df = px.data.gapminder()

        if _decorator:
            if aggregation:
                df = df[df["year"] == 2007][["continent", "country", "pop"]].rename(columns={"pop": "population"})
                _decorator.add(df, "population", agg_func="sum")
                groups = True

            if groups:
                # group by 'continent'
                _decorator.add(df, "continent", group_by=True)
            else:
                # add text filter for continent/country
                _decorator.text_filter(df, ["country", "continent"])

            if links:
                _decorator.link(df, "https://www.google.com/search?q=%s", "country")

            if drilldown:
                _decorator.drill(df, "demo.chart -c %s", "country")

        return df

    def prompt(self, question: str = "are you sure?", options: list[str] = ["yes", "no"]):
        """
        Example of seeking confirmation for an action
        :param question: question to ask
        :param options: list of options
        """
        response = yield {"prompt": question, "options": options}
        return f"you answered: {response}"


if __name__ == "__main__":

    def main():
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stdout,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

        # if using matplotlib, charts are exported to artifact files, these need to be on the web server
        # clio.widget.artifact_url = "/artifacts/"
        # clio.widget.artifact_location = "/usr/share/nginx/html/clio-web/artifacts/"

        router = RouterClient("http://localhost:8085", "dev-token")
        WidgetWrapper.host_object("demo", Demo(), router)

    main()
