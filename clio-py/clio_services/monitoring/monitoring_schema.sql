
-- *** file_system_usage ***

-- drop table file_system_usage;

create table if not exists file_system_usage
(
    dttm DateTime64(9),
    hostname String,
    file_system String,
    size Int64,
    used Int64,
    available Int64,
    mounted_on String
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, hostname, file_system, mounted_on)
    comment 'auto generated table';

select * from file_system_usage limit 10;

-- migrators
-- alter table file_system_usage add column hostname String after dttm;
-- alter table file_system_usage add column file_system String after hostname;
-- alter table file_system_usage add column size Int64 after file_system;
-- alter table file_system_usage add column used Int64 after size;
-- alter table file_system_usage add column available Int64 after used;
-- alter table file_system_usage add column mounted_on String after available;

-- full table migration (for key changes)
-- rename table file_system_usage to file_system_usage_tmp;

-- insert into file_system_usage
--    (dttm, hostname, file_system, size, used, available, mounted_on)
--    select dttm, hostname, file_system, size, used, available, mounted_on
--    from file_system_usage_tmp;

-- drop table file_system_usage_tmp;


-- *** process_resources ***

-- drop table process_resources;

create table if not exists process_resources
(
    dttm DateTime64(9),
    hostname String,
    pid Int64,
    user String,
    priority Int64,
    nice Int64,
    virt Int64,
    res Int64,
    shr Int64,
    status String,
    cpu_perc Float64,
    mem_perc Float64,
    time Float64,
    command String
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, hostname, pid)
    comment 'auto generated table';

select * from process_resources limit 10;

-- migrators
-- alter table process_resources add column hostname String after dttm;
-- alter table process_resources add column pid Int64 after hostname;
-- alter table process_resources add column user String after pid;
-- alter table process_resources add column priority Int64 after user;
-- alter table process_resources add column nice Int64 after priority;
-- alter table process_resources add column virt Int64 after nice;
-- alter table process_resources add column res Int64 after virt;
-- alter table process_resources add column shr Int64 after res;
-- alter table process_resources add column status String after shr;
-- alter table process_resources add column cpu_perc Float64 after status;
-- alter table process_resources add column mem_perc Float64 after cpu_perc;
-- alter table process_resources add column time Float64 after mem_perc;
-- alter table process_resources add column command String after time;

-- full table migration (for key changes)
-- rename table process_resources to process_resources_tmp;

-- insert into process_resources
--    (dttm, hostname, pid, user, priority, nice, virt, res, shr, status, cpu_perc, mem_perc, time, command)
--    select dttm, hostname, pid, user, priority, nice, virt, res, shr, status, cpu_perc, mem_perc, time, command
--    from process_resources_tmp;

-- drop table process_resources_tmp;


-- *** cpu_usage ***

-- drop table cpu_usage;

create table if not exists cpu_usage
(
    dttm DateTime64(9),
    hostname String,
    load_avg_1 Float64,
    load_avg_5 Float64,
    load_avg_15 Float64,
    tasks Int64,
    tasks_running Int64,
    cpu_user Float64,
    cpu_system Float64,
    cpu_nice Float64,
    cpu_idle Float64,
    cpu_wait Float64,
    cpu_hi Float64,
    cpu_si Float64,
    cpu_st Float64
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, hostname)
    comment 'auto generated table';

select * from cpu_usage limit 10;

-- migrators
-- alter table cpu_usage add column hostname String after dttm;
-- alter table cpu_usage add column load_avg_1 Float64 after hostname;
-- alter table cpu_usage add column load_avg_5 Float64 after load_avg_1;
-- alter table cpu_usage add column load_avg_15 Float64 after load_avg_5;
-- alter table cpu_usage add column tasks Int64 after load_avg_15;
-- alter table cpu_usage add column tasks_running Int64 after tasks;
-- alter table cpu_usage add column cpu_user Float64 after tasks_running;
-- alter table cpu_usage add column cpu_system Float64 after cpu_user;
-- alter table cpu_usage add column cpu_nice Float64 after cpu_system;
-- alter table cpu_usage add column cpu_idle Float64 after cpu_nice;
-- alter table cpu_usage add column cpu_wait Float64 after cpu_idle;
-- alter table cpu_usage add column cpu_hi Float64 after cpu_wait;
-- alter table cpu_usage add column cpu_si Float64 after cpu_hi;
-- alter table cpu_usage add column cpu_st Float64 after cpu_si;

-- full table migration (for key changes)
-- rename table cpu_usage to cpu_usage_tmp;

-- insert into cpu_usage
--    (dttm, hostname, load_avg_1, load_avg_5, load_avg_15, tasks, tasks_running, cpu_user, cpu_system, cpu_nice, cpu_idle, cpu_wait, cpu_hi, cpu_si, cpu_st)
--    select dttm, hostname, load_avg_1, load_avg_5, load_avg_15, tasks, tasks_running, cpu_user, cpu_system, cpu_nice, cpu_idle, cpu_wait, cpu_hi, cpu_si, cpu_st
--    from cpu_usage_tmp;

-- drop table cpu_usage_tmp;


-- *** cpu_utilisation ***

-- drop table cpu_utilisation;

create table if not exists cpu_utilisation
(
    dttm DateTime64(9),
    hostname String,
    cpu Int64,
    usr Float64,
    nice Float64,
    sys Float64,
    iowait Float64,
    irq Float64,
    soft Float64,
    steal Float64,
    guest Float64,
    gnice Float64,
    idle Float64
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, hostname, cpu)
    comment 'auto generated table';

select * from cpu_utilisation limit 10;

-- migrators
-- alter table cpu_utilisation add column hostname String after dttm;
-- alter table cpu_utilisation add column cpu Int64 after hostname;
-- alter table cpu_utilisation add column usr Float64 after cpu;
-- alter table cpu_utilisation add column nice Float64 after usr;
-- alter table cpu_utilisation add column sys Float64 after nice;
-- alter table cpu_utilisation add column iowait Float64 after sys;
-- alter table cpu_utilisation add column irq Float64 after iowait;
-- alter table cpu_utilisation add column soft Float64 after irq;
-- alter table cpu_utilisation add column steal Float64 after soft;
-- alter table cpu_utilisation add column guest Float64 after steal;
-- alter table cpu_utilisation add column gnice Float64 after guest;
-- alter table cpu_utilisation add column idle Float64 after gnice;

-- full table migration (for key changes)
-- rename table cpu_utilisation to cpu_utilisation_tmp;

-- insert into cpu_utilisation
--    (dttm, hostname, cpu, usr, nice, sys, iowait, irq, soft, steal, guest, gnice, idle)
--    select dttm, hostname, cpu, usr, nice, sys, iowait, irq, soft, steal, guest, gnice, idle
--    from cpu_utilisation_tmp;

-- drop table cpu_utilisation_tmp;


-- *** memory_utilisation ***

-- drop table memory_utilisation;

create table if not exists memory_utilisation
(
    dttm DateTime64(9),
    hostname String,
    total Int64,
    used Int64,
    free Int64,
    shared Int64,
    buff_cache Int64,
    available Int64,
    swap_total Int64,
    swap_used Int64,
    swap_free Int64
)
    engine = MergeTree()
    partition by toYYYYMM(dttm)
    order by (dttm, hostname)
    comment 'auto generated table';

select * from memory_utilisation limit 10;

-- migrators
-- alter table memory_utilisation add column hostname String after dttm;
-- alter table memory_utilisation add column total Int64 after hostname;
-- alter table memory_utilisation add column used Int64 after total;
-- alter table memory_utilisation add column free Int64 after used;
-- alter table memory_utilisation add column shared Int64 after free;
-- alter table memory_utilisation add column buff_cache Int64 after shared;
-- alter table memory_utilisation add column available Int64 after buff_cache;
-- alter table memory_utilisation add column swap_total Int64 after available;
-- alter table memory_utilisation add column swap_used Int64 after swap_total;
-- alter table memory_utilisation add column swap_free Int64 after swap_used;

-- full table migration (for key changes)
-- rename table memory_utilisation to memory_utilisation_tmp;

-- insert into memory_utilisation
--    (dttm, hostname, total, used, free, shared, buff_cache, available, swap_total, swap_used, swap_free)
--    select dttm, hostname, total, used, free, shared, buff_cache, available, swap_total, swap_used, swap_free
--    from memory_utilisation_tmp;

-- drop table memory_utilisation_tmp;

