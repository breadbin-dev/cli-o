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

-- *** user_token ***

-- drop table user_token;

create table if not exists user_token
(
    dttm DateTime64(9),
    token String,
    username String,
    email String
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, username)
    comment 'auto generated table';

select * from user_token limit 10;

-- migrators
-- alter table user_token add column dttm DateTime64(9);
-- alter table user_token add column token String after dttm;
-- alter table user_token add column username String after token;
-- alter table user_token add column email String after username;

