from dataclasses import dataclass

import settings
import logging
import sys

from core import Stamped, Keyed, dttms, Key, services
from core.process import run_command_in_shell
from core.strs import tabulate_objects, tabulate_object, parse_readable_mem

_logger = logging.getLogger(__name__)


@dataclass
class FileSystemUsage(Stamped, Keyed):
    hostname: str
    file_system: str
    size: int
    used: int
    available: int
    mounted_on: str

    def key(self) -> Key:
        return Key(self.hostname, self.file_system, self.mounted_on)


def disk_usage() -> list[FileSystemUsage]:
    output = run_command_in_shell("df")
    now = dttms.now()

    def parse_fs(s):
        fs, sz, uz, av, up, m = s.split()
        return FileSystemUsage(now, settings.hostname, fs, int(sz), int(uz), int(av), m)

    return [parse_fs(line) for line in output.split("\n")[1:] if line]


@dataclass
class ProcessResources(Stamped, Keyed):
    hostname: str
    pid: int
    user: str
    priority: int
    nice: int
    virt: int
    res: int
    shr: int
    status: str
    cpu_perc: float
    mem_perc: float
    time: float  # seconds
    command: str

    def key(self) -> Key:
        return Key(self.hostname, self.pid)


@dataclass
class CpuUsage(Stamped, Keyed):
    # https://www.redhat.com/sysadmin/interpret-top-output
    hostname: str
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    tasks: int
    tasks_running: int
    cpu_user: float
    cpu_system: float
    cpu_nice: float
    cpu_idle: float
    cpu_wait: float
    cpu_hi: float  # hardware interrupt
    cpu_si: float  # software interrupt
    cpu_st: float  # virtual wait for physical

    def key(self) -> Key:
        return Key(self.hostname)


def _parse_top_line(line):
    title, items = line.split(":")
    items = {k: v for v, k in [item.strip().split(" ") for item in items.split(",")]}
    return title, items


def _truncate_command(command):
    if len(command) > 50:
        command = command.split(maxsplit=1)[0]
    return command


def _parse_top_time(time):
    mins, secs = time.split(":")
    mins = 60.0 * float(mins)

    if "." in secs:
        secs, hundreds = secs.split(".")
        secs = float(secs) + int(hundreds) / 100
    else:
        secs = float(secs)
    return mins + secs


def _priority(p):
    return 100 if p == "rt" else int(p)


def top():
    output = run_command_in_shell("COLUMNS=512 top -bn1").split("\n")
    dttm = dttms.now()
    *_, la1, la5, la15 = output[0].rsplit(":", 1)[-1].split(",")  # line 0, load average
    _, tasks = _parse_top_line(output[1])  # line 1, tasks
    _, cpu = _parse_top_line(output[2])  # line 2, cpu
    summary = CpuUsage(
        dttm,
        settings.hostname,
        float(la1),
        float(la5),
        float(la15),
        int(tasks["total"]),
        int(tasks["running"]),
        float(cpu["us"]),
        float(cpu["sy"]),
        float(cpu["ni"]),
        float(cpu["id"]),
        float(cpu["wa"]),
        float(cpu["hi"]),
        float(cpu["si"]),
        float(cpu["st"]),
    )
    # individual procs
    h = {c: i for i, c in enumerate(output[6].split())}

    def mem(r, k):
        return parse_readable_mem(r[h[k]], target="k")

    procs = [
        ProcessResources(
            dttm,
            settings.hostname,
            int(r[h["PID"]]),
            r[h["USER"]],
            _priority(r[h["PR"]]),
            _priority(r[h["NI"]]),
            mem(r, "VIRT"),
            mem(r, "RES"),
            mem(r, "SHR"),
            r[h["S"]],
            float(r[h["%CPU"]]),
            float(r[h["%MEM"]]),
            _parse_top_time(r[h["TIME+"]]),
            _truncate_command(r[h["COMMAND"]]),
        )
        for r in [p.split(maxsplit=len(h)) for p in output[7:] if p]
    ]
    return summary, procs


@dataclass
class CpuUtilisation(Stamped, Keyed):
    hostname: str
    cpu: int
    usr: float
    nice: float
    sys: float
    iowait: float
    irq: float
    soft: float
    steal: float
    guest: float
    gnice: float
    idle: float

    def key(self) -> Key:
        return Key(self.hostname, self.cpu)


def cpu_utilisation(threshold: float = 5.0):
    output = run_command_in_shell("mpstat -P ALL").split("\n")[2:]
    now = dttms.now()
    h = {c: i for i, c in enumerate(output[0].rsplit(maxsplit=11)[2:])}
    result = []
    for ln in output[1:]:
        if not ln:
            continue
        _, cpu, *ln = ln.rsplit(maxsplit=11)
        cpu = -1 if cpu == "all" else int(cpu)  # -1 for 'all'
        ln = [float(f) for f in ln]

        idle = ln[h["%idle"]]
        total = 100 - idle
        if cpu < 0 or total >= threshold:
            result.append(
                CpuUtilisation(
                    now,
                    settings.hostname,
                    cpu,
                    ln[h["%usr"]],
                    ln[h["%nice"]],
                    ln[h["%sys"]],
                    ln[h["%iowait"]],
                    ln[h["%irq"]],
                    ln[h["%soft"]],
                    ln[h["%steal"]],
                    ln[h["%guest"]],
                    ln[h["%gnice"]],
                    idle,
                )
            )
    return result


@dataclass
class MemoryUtilisation(Stamped, Keyed):
    hostname: str
    total: int
    used: int
    free: int
    shared: int
    buff_cache: int
    available: int
    swap_total: int
    swap_used: int
    swap_free: int

    def key(self) -> Key:
        return Key(self.hostname)


def memory_utilisation():
    output = run_command_in_shell("free").split("\n")
    now = dttms.now()
    h = {k: i for i, k in enumerate(output[0].split())}
    mem = [int(x) for x in output[1].split(":")[-1].split()]
    swap = [int(x) for x in output[2].split(":")[-1].split()]
    return MemoryUtilisation(
        now,
        settings.hostname,
        mem[h["total"]],
        mem[h["used"]],
        mem[h["free"]],
        mem[h["shared"]],
        mem[h["buff/cache"]],
        mem[h["available"]],
        swap[h["total"]],
        swap[h["used"]],
        swap[h["free"]],
    )


if __name__ == "__main__":

    def _main():
        db = services.audit_db()
        shutdown = services.shutdown_handler()
        i = 0

        while not shutdown.killed:
            dbc = db.counter()

            cpu_usage, procs = top()
            dbc.insert(cpu_usage)
            dbc.inserts(procs)

            dbc.inserts(cpu_utilisation())

            dbc.insert(memory_utilisation())

            if i % 5 == 0:
                dbc.inserts(disk_usage())  # disk usage is slow moving, so can sample less regularly

            logging.info(f"inserted {dbc.inserted} metrics")
            i += 1
            shutdown.sleep(60)

    def _print():
        print("\n*** disk usage ***")
        print(tabulate_objects(disk_usage()))

        cpu_usage, procs = top()
        print("\n*** cpu usage ***")
        print(tabulate_object(cpu_usage))

        print("\n*** process resources ***")
        print(tabulate_objects(procs))

        print("\n*** cpu utilisation ***")
        print(tabulate_objects(cpu_utilisation()))

        print("\n*** memory utilisation ***")
        print(tabulate_object(memory_utilisation()))

    if len(sys.argv) > 1:
        if sys.argv[1] == "--print":
            _print()
        else:
            raise Exception(f"Unexpected args: {sys.argv[1:]}")
    else:
        _main()
