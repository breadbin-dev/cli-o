
-- *** ticket ***

-- drop table ticket;

create table if not exists ticket
(
    dttm DateTime64(9),
    id String,
    group String,
    message String,
    open Bool,
    acknowledged Bool,
    owner String,
    created_dttm DateTime64(9)
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, id)
    comment 'auto generated table';

select * from ticket limit 10;

-- migrators
-- alter table ticket add column id String after dttm;
-- alter table ticket add column group String after id;
-- alter table ticket add column message String after group;
-- alter table ticket add column open Bool after message;
-- alter table ticket add column acknowledged Bool after open;
-- alter table ticket add column owner String after acknowledged;
-- alter table ticket add column created_dttm DateTime64(9) after owner;

-- full table migration (for key changes)
-- rename table ticket to ticket_tmp;

-- insert into ticket
--    (dttm, id, group, message, open, acknowledged, owner, created_dttm)
--    select dttm, id, group, message, open, acknowledged, owner, created_dttm
--    from ticket_tmp;

-- drop table ticket_tmp;


-- *** schedule_preference ***

-- drop table schedule_preference;

create table if not exists schedule_preference
(
    asserted_from DateTime64(9),
    username String,
    prefs String,
    asserted_to Nullable(DateTime64(9))
)
    engine = MergeTree()
    partition by toYYYYMM(asserted_from)
    order by (asserted_from, username)
    comment 'auto generated table';

select * from schedule_preference limit 10;

-- migrators
-- alter table schedule_preference add column username String after asserted_from;
-- alter table schedule_preference add column prefs String after username;
-- alter table schedule_preference add column asserted_to Nullable(DateTime64(9)) after prefs;

-- full table migration (for key changes)
-- rename table schedule_preference to schedule_preference_tmp;

-- insert into schedule_preference
--    (asserted_from, username, prefs, asserted_to)
--    select asserted_from, username, prefs, asserted_to
--    from schedule_preference_tmp;

-- drop table schedule_preference_tmp;

