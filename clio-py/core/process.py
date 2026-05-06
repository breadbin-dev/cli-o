import signal
import subprocess
import time
import threading
import logging
from dataclasses import dataclass, fields, field
from core import dttms, ToDict

from core.clocks import Session
from core.dttms import format_friendly_time

_logger = logging.getLogger(__name__)


def run_command_in_shell(command: str, remote_host: str = None) -> str:
    if remote_host:
        command = f"ssh {remote_host} '{command}'"

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = proc.communicate()
    if proc.returncode != 0:
        if error:
            raise Exception(error.decode())
        else:
            raise Exception(f"return code [{proc.returncode}]")
    return output.decode()


class ShutdownHandler:
    def __init__(self):
        self._killed = False
        if isinstance(threading.current_thread(), threading._MainThread):
            signal.signal(signal.SIGINT, self.exit_gracefully)
            signal.signal(signal.SIGTERM, self.exit_gracefully)
        else:
            _logger.warning("ShutdownHandler not threading main thread")

    @property
    def killed(self):
        return self._killed

    @killed.setter
    def killed(self, value):
        self._killed = value

    def exit_gracefully(self, signum, frame):
        _logger.warning(f"Shutting down [{signum}]...")
        self.killed = True
        exit(0)

    def await_shutdown(self):
        while not self.killed:
            time.sleep(1)

    def sleep(self, secs, inc=1):
        """sleep for period of time, but return early if shutdown"""
        start_time = time.time()
        while time.time() < start_time + secs:
            if self.killed:
                return
            time.sleep(inc)

    def await_session(self, session: Session):
        while dttms.now() not in session:
            next_open = session.open.next([dttms.now()] * 2)[0]
            sleep_time = next_open - dttms.now()
            _logger.info(f"Waiting {format_friendly_time(sleep_time)} until {next_open} for {session}.")
            self.sleep(sleep_time.astype(int) / 1e9)
            _logger.info("Await session complete.")


@dataclass(frozen=True)
class ProcessStatus(ToDict):
    """Status of process. All memory in KBs"""

    # More fields available https://www.kernel.org/doc/html/v6.2/filesystems/proc.html?
    Pid: int
    VmPeak: int
    VmSize: int
    VmHWM: int
    VmRSS: int
    RssAnon: int
    RssFile: int
    RssShmem: int


@dataclass(frozen=True)
class PeakMemory(ToDict):
    """Peak memory in KBs."""

    Vm: int
    Rss: int


def process_status(pid: int = ...) -> ProcessStatus:
    """Get the status of a process from `/proc/<pid>/status`."""
    # Docs https://www.kernel.org/doc/html/v6.2/filesystems/proc.html?
    if pid is ...:
        pid = "self"

    field_names = tuple(x.name for x in fields(ProcessStatus))
    kwargs = {}
    with open(f"/proc/{pid}/status", "r") as f:
        for line in f:
            if line.startswith(field_names):
                parts = line.split()
                kwargs[parts[0].rstrip(":")] = int(parts[1])
    return ProcessStatus(**kwargs)


@dataclass
class ProcessStatusContext(ToDict):
    """Context manager to capture process status before and after a block."""

    pid: int = field(default=..., repr=False)
    before: ProcessStatus = None
    after: ProcessStatus = None

    def __enter__(self):
        self.before = process_status(self.pid)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.after = process_status(self.pid)

    def peak_memory_diff(self) -> PeakMemory:
        return PeakMemory(self.after.VmPeak - self.before.VmPeak, self.after.VmHWM - self.before.VmHWM)
