import dataclasses
import subprocess
import enum
import functools
import uuid
import re
import logging
from contextlib import contextmanager
from enum import IntEnum
from itertools import repeat
from time import sleep
from collections import defaultdict
from pathlib import Path
from dataclasses import fields

import numpy as np
import pandas as pd
from typing import TypeVar, Type

from clickhouse_driver import Client

import settings
from core import dttms, strs, DttmLike, format_dttm
from core.collections import ensure_list
from core.strs import ProgressBar, parse_readable_mem, GB

_logger = logging.getLogger(__name__)


def _format_field(field, val):
    if val is None:
        return "null"

    if field.type == np.datetime64 or field.type == DttmLike:
        if field.name.endswith("_dt"):
            return f"'{dttms.format_dt_sql(val.astype(dttms.dtype_days))}'"
        else:
            return f"'{dttms.format_dttm_sql(val)}'"

    if field.type == uuid.UUID:
        return f"'{val}'"

    if issubclass(type(field.type), type) and issubclass(field.type, enum.Enum):
        if issubclass(type(type(val)), type) and issubclass(type(val), enum.Enum):
            # val is enum
            val = val.value

    return f"{val!r}"


def _format_param(val):
    if val is None:
        return "null"

    if isinstance(val, np.datetime64):
        if val.dtype == dttms.dtype_days:
            return f"'{dttms.format_dt_sql(val)}'"
        else:
            return f"'{dttms.format_dttm_sql(val)}'"

    _type = type(val)
    if _type == uuid.UUID:
        return f"'{val}'"

    if issubclass(type(_type), type) and issubclass(_type, enum.Enum):
        # val is enum
        val = val.value

    return f"{val!r}"


def sql_dttms(from_dttm: DttmLike, to_dttm: DttmLike, field: str = "dttm", left_exclusive=True):
    from_dttm = dttms.as_dttm(from_dttm, from_dttm=True)
    if left_exclusive:
        from_dttm += dttms.a_nano
    to_dttm = dttms.as_dttm(to_dttm, to_dttm=True)
    return f"{field} between '{dttms.format_dttm_sql(from_dttm)}' and '{dttms.format_dttm_sql(to_dttm)}'"


def sql_optional_dttms(from_dttm: DttmLike, to_dttm: DttmLike, field: str = ..., left_exclusive=True):
    if from_dttm is None and to_dttm is None:
        return "1=1"

    if field is ...:
        field = "dttm"

    if from_dttm is None:
        to_dttm = dttms.as_dttm(to_dttm, to_dttm=True)
        return f"{field} <= '{dttms.format_dttm_sql(to_dttm)}'"

    if to_dttm is None:
        from_dttm = dttms.as_dttm(from_dttm, from_dttm=True)
        return f"{field} {'>' if left_exclusive else '>='} '{dttms.format_dttm_sql(from_dttm)}'"

    return sql_dttms(from_dttm, to_dttm, field=field, left_exclusive=left_exclusive)


def sql_optional_list(field, items):
    items = ensure_list(items)
    if len(items) == 1:
        item = items[0]
        eq = "like" if isinstance(item, str) and "%" in item else "="
        return f"{field} {eq} {_format_param(item)}"
    else:
        return f"{field} in {sql_list(items)}"


def sql_clauses(
    from_dttm: DttmLike = None,
    to_dttm: DttmLike = None,
    dttm_field: str = ...,
    join_by=" and ",
    order_by="dttm desc",
    **optional_fields,
):
    clauses = []
    if from_dttm or to_dttm:
        clauses += [sql_optional_dttms(from_dttm, to_dttm, field=dttm_field)]

    clauses += [sql_optional_list(k, v) for k, v in optional_fields.items() if v is not None and v is not ...]

    if len(clauses) == 0:
        clauses = "1=1"
    else:
        clauses = join_by.join(clauses)

    if order_by is not None:
        clauses += f" order by {order_by}"

    return clauses


def sql_asof(as_of_dttm: DttmLike):
    dttm = dttms.format_dttm_sql(dttms.as_dttm(as_of_dttm))
    return f"asserted_from <= '{dttm}' and (asserted_to is null or asserted_to > '{dttm}')"


def sql_dt(dt: DttmLike):
    return f"'{dttms.format_dt_sql(dttms.as_date(dt))}'"


def sql_dts(from_dt: DttmLike, to_dt: DttmLike, field: str = "date"):
    from_dt = dttms.as_date(from_dt)
    to_dt = dttms.as_date(to_dt)
    return f"{field} between '{dttms.format_dt_sql(from_dt)}' and '{dttms.format_dt_sql(to_dt)}'"


def sql_list(items):
    return "(" + ",".join([_format_param(i) for i in items]) + ")"


def sql_list_regex_match(col_names: list[str] | str, patterns: list[str], seperator: str = " and "):
    match col_names:
        case list():
            if len(col_names) != len(patterns):
                raise ValueError("col_names and items must have same length.")
        case str():
            col_names = repeat(col_names, len(patterns))
        case _:
            raise TypeError("col_names must be a list or str.")
    return seperator.join(f"match({col_name}, {repr(pattern)})" for col_name, pattern in zip(col_names, patterns))


def sql_tree_filter(items, columns):
    """
    build a sql filter from items that _may_ contain ':' separated tree filter
    e.g. BONDS:RX1 where *columns would be ['mstrat', 'asset']
    """
    full_filters = defaultdict(list)
    conditional_filters = []
    for item in items:
        if ":" not in item:
            full_filters[columns[0]].append(item)
        else:
            ix = {columns[i]: x for i, x in enumerate(item.split(":")) if x != "*"}
            conditional_filters.append(ix)

    conditions = []
    for k, v in full_filters.items():
        if len(v) == 1:
            conditions.append(f"{k}={repr(v[0])}")
        else:
            conditions.append(f"{k} in {sql_list(v)}")

    for cf in conditional_filters:
        cf = " and ".join([f"{k}={repr(v)}" for k, v in cf.items()])
        conditions.append(f"({cf})")

    return " or ".join(conditions)


_dtypes = {
    "DateTime64(9)": lambda data: np.array(data, dtype=dttms.dtype_nanos),
    "Date": lambda data: np.array(data, dtype=dttms.dtype_days),
}


T = TypeVar("T")


@dataclasses.dataclass
class TableMetaData:
    database: str
    name: str
    engine: str
    partition_key: str
    sorting_key: str
    primary_key: str
    create_table_query: str


class Database:
    def __init__(self, connection, write_connection=...):
        self.connection = connection
        self.write_connection = write_connection

    def __repr__(self):
        return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1***\3", self.connection)  # replace password with ***

    @contextmanager
    def stop_merges(self):
        self._client(True).execute(f"SYSTEM STOP MERGES {self._client(True).connection.database};")
        yield
        self._client(True).execute(f"SYSTEM START MERGES {self._client(True).connection.database};")

    @functools.cache
    def table_metadata(self, writeable: bool) -> dict[str, TableMetaData]:
        db = self._client(writeable).connection.database
        sql = f"select * from system.tables where database = '{db}';"
        data = self.select(TableMetaData, sql, _writable=writeable)
        return {x.name: x for x in data}

    @functools.cache
    def _client(self, write, db: str | None = ...):
        if write and self.write_connection is not ...:
            conn = self.write_connection
        else:
            conn = self.connection
        protocol, conn = conn.split("//")
        conn, db_ = conn.rsplit("/", 1)
        creds, conn = conn.rsplit("@", 1)
        host, port = conn.split(":")
        user, pwd = creds.split(":", 1)
        if db is ...:
            db = db_
        elif db is None:
            db = ""
        return Client(host, port=int(port), user=user, password=pwd, database=db, tcp_keepalive=(60, 5, 2))

    def insert(self, obj):
        self.inserts([obj])

    def update_obj(self, obj, keys):
        self.delete_obj(obj, keys)
        self.insert(obj)

    def delete_obj(self, obj, keys):
        table_name = strs.camel_to_snake(obj.__class__.__name__)
        fields = {f.name: f for f in dataclasses.fields(obj.__class__)}
        clause = []
        for k, v in keys.items():
            clause.append(f"{k}={_format_field(fields[k], v)}")
        clause = " and ".join(clause)

        assert self.count(f"select count(*) from {table_name} where {clause}") == 1, "update should affect single item"
        self.delete(f"delete from {table_name} where {clause}")

    def inserts(self, objs):
        if not objs:
            return
        table_name = strs.camel_to_snake((cls := objs[0].__class__).__name__)
        flds = dataclasses.fields(cls)
        cols = ", ".join(f.name for f in flds)
        values_list = []
        for obj in objs:
            values = [_format_field(f, getattr(obj, f.name)) for f in flds]
            values_list.append(f"({','.join(values)})")
        sql = f"INSERT INTO {table_name}({cols}) VALUES {','.join(values_list)}"
        with self._client(True) as client:
            client.execute(sql)

    def insert_df(self, cls, df):
        table_name = strs.camel_to_snake(cls.__name__)
        fields = dataclasses.fields(cls)

        field_names = ", ".join([f.name for f in fields])
        sql = f"INSERT INTO {table_name} ({field_names}) VALUES"

        with self._client(True) as client:
            client.insert_dataframe(sql, df, settings={"use_numpy": True})

    def upsert_df(self, cls, df, index: str | list[str] = ...):
        table_name = strs.camel_to_snake(cls.__name__)
        temp_name = f"temp_{table_name}_{uuid.uuid4()}".replace("-", "_")
        fields = dataclasses.fields(cls)

        if index is ...:
            index = self.table_metadata(True)[table_name].primary_key
        elif isinstance(index, list):
            index = ", ".join(index)

        field_names = ", ".join([f.name for f in fields])
        sql_insert = f"INSERT INTO {temp_name} ({field_names}) VALUES"

        sql_tmp_table = f"CREATE TABLE {temp_name} ENGINE = Memory  AS SELECT * FROM {table_name}" f" WHERE 0;"

        delete_sql = f"DELETE FROM {table_name} WHERE ({index}) IN (SELECT {index} FROM {temp_name});"
        insert_sql = f"INSERT INTO {table_name} SELECT * FROM {temp_name};"

        with self._client(True) as client:
            client.execute(sql_tmp_table)
            client.insert_dataframe(sql_insert, df, settings={"use_numpy": True})
            client.execute(delete_sql)
            client.execute(insert_sql)
            client.execute(f"drop table {temp_name};")

    def counter(self):
        return DatabaseCounter(self)

    def query(self, sql: str, _writable=False, parse_dates=..., dtype=None) -> pd.DataFrame:
        if dtype is None:
            dtype = {}
        if parse_dates is not ...:
            dtype.update({col: dttms.dtype_nanos for col in parse_dates})
        with self._client(_writable) as client:
            df = client.query_dataframe(sql)
        if dtype and not df.empty:
            df = df.astype(dtype)
        return df

    def delete(self, sql: str):
        self.query(sql, _writable=True)

    def update(self, sql: str):
        self.query(sql, _writable=True)

    def select(self, cls: Type[T], sql, _writable=False, as_frame=False) -> list[T] | pd.DataFrame:
        with self._client(_writable) as client:
            cols = [field.name for field in fields(cls)]
            data, query_cols = client.execute(sql, with_column_types=True, columnar=True)
            dict_data = {
                col_name: _dtypes.get(col_type, lambda x: x)(col_data)
                for col_data, (col_name, col_type) in zip(data, query_cols)
            }
            iters = [dict_data[x] for x in cols if x in dict_data]
            combined_iter = zip(*iters)
            result = [cls(*x) for x in combined_iter]
            return pd.DataFrame(result) if as_frame else result

    def count(self, sql, _writable=False):
        return self.query(sql, _writable=_writable).values[0][0]

    def clickhouse_url(self, writable: bool = False):
        with self._client(writable, None) as client:
            return ":".join(str(x) for x in client.connection.hosts[0])

    def __get_disk_path(self, disk: str = ...) -> tuple[Path, str]:
        if disk is ...:
            disk = settings.hostname
        with self._client(False, None) as client:
            data = client.execute(f"select disks.path, disks.name from system.disks where disks.name = '{disk}'")
            if len(data) == 0:
                raise Exception(f"disk {disk} not found in config.")
            path, name = data[0]
        return Path(path), name

    @staticmethod
    def latest_path_as_of(root: Path, as_of_dttm: DttmLike = ..., raise_exc=True) -> Path | None:
        if as_of_dttm is ...:
            as_of_dttm = dttms.now()
        else:
            as_of_dttm = dttms.as_dttm(as_of_dttm)

        pattern = re.compile(r"(\d{8}_\d{4})$")  # matching date format
        dttms_paths = [
            match.group(1)  # Extract the date-time part
            for f in root.iterdir()
            if (match := pattern.search(f.name))  # Check if the filename matches the pattern
        ]
        dttms_ = dttms.as_dttms(dttms_paths).astype(dttms.dtype_minutes)
        deltas = (as_of_dttm - dttms_).astype(int)
        candidates = deltas[deltas > 0]
        if len(candidates) == 0:
            if raise_exc:
                raise Exception(f"No backup before {as_of_dttm} earliest backup is {dttms_paths[np.argmin(deltas)]}")
            else:
                return None
        index_min = np.argmin(candidates)
        return root / f"{dttms_paths[index_min]}"

    def backup(self, path: str = ..., incremental: bool = ...) -> Path | None:
        if path is ...:
            path = format_dttm(dttms.now(), "%Y%m%d_%H%M")

        root_path, backup_disk_name = self.__get_disk_path()
        latest_pth = Database.latest_path_as_of(root_path, raise_exc=False)
        backup_pth = Path(root_path).joinpath(path)

        if incremental is ...:
            incremental = latest_pth is not None

        if not root_path.exists():
            root_path.mkdir()

        qry = f"BACKUP DATABASE default TO Disk('{backup_disk_name}', '{path}')"
        if incremental:
            qry += f" SETTINGS base_backup = Disk('{backup_disk_name}', '{latest_pth.name}')"

        with self._client(False) as client:
            client.execute(qry)
            _logger.info(f"Taken backup of database {self.clickhouse_url()} to {root_path / path}")

        if not backup_pth.exists():
            raise FileNotFoundError(f"Backup file {backup_pth} does not exist.")

        return backup_pth

    def backup_paths(self, host, as_of_dttm: DttmLike = ...) -> tuple[Path, str, str]:
        restore_root_path, disk_name = self.__get_disk_path(host)

        if as_of_dttm == "latest":
            pth = self.latest_path_as_of(restore_root_path).name
        else:
            pth = self.latest_path_as_of(restore_root_path, as_of_dttm).name

        backup_pth = restore_root_path / pth
        return backup_pth, disk_name, pth

    def restore(self, as_of_dttm: DttmLike | str = "latest", from_host: str = ...):
        backup_pth, disk_name, pth = self.backup_paths(from_host, as_of_dttm)

        with self._client(True, None) as client:
            _logger.info(f"Dropping database default from {self.clickhouse_url()}")
            client.execute("DROP DATABASE IF EXISTS default;")
            _logger.info(f"Restoring database {self.clickhouse_url()} from {backup_pth}")
            qry_id, status = client.execute(f"RESTORE DATABASE default FROM Disk('{disk_name}', '{pth}') ASYNC")[0]
            timeout_dttm = dttms.as_dttm("now+5m")
            status = _RestoreStatus[status]
            progress = ProgressBar("Database restore")
            while status.is_in_progress:
                sleep(0.5)
                status, processed, total, error = client.execute(
                    f"SELECT status, bytes_read, total_size, error FROM system.backups WHERE id='{qry_id}'"
                )[0]
                if total > 0:
                    progress.print_update(processed, total)
                status = _RestoreStatus[status]
                if dttms.now() > timeout_dttm:
                    raise TimeoutError(f"Restore ({qry_id}) timed out after 5 mins.")

        if status.is_error:
            raise Exception(f"Restore ({qry_id}) failed with err: {error}.")

        _logger.info("Restore complete.")

    def list_backups(self, disk: str = ...):
        backup_root_path, disk_name = self.__get_disk_path(disk)
        sizes = []
        total = 0
        for child in backup_root_path.iterdir():
            if child.is_dir():
                result = subprocess.run(["du", "-sh", str(child)], capture_output=True, text=True, check=True)
                size = parse_readable_mem(result.stdout.strip().split()[0])
                total += size
                sizes.append({"path": str(child), "size": size})
        sizes.append({"path": "TOTAL", "size": total})
        df = pd.DataFrame(sizes)
        df["size"] = (df["size"] / GB).apply(lambda x: f"{x:.2f} GB")
        return df

    def get_table_hash(self, excluded_tables: list[str] = ..., included_tables: list[str] = None) -> dict[str, int]:
        if excluded_tables is ...:
            excluded_tables = []

        where_clause = ""
        if excluded_tables is not None:
            comma_sep_tables = ", ".join(f"'{table}'" for table in excluded_tables)
            where_clause += f" and table not in({comma_sep_tables})"
        if included_tables is not None:
            comma_sep_tables = ", ".join(f"'{table}'" for table in included_tables)
            where_clause += f" and table in({comma_sep_tables})"

        with self._client(False) as client:
            cols = client.execute(
                "SELECT name, table "
                "from system.columns "
                f"where database='default' {where_clause} "
                "order by table, name"
            )
            table_cols = defaultdict(list)
            for col, table in cols:
                table_cols[table].append(col)

            table_hashes = {}
            for table_name, cols in table_cols.items():
                concat_columns = ", ".join([f"toString({col})" for col in cols])
                comma_sep_cols = ", ".join(cols)
                table_hashes[table_name] = client.execute(
                    f"""SELECT cityHash64(arrayStringConcat(groupArray(concat({concat_columns})))) AS table_hash
            FROM (SELECT * FROM {table_name} ORDER BY {comma_sep_cols}) AS sorted_data;
            """
                )[0][0]

        return table_hashes


@dataclasses.dataclass
class DatabaseCounter:
    database: Database
    inserted: int = 0
    updated: int = 0
    deleted: int = 0

    def insert(self, obj):
        self.database.insert(obj)
        self.inserted += 1

    def update(self, obj, keys):
        self.database.update_obj(obj, keys)
        self.updated += 1

    def delete(self, obj, keys):
        self.database.delete_obj(obj, keys)
        self.deleted += 1

    def inserts(self, objs):
        self.database.inserts(objs)
        self.inserted += len(objs)


class _RestoreStatus(IntEnum):
    RESTORING = 3
    RESTORED = 4
    RESTORE_FAILED = 5
    BACKUP_CANCELLED = 6
    RESTORE_CANCELLED = 7

    @property
    def is_in_progress(self):
        return self == _RestoreStatus.RESTORING

    @property
    def is_error(self):
        return self > 4

    @property
    def is_success(self):
        return self == 4
