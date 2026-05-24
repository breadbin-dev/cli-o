-- *** service_status ***

-- drop table service_status;

create table if not exists service_status
(
    dttm DateTime64(9),
    name String,
    running Boolean,
    connected Boolean,
    msg Nullable(String)
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, name)
    comment 'auto generated table';

select * from service_status limit 10;

-- migrators
-- alter table service_status add column dttm DateTime64(9);
-- alter table service_status add column name String after dttm;
-- alter table service_status add column running Boolean after name;
-- alter table service_status add column connected Boolean after running;
-- alter table service_status add column msg Nullable(String) after connected;

-- *** task_status ***

-- drop table task_status;

create table if not exists task_status
(
    dttm DateTime64(9),
    name String,
    state String,
    next_dttm Nullable(DateTime64(9)),
    previous_dttm Nullable(DateTime64(9)),
    previous_result Nullable(String),
    msg Nullable(String)
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, name)
    comment 'auto generated table';

select * from task_status limit 10;

-- migrators
-- alter table task_status add column dttm DateTime64(9);
-- alter table task_status add column name String after dttm;
-- alter table task_status add column state String after name;
-- alter table task_status add column next_dttm Nullable(DateTime64(9)) after state;
-- alter table task_status add column previous_dttm Nullable(DateTime64(9)) after next_dttm;
-- alter table task_status add column previous_result Nullable(String) after previous_dttm;
-- alter table task_status add column msg Nullable(String) after previous_result;

