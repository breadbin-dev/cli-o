from functools import cache
from pathlib import Path

import numpy as np
from core.process import run_command_in_shell
from core import parse_dttm


@cache
def boot_dttm() -> np.datetime64:
    str_uptime = run_command_in_shell("uptime -s")
    return parse_dttm(str_uptime.strip())


@cache
def boot_id() -> str:
    pth = Path("/proc/sys/kernel/random/boot_id")
    return pth.read_text().strip()
