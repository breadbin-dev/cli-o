import clio_services
from clio import DttmLike, dttms
from clio.dbs import sql_dttms


class ServicesWidget:
    """
    Services monitoring
    """

    def status(
        self,
        from_dttm: DttmLike = "now-1BD",
        to_dttm: DttmLike = "now",
        name: str = None,
        errs: bool = False,
        verbose: bool = False,
        stale_cutoff: DttmLike | None = "10m",
    ):
        """
        Show status of system clio_services

        :param from_dttm: Start datetime for the query range.
        :param to_dttm: End datetime for the query range.
        :param name: Name of the service to filter by.
        :param errs: If True, filter for records with errs only (running = 0 or connected = 0).
        :param verbose: If True, return all rows. If False, return only most recent for each service.
        :param stale_cutoff: Records older than this datetime will be flagged as stale.
        """
        cutoff_time = None
        if stale_cutoff:
            cutoff_time = dttms.parse_period(stale_cutoff)

        to_dttm = dttms.as_dttm(to_dttm)
        where_clause = f"WHERE {sql_dttms(from_dttm, to_dttm)}"
        if name:
            where_clause += f" AND name = '{name}'"

        if verbose:
            query = f"""
                    SELECT dttm, name, CAST(running as INTEGER) running, CAST(connected as INTEGER) connected
                    FROM service_status
                    {where_clause}
                    ORDER BY dttm DESC
                """
        else:
            query = f"""
                    WITH ranked_services AS (
                        SELECT dttm, name, running, connected,
                               ROW_NUMBER() OVER (PARTITION BY name ORDER BY dttm DESC) AS rnk
                        FROM service_status
                        {where_clause}
                    )
                    SELECT dttm, name, CAST(running as INTEGER) running, CAST(connected as INTEGER) connected
                    FROM ranked_services
                    WHERE rnk = 1
                    ORDER BY dttm DESC
                """

        db = clio_services.audit_db()
        df = db.query(query).astype({"running": bool, "connected": bool})
        cols = ["dttm", "name", "running", "connected"]
        if stale_cutoff:
            df["stale_cutoff"] = df["dttm"] - cutoff_time
            df["next_cutoff"] = df.groupby("name")["stale_cutoff"].shift(1)
            df["next_cutoff"] = df["next_cutoff"].fillna(to_dttm - cutoff_time)
            df["is_stale"] = df["dttm"] < df["next_cutoff"]
            df["is_error"] = ~df["running"] | ~df["connected"] | df["is_stale"]
            cols.append("is_stale")
        else:
            df["is_error"] = ~df["running"] | ~df["connected"]
        cols.append("is_error")

        df = df.sort_values("dttm")
        df = df[cols]

        if errs:
            df = df.loc[df["is_error"]]
        return df


if __name__ == "__main__":

    def main():
        from clio.widget import WidgetWrapper

        router = clio_services.router_client()
        WidgetWrapper.host_object("clio_services", ServicesWidget(), router)

    main()
