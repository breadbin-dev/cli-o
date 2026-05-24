from typing import Literal

from core import DttmLike, services
from core.dbs import sql_dttms
import plotly.express as px

from core.arrays import display_dttm


def _filter_by_threshold(df, threshold, groupby, filter_type: Literal["last", "max"]):
    if filter_type == "max":
        filters = df.groupby(groupby).agg({"used_perc": "max"})
    else:
        assert filter_type == "last"
        filters = df.groupby(groupby).tail(1).set_index(groupby)

    filters = filters[filters["used_perc"] >= threshold].index.values
    return df[df[groupby].isin(filters)]


class ServerWidget:
    """
    server monitoring
    """

    def disk(
        self,
        from_dttm: DttmLike = "now-1D",
        to_dttm: DttmLike = "now",
        verbose: bool = False,
        chart: bool = False,
        threshold: int = None,
    ):
        """
        Show Filter Usage
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param verbose: display full table contents
        :param chart: display % usage as chart
        :param threshold: % usage to filter above
        """
        db = services.audit_db()

        df = db.query(
            f"""
            select dttm, hostname, used, size, mounted_on from file_system_usage
            where {sql_dttms(from_dttm, to_dttm)}
            and (mounted_on not like '/home/%%' or mounted_on like '/home/svc%%')
            order by dttm
            """
        )
        df["mount"] = df["hostname"] + ":" + df["mounted_on"]
        df["used_perc"] = (100 * df["used"] / df["size"]).astype(int)

        if threshold:
            df = _filter_by_threshold(df, threshold, "mount", "max" if chart else "last")

        if verbose or df.empty:
            return df

        if chart:
            df = df.pivot(index="dttm", columns="mount", values="used_perc")
            fig = px.line(df, x=df.index, y=df.columns, range_y=(0, 100))
            fig.update_layout(yaxis_title="used(%)")
            return fig

        df = df.groupby("mount").tail(1).drop(columns="mount")
        df["dttm"] = display_dttm(df["dttm"])
        return df.reset_index(drop=True)

    def cpu(
        self,
        from_dttm: DttmLike = "now-10m",
        to_dttm: DttmLike = "now",
        chart: bool = False,
        verbose: bool = False,
        threshold: int = None,
    ):
        """
        Show Cpu Usage
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param verbose: display full table contents
        :param chart: display % usage as chart
        :param threshold: % usage to filter above
        """
        db = services.audit_db()
        r = db.query(f"select * from cpu_usage where {sql_dttms(from_dttm, to_dttm)}")
        if verbose:
            return r

        r["not_idle"] = -(r["cpu_idle"] - 100)

        if threshold:
            r = r[r["not_idle"] >= threshold]

        if chart:
            df = r.pivot(index="dttm", columns="hostname", values="not_idle")
            fig = px.line(df, x=df.index, y=df.columns, range_y=(0, 100))
            fig.update_layout(yaxis_title="usage(%)")
            return fig

        return r

    def load(
        self,
        from_dttm: DttmLike = "now-10m",
        to_dttm: DttmLike = "now",
        average: int = 1,
        chart: bool = False,
        verbose: bool = False,
        threshold: int = None,
    ):
        """
        Show Cpu Load Average
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param average: minutes (1, 4, 15)
        :param verbose: display full table contents
        :param chart: display % usage as chart
        :param threshold: % usage to filter above
        """
        db = services.audit_db()
        r = db.query(f"select * from cpu_usage where {sql_dttms(from_dttm, to_dttm)}")
        if verbose:
            return r

        col = f"load_avg_{average}"

        if threshold:
            r = r[r[col] >= threshold]

        if chart:
            df = r.pivot(index="dttm", columns="hostname", values=col)
            fig = px.line(df, x=df.index, y=df.columns, range_y=(0, 100))
            fig.update_layout(yaxis_title=col)
            return fig

        return r

    def memory(
        self,
        from_dttm: DttmLike = "now-10m",
        to_dttm: DttmLike = "now",
        verbose: bool = False,
        chart: bool = False,
        threshold: int = None,
    ):
        """
        Show Memory Usage
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param verbose: display full table contents
        :param chart: display % usage as chart
        :param threshold: % usage to filter above
        """
        db = services.audit_db()

        df = db.query(
            f"""
            select dttm, hostname, total, available from memory_utilisation
            where {sql_dttms(from_dttm, to_dttm)} order by dttm
            """
        )
        df["used_perc"] = (100 * (df["total"] - df["available"]) / df["total"]).astype(int)
        return self._memory(df, threshold, chart, verbose)

    def swap(
        self,
        from_dttm: DttmLike = "now-10m",
        to_dttm: DttmLike = "now",
        verbose: bool = False,
        chart: bool = False,
        threshold: int = None,
    ):
        """
        Show Swap Usage
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param verbose: display full table contents
        :param chart: display % usage as chart
        :param threshold: % usage to filter above
        """
        db = services.audit_db()

        df = db.query(
            f"""
            select dttm, hostname, swap_used, swap_total from memory_utilisation
            where {sql_dttms(from_dttm, to_dttm)} order by dttm
            """
        )
        df["used_perc"] = (100 * (df["swap_used"]) / df["swap_total"]).astype(int)
        return self._memory(df, threshold, chart, verbose)

    def _memory(self, df, threshold, chart, verbose):
        if threshold:
            df = _filter_by_threshold(df, threshold, "hostname", "max" if chart else "last")

        if verbose or df.empty:
            return df

        if chart:
            df = df.pivot(index="dttm", columns="hostname", values="used_perc")
            fig = px.line(df, x=df.index, y=df.columns, range_y=(0, 100))
            fig.update_layout(yaxis_title="used(%)")
            return fig

        df = df.groupby("hostname").tail(1).copy()
        df["dttm"] = display_dttm(df["dttm"])
        return df.reset_index(drop=True)


if __name__ == "__main__":

    def main():
        import logging
        import settings

        settings.chart_context = "plotly"
        from core.widget import WidgetWrapper

        logging.info(settings.process_descriptor())
        router = services.router_client()
        WidgetWrapper.host_object("servers", ServerWidget(), router)

    main()
