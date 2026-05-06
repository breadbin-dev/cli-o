import logging
import subprocess
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from argparse import ArgumentParser, Namespace
import numpy as np
from core import services

_logger = logging.getLogger(__name__)


class Result(str, Enum):
    # From docs: https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html
    SUCCESS = "success"
    FAILED = "failed"
    RESOURCES = "resources"
    EXIT_CODE = "exit-code"
    SIGNAL = "signal"
    CORE_DUMP = "core-dump"
    TIMEOUT = "timeout"
    WATCHDOG = "watchdog"
    START_LIMIT = "start-limit"
    OTHER = "Other"

    @classmethod
    def _missing_(cls, value):
        return cls.OTHER


class State(str, Enum):
    # From docs: https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    MAINTENANCE = "maintenance"
    RELOADING = "reloading"
    REFRESHING = "refreshing"
    RUNNING = "running"
    OTHER = "other"

    @classmethod
    def _missing_(cls, value):
        return cls.OTHER


@dataclass(init=False)
class SystemCtlStatus:
    pattern = re.compile(
        r"^(?P<service_name>[^\s]+)\s+"
        r"MainPID=(?P<p_id>\d+)\s+"
        r"Result=(?P<result>[^\s]+)\s+"
        r"ExecMainStartTimestamp=(?P<start_time>.*?)\s+"
        r"ActiveState=(?P<active_state>[^\s]+)\s+"
        r"SubState=(?P<sub_state>[^\s]+)"
    )

    service_name: str
    p_id: int | None
    result: Result
    start_time: dt.datetime | None
    active_state: State
    sub_state: State

    def __init__(self, _str: str):
        match = SystemCtlStatus.pattern.match(_str)
        self.original_str = _str
        if match:
            self.service_name = match.group("service_name")
            p_id = int(match.group("p_id"))
            self.p_id = p_id if p_id != 0 else None
            self.result = Result(match.group("result"))
            start_time = match.group("start_time")
            self.start_time = dt.datetime.strptime(start_time, "%a %Y-%m-%d %H:%M:%S %Z") if start_time else None
            self.active_state = State(match.group("active_state"))
            self.sub_state = State(match.group("sub_state"))
        else:
            raise ValueError(f"Invalid input: {_str}")


@dataclass(frozen=True)
class ServiceStatus:
    dttm: np.datetime64
    name: str
    running: bool
    connected: bool
    msg: str


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("-b", "--bin_path", required=True, type=Path)
    return parser.parse_args()


def run_script(script_path: Path) -> str:
    """
    Run the specified script and capture its output.
    """
    _logger.info(f"Running script: {script_path}")
    process = subprocess.Popen(
        [str(script_path), "status"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=15)
        _logger.info("Script stdout:\n%s", stdout)
        if stderr:
            _logger.warning("Script stderr:\n%s", stderr)
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        return stdout
    except subprocess.TimeoutExpired as ex:
        process.kill()
        stdout, stderr = process.communicate()
        _logger.error("Script timed out")
        _logger.error("Script stdout:\n%s", stdout)
        _logger.error("Script stderr:\n%s", stderr)
        raise TimeoutError("Script timed out") from ex


def main():
    args = parse_args()
    root_path = args.bin_path
    services_sh_path = root_path / "services.sh"

    if not services_sh_path.exists():
        raise FileNotFoundError(f"services.sh path not found: {services_sh_path}")

    result = run_script(services_sh_path)
    wave_time = np.datetime64(dt.datetime.now(tz=dt.timezone.utc).replace(tzinfo=None))

    _logger.info("Parsing service status output.")
    statuses = [SystemCtlStatus(line) for line in result.splitlines()]
    statuses_db = [
        ServiceStatus(
            dttm=wave_time,
            name=status.service_name,
            running=status.active_state == State.ACTIVE,
            connected=status.sub_state == State.RUNNING,
            msg=status.original_str,
        )
        for status in statuses
    ]

    _logger.info(f"Writing {len(statuses)} service statuses to audit db.")
    db = services.audit_db()
    db.inserts(statuses_db)


if __name__ == "__main__":
    main()
