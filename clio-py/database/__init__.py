import dataclasses
import enum

import numpy as np

from core import DttmLike
from core.strs import camel_to_snake

create_table_template = """
-- *** {table_name} ***

-- drop table {table_name};

create table if not exists {table_name}
(
{table_columns}
)
    engine = {engine}({engine_args})
    partition by {dttm_partition}({dttm_column})
    order by ({table_keys}){ttl}
    comment 'auto generated table';

select * from {table_name} limit 10;

-- migrators
{insert_columns}

-- full table migration (for key changes)
-- rename table {table_name} to {table_name}_tmp;

-- insert into {table_name}
--    ({column_names})
--    select {column_names}
--    from {table_name}_tmp;

-- drop table {table_name}_tmp;

"""


def type_for_field(type_, name):
    if type_ == np.datetime64 or type_ == DttmLike:
        if name.endswith("_dt"):
            return "Date"
        else:
            return "DateTime64(9)"
    if type_ == str:
        return "String"
    if type_ == float:
        return "Float64"
    if type_ == int:
        return "Int64"
    if type_ == bool:
        return "Bool"
    if issubclass(type_, enum.Enum):
        if issubclass(type_, int):
            return "Int64"
        return "String"

    raise Exception(f"Unsupported type {type_.__name__}")


def column_for_field(field, is_nullable):
    tff = type_for_field(field.type, field.name)
    if is_nullable:
        tff = f"Nullable({tff})"
    return f"{field.name} {tff}"


def schema_column(cf):
    return f"    {cf}"


def insert_column(table, cf, prev):
    return f"-- alter table {table} add column {cf} after {prev};"


def schema_for_object(cls, dttm_column="dttm", engine="MergeTree", engine_args="", ttl="", dttm_partition="toYYYYMM"):
    table_name = camel_to_snake(cls.__name__)
    table_columns = []
    table_keys = []
    insert_columns = []
    column_names = []

    fields = {x.name: x for x in dataclasses.fields(cls)}
    nullable_fields = set(cls.__nullable_fields__ if hasattr(cls, "__nullable_fields__") else [])

    table_columns.append(schema_column(column_for_field(dttm := fields[dttm_column], False)))
    table_keys.append(dttm_column)
    table_keys.extend(cls.get_key_fields())
    column_names.append(dttm_column)

    assert dttm.name == dttm_column and (dttm.type == np.datetime64 or dttm.type == DttmLike)

    prev = fields[dttm_column].name
    for field_name, field in fields.items():
        if field_name != dttm_column:
            cf = column_for_field(field, field_name in nullable_fields)
            table_columns.append(schema_column(cf))
            insert_columns.append(insert_column(table_name, cf, prev))
            column_names.append(field_name)
            prev = field_name

    return create_table_template.format(
        table_name=table_name,
        table_columns=",\n".join(table_columns),
        table_keys=", ".join(table_keys),
        insert_columns="\n".join(insert_columns),
        column_names=", ".join(column_names),
        dttm_column=dttm_column,
        engine=engine,
        engine_args=engine_args,
        ttl=ttl,
        dttm_partition=dttm_partition,
    )
