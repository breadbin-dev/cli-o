import uuid
from collections import defaultdict
import logging
import pandas as pd

import settings
from core import services, dttms
from core.dbs import sql_list
from core.io import CaptureLogs

from database.backup import compare_dbs
from core import DttmLike

_logger = logging.getLogger(__name__)


class DatabaseWidget:
    """database functions"""

    def query(self, sql: str, limit: int = 100):
        """
        query audit database
        :param sql: sql to run
        :param limit: number of rows to return
        """
        db = services.audit_db()
        if limit is not None and limit > -1:
            sql += f" limit {limit}"
        return db.query(sql)

    def tables(self, database: str = "default"):
        """
        list audit tables
        :param database: name of database
        """
        db = services.audit_db()
        where = "" if database is None else f" where database = '{database}'"
        return db.query(f"select database, table from system.tables{where}")

    def backup(self, path: str = ..., secondary: bool = False):
        """
        Perform a backup of the audit database.
        :param path: Optional relative path to place the backup (defaults to timestamp).
        :param secondary: Whether to take backup on primary or secondary database (defaults to False).
        """
        audit_db = services.audit_db_backup() if secondary else services.audit_db()
        answer = yield {
            "prompt": f"Backup database {audit_db.clickhouse_url()}?",
            "options": ["OK", "Cancel"],
        }
        if answer == "OK":

            @CaptureLogs(return_result=False)
            def _backup():
                _logger.info("Starting database backup...")
                audit_db = services.audit_db()
                audit_db.backup(path, ...)
                _logger.info("Database backup completed.")

            yield _backup()
        else:
            yield f"No action ({answer})"

    def restore(self, as_of_dttm: DttmLike = "latest", secondary: bool = False, from_host: str = ...):
        """
        Restore the audit database from a specified timestamp or from 'latest'.
        :param as_of_dttm: Timestamp or 'latest' for restore.
        :param secondary: Whether to execute restore on primary or secondary database (defaults to False).
        :param from_host: Hostname of database to restore from.
        """
        audit_db = services.audit_db_backup() if secondary else services.audit_db()
        if not secondary and from_host is ...:
            from_host = settings.secondary_host
        backup_pth, disk_name, pth = audit_db.backup_paths(from_host)
        answer = yield {
            "prompt": f"Restore database {audit_db.clickhouse_url()} from {backup_pth}?",
            "options": ["OK", "Cancel"],
        }
        if answer == "OK":

            @CaptureLogs(return_result=False)
            def _restore():
                _logger.info("Starting database restore...")
                audit_db.restore(as_of_dttm, from_host)
                _logger.info("Database restore completed.")

            yield _restore()
        else:
            yield f"No action ({answer})"

    @CaptureLogs(return_result=False)
    def compare(self):
        """
        Compare the live audit database and the restore database.
        Raises an exception if they differ.
        """
        return compare_dbs()

    def list_backups(self, secondary: bool = False, disk: str = ...):
        """
        List All Backups
        :param secondary: Whether to list backups on primary or secondary database (defaults to False).
        :param disk: Which directory from db config to list backups from.
        """
        audit_db = services.audit_db_backup() if secondary else services.audit_db()
        if secondary and disk is ...:
            disk = settings.secondary_host
        return audit_db.list_backups(disk)

    def duplicate_rows(self, tables: list[str] = ..., verbose: bool = False):
        """
        Identifies rows that are duplicated based on the primary key in the specified tables.

        This method queries the database to detect rows with duplicate values for the primary key in each table.
        By default, it checks all tables except certain excluded ones. You can also specify a list of tables
        to check explicitly. If duplicates are found, the method returns a DataFrame summarizing the results
        :param tables: Optional list of tables to check
        :param verbose: Show duplicated rows
        """
        db = services.audit_db()
        table_meta_data = db.table_metadata(False)

        if tables is not ...:
            missing_tables = [x for x in tables if x not in table_meta_data]
            if missing_tables:
                raise Exception(f"Some tables do not exist: {missing_tables}. Choose from {", ".join(table_meta_data)}")
            table_meta_data_filt = {k: v for k, v in table_meta_data.items() if k in tables}
        else:
            exclude_tables = {"mo_pnl"}
            table_meta_data_filt = {k: v for k, v in table_meta_data.items() if k not in exclude_tables}

        sql_template = (
            "SELECT {primary_key}, count(*) as count FROM {table} GROUP BY {primary_key} HAVING COUNT(*) > 1;"
        )

        list_dupes = []
        for table in table_meta_data_filt.values():
            if table.primary_key:
                dupes = db.query(sql_template.format(table=table.name, primary_key=table.primary_key))
                dupes["table"] = table.name
                if not dupes.empty:
                    keys = table.primary_key.split(",")
                    keys = [x.strip() for x in keys]
                    dupes["value"] = dupes[keys].astype(str).agg(", ".join, axis=1)
                    dupes["key"] = table.primary_key
                    dupes = dupes.drop(keys, axis=1)
                    list_dupes.append(dupes)

        if len(list_dupes) == 0:
            return pd.DataFrame()

        df = pd.concat(list_dupes)
        df = df[["table", "key", "value", "count"]]

        if not verbose:
            df = df.groupby(["table"])["key"].count().to_frame()
            df = df.reset_index().rename(columns={"key": "Num. Duplicate Keys"})

        return df

    def remove_duplicates(self, tables: list[str], commit: bool = False) -> pd.DataFrame:
        """
        Remove duplicates rows from specified tables based on primary key
        :param tables: List of tables
        :param commit: Commit deletion
        """
        db = services.audit_db()
        table_meta_data = db.table_metadata(True)

        missing_tables = [x for x in tables if x not in table_meta_data]
        if missing_tables:
            raise Exception(f"Some tables do not exist: {missing_tables}. Choose from {", ".join(table_meta_data)}")

        sql_template_temp = "CREATE TABLE {temp_name} as {table_name};"
        sql_template_insert = "INSERT INTO {temp_name} SELECT DISTINCT ON ({primary_key}) * FROM {table_name};"

        rows_count = []
        for table in table_meta_data.values():
            if table.name in tables:
                if not table.primary_key:
                    raise Exception(f'Table "{table}" has no primary key.')

                temp_name = f"temp_{table.name}_{uuid.uuid4()}".replace("-", "_")
                count_before = db.query(f"SELECT COUNT() count FROM {table.name};").at[0, "count"]

                # Create de-duplicated table with exact same schema
                db.query(sql_template_temp.format(temp_name=temp_name, table_name=table.name))
                db.query(
                    sql_template_insert.format(
                        temp_name=temp_name, table_name=table.name, primary_key=table.primary_key
                    )
                )

                # Count rows, rename and drop if required
                count_after = db.query(f"SELECT COUNT() count FROM {temp_name};").at[0, "count"]
                if commit:
                    temp_name_drop = f"temp_{table.name}_{uuid.uuid4()}".replace("-", "_")
                    db.query(f"RENAME TABLE {table.name} TO {temp_name_drop}, {temp_name} TO {table.name};")
                    db.query(f"DROP TABLE {temp_name_drop};")
                else:
                    db.query(f"DROP TABLE {temp_name};")
                rows_count.append({"table_name": table.name, "count_before": count_before, "count_after": count_after})

        df = pd.DataFrame.from_records(rows_count)
        return df

    def table_metadata(self, writable: bool = False, refresh: bool = True):
        """
        View table metadata
        :param writable: Whether to use writable connection
        :param refresh: Whether to refresh table metadata
        """
        db = services.audit_db()
        if refresh:
            db.table_metadata.cache_clear()
        meta = db.table_metadata(writable)
        return pd.DataFrame(meta.values())

    def last_updated(
        self,
        tables: list[str] = ...,
        allowed_time: DttmLike = "1BD",
        errs: bool = False,
        extended_time: DttmLike = "10BD",
        extended_time_tables: list[str] = ...,
    ) -> pd.DataFrame:
        """
        Check when each table was last updated by looking for the max timestamp
        in its primary key (datetime64 columns or uses updated_dttm is present).

        :param tables: List of tables to check
        :param allowed_time: How "old" the data can be before being flagged, defaults to 1 business day.
        :param errs: If True, only return rows that exceed allowed_time.
        :param extended_time: How "old" the data can be for slow updating tables, defaults to 10 business days.
        :param extended_time_tables: List of slow updating tables
        :return: DataFrame with columns [table, datetime_column, last_update, diff, flagged]
        """
        if allowed_time:
            allowed_time = dttms.parse_period(allowed_time)
        if extended_time:
            extended_time = dttms.parse_period(extended_time)
        if extended_time_tables is ...:
            extended_time_tables = ["asset_resolution", "mo_pnl"]

        db = services.audit_db()
        table_meta = db.table_metadata(False)

        if tables is not ...:
            missing_tables = [x for x in tables if x not in table_meta]
            if missing_tables:
                raise ValueError(
                    f"The following tables do not exist: {missing_tables}. "
                    f"Available tables: {', '.join(table_meta.keys())}"
                )
            table_meta_filt = {k: v for k, v in table_meta.items() if k in tables}
        else:
            exclude_tables = {
                "user_action",
                "user_token",
            }
            table_meta_filt = {k: v for k, v in table_meta.items() if k not in exclude_tables}

        pks = db.query(
            f"SELECT *, CASE WHEN name = 'updated_dttm' THEN 0 ELSE 1 END is_updated_dttm FROM"
            f" system.columns"
            f" WHERE table IN {sql_list(table_meta_filt)}"
            f" AND (is_in_primary_key or name = 'updated_dttm')"
            f" AND datetime_precision is not null"
            f" ORDER BY table, is_updated_dttm, position"
        )
        dttm_pk = defaultdict(list)

        for _, row in pks.iterrows():
            dttm_pk[row["table"]].append(row["name"])

        if missing := table_meta_filt.keys() - dttm_pk.keys():
            raise ValueError(f"Some tables do not have a datetime like column: {missing}")

        results = []
        for table_name, dt_pks in dttm_pk.items():
            max_dttm_i = dttms.epoc
            for dt_pk in dt_pks:
                max_dttm_i = max(
                    max_dttm_i, db.query(f"SELECT CAST(MAX({dt_pk}) AS DATETIME64) max FROM {table_name};").at[0, "max"]
                )
                if dt_pk == "updated_dttm":
                    break
            results.append({"Table": table_name, "Last Update": max_dttm_i})

        df = pd.DataFrame.from_records(results).set_index("Table")
        df["Cutoff"] = dttms.now() - allowed_time
        if len(extended_time_tables := df.index.intersection(extended_time_tables)):
            df.loc[extended_time_tables, "Cutoff"] = dttms.now() - extended_time
        df["Is Err"] = df["Last Update"] < df["Cutoff"]
        df = df.reset_index()

        if errs:
            df = df.loc[df["Is Err"], :]
        return df


if __name__ == "__main__":

    def main():
        import logging
        import settings
        from core.widget import WidgetWrapper

        logging.info(settings.process_descriptor())
        router = services.router_client()
        WidgetWrapper.host_object("db", DatabaseWidget(), router)

    main()
