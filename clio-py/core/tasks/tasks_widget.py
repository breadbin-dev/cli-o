from core import DttmLike, services
from core.dbs import sql_dttms
from core.tseries import display_dttms


class TasksWidget:
    """
    scheduled tasks and checks
    """

    def status(
        self,
        from_dttm: DttmLike = "now-5D",
        to_dttm: DttmLike = "now",
        verbose: bool = False,
        errs: bool = False,
        _decorator=None,
    ):
        """
        current status of tasks
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param verbose: display full table contents
        :param errs: filter for problems
        :param _decorator: hints for rendering the result
        """

        db = services.audit_db()
        df = db.query(
            f"""
            select * from task_status
            where {sql_dttms(from_dttm, to_dttm)} order by dttm
            """
        )

        if verbose or df.empty:
            return df

        df = df.groupby("name").tail(1).copy()
        display_dttms(df)

        if _decorator is not None:
            df["action"] = ["run"] * len(df)
            _decorator.drill(df, "tasks.run -t &quot;%s&quot;", "action", lambda r: r["name"])

        if errs:
            df = df[df["previous_result"] == "Problem"]

        return df.reset_index(drop=True)


if __name__ == "__main__":

    def main():
        import logging
        import settings
        from core.router import WidgetWrapper

        logging.info(settings.process_descriptor())
        router = services.router_client()
        WidgetWrapper.host_object("tasks", TasksWidget(), router)

    main()
