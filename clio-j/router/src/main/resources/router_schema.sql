-- *** service_status ***

-- drop table if exists service_status;

create table if not exists service_status
(
    dttm      TEXT    not null,
    name      TEXT    not null,
    running   INTEGER not null,
    connected INTEGER not null,
    msg       TEXT
);

-- *** user ***

-- drop table if exists "user";

create table if not exists "user"
(
    username TEXT not null,
    email    TEXT not null,
    passhash TEXT not null
);

-- *** user_token ***

-- drop table if exists user_token;

create table if not exists user_token
(
    dttm     TEXT not null,
    token    TEXT not null,
    username TEXT not null,
    email    TEXT not null
);