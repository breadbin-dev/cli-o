import fcntl
import io
import os
import re
import sys
import tempfile
import logging
import shutil
import time
import errno
from functools import wraps
from os import SEEK_END, SEEK_CUR
from pathlib import Path
from typing import Literal, Callable
from dataclasses import dataclass

import pandas as pd
import numpy as np

import settings
from core import Key, dttms
from core.process import run_command_in_shell

_logger = logging.getLogger(__name__)


def relative_path_to_target(target, link_name):
    if not (target.startswith("/") and link_name.startswith("/")):
        return target
    if (pf := os.path.commonprefix([target, link_name])) == "/":
        return target
    if not pf.endswith("/"):
        pf = pf[: pf.rindex("/") + 1]
    return ("../" * (len(link_name[len(pf) :].split("/")) - 1)) + target[len(pf) :]


def local_real_path(path, n=1, throws=True):
    """we only care about our local real-path, not the global realpath"""
    root = path.rsplit("/", maxsplit=n)[0]
    real_path = os.path.realpath(path)
    real_suffix = "/".join(real_path.rsplit("/", maxsplit=n)[-n:])
    local_path = f"{root}/{real_suffix}"
    if not os.path.exists(local_path):
        assert not throws, f"{path} should resolve to real location"
        return None, None
    else:
        return local_path, real_suffix


def symlink_force(target, link_name, relative=True, overwrite=False):
    """
    Create a symbolic link named link_name pointing to target.
    If link_name exists then FileExistsError is raised, unless overwrite=True.
    When trying to overwrite a directory, IsADirectoryError is raised.
    """
    if os.name == "nt":
        return create_windows_link(target, link_name, overwrite)

    if relative:
        target = relative_path_to_target(target, link_name)

    if not overwrite:
        os.symlink(target, link_name)
        return

    # os.replace() may fail if files are on different filesystems
    link_dir = os.path.dirname(link_name)

    # Create link to target with temporary filename
    while True:
        temp_link_name = tempfile.mktemp(dir=link_dir)

        # os.* functions mimic as closely as possible system functions
        # The POSIX symlink() returns EEXIST if link_name already exists
        # https://pubs.opengroup.org/onlinepubs/9699919799/functions/symlink.html
        try:
            os.symlink(target, temp_link_name)
            break
        except FileExistsError:
            pass

    # Replace link_name with temp_link_name
    try:
        # Pre-empt os.replace on a directory with a nicer message
        if (os.path.isdir(link_name) or os.path.isfile(link_name)) and not os.path.islink(link_name):
            raise IsADirectoryError(f"Cannot symlink over existing directory: '{link_name}'")
        os.replace(temp_link_name, link_name)
    except Exception:
        if os.path.islink(temp_link_name):
            os.remove(temp_link_name)
        raise Exception


def realpath(fpath):
    if os.name == "nt":
        return windows_real_path(fpath)
    else:
        return os.path.realpath(fpath)


def create_windows_link(target, link_name, overwrite=False):
    from win32com.client import Dispatch  # noqa

    target_folder, target_filename = os.path.split(target)
    if target_folder == "":
        target_folder = os.path.split(link_name)[0]

    link_path = os.path.splitext(link_name)[0] + ".lnk"

    if os.path.exists(link_path) and not overwrite:
        raise FileExistsError(link_path)

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(link_path)
    shortcut.Targetpath = os.path.join(target_folder, target_filename)
    shortcut.WorkingDirectory = os.path.dirname(link_path)
    shortcut.save()


def read_windows_link_target(fpath):
    from win32com.client import Dispatch  # noqa

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(fpath)
    target = shortcut.Targetpath
    return target


def is_windows_link(fpath):
    return os.path.splitext(fpath)[-1].lower() == ".lnk"


def windows_real_path(fpath):
    if os.path.splitext(fpath)[-1] == "":  # we are on windows and there is no extension, assume it's a symlink
        fpath += ".lnk"

    if is_windows_link(fpath):
        return read_windows_link_target(fpath)

    return fpath


class LockFile:
    """used to lock a file or directory across multiple processes"""

    def __init__(self, lock_file, handle=None):
        self.lock_file = lock_file
        self._handle = handle
        self._lock_fd = None

    def read(self):
        return _LockFileRead(self.lock_file, handle=self._handle)

    def write(self):
        return _LockFileWrite(self.lock_file, handle=self._handle)


class _LockFileWrite(LockFile):
    def __enter__(self):
        self._lock_fd = open(self.lock_file, "w")
        fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
        return self.lock_file if self._handle is None else self._handle

    def __exit__(self, exc, value, tb):
        fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
        self._lock_fd.close()


class _LockFileRead(LockFile):
    def __enter__(self):
        self._lock_fd = open(self.lock_file, "r")
        fcntl.flock(self._lock_fd, fcntl.LOCK_SH)
        return self.lock_file if self._handle is None else self._handle

    def __exit__(self, exc, value, tb):
        fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
        self._lock_fd.close()


class FileCacheItem:
    def __init__(self, locations, current_key):
        self.locations = locations
        self.current_key = current_key
        self.lock = None

    def __enter__(self):
        folder = self.locations[0].rsplit("/", maxsplit=1)[0]
        os.makedirs(folder, exist_ok=True)
        self.lock = LockFile(f"{self.locations[0]}.lock").write()
        self.lock.__enter__()
        return self

    def __exit__(self, exc, value, tb):
        self.lock.__exit__(exc, value, tb)

    def read(self) -> pd.DataFrame | pd.Series | None:
        for location in self.locations:
            if os.path.isfile(location):
                return pd.read_pickle(location)
        return None

    def read_current(self) -> pd.DataFrame | None:
        for location in self.locations:
            location = self._current_location(location)
            if os.path.isfile(location):
                return pd.read_pickle(location)
        return None

    def _current_location(self, location):
        return f"{location.rsplit('/', 1)[0]}/{self.current_key}"

    def write(self, item: pd.DataFrame | pd.Series):
        location = self.locations[0]
        os.makedirs(location.rsplit("/", 1)[0], exist_ok=True)
        item.to_pickle(location)

        if self.current_key:
            symlink_force(location, self._current_location(location), overwrite=True)


class FileCache:
    def __init__(self, location=..., alt_locations=...):
        if location is ...:
            location = f"{settings.data_path}/.cache"
        if alt_locations is ...:
            alt_locations = []
        self.locations = [location] + alt_locations

    def loc(self, dataset, *args, current_key=None) -> FileCacheItem:
        if current_key:
            if current_key is ...:
                current_key = Key(*args[:-1])
            else:
                current_key = Key(*current_key)
        locations = [f"{loc}/{dataset}/{Key(*args)}.pickle" for loc in self.locations]
        return FileCacheItem(locations, current_key)


def _retry_if_not_empty(
    func: Callable[[str], None],
    path: str | os.PathLike,
    exc: tuple[type[Exception], Exception, None],
    *,
    attempts: int = 5,
    sleep_base: float = 0.1,
) -> None:
    err = exc[1]  # the OSError instance
    if isinstance(err, OSError) and err.errno != errno.ENOTEMPTY:
        raise exc

    for i in range(attempts):
        time.sleep(sleep_base * (i + 1))
        try:
            func(path)
            return
        except OSError as exc:
            if exc.errno != errno.ENOTEMPTY or i == attempts - 1:
                raise exc


def robust_rmtree(dir_path: str | Path, attempts: int = 5, sleep_base: float = 0.1) -> None:
    """
    Remove *dir_path* recursively, tolerant against NAS latency
    """
    shutil.rmtree(
        dir_path,
        onerror=lambda f, p, exc: _retry_if_not_empty(f, p, exc, attempts=attempts, sleep_base=sleep_base),
    )


def copy_dir_contents(
    src: Path, dest: Path, preserve_metadata=True, do_log=False, exists: Literal["raise", "warn", "ok"] = "ok"
):
    """
    Recursively copies the contents of the source directory to the destination directory
    optionally preserving metadata (mtime, inode, etc.)
    """
    if not src.is_dir():
        raise ValueError(f"The source path '{src}' is not a directory.")
    if not dest.is_dir():
        raise ValueError(f"The destination path '{src}' is not a directory.")

    copy_function = shutil.copy2 if preserve_metadata else shutil.copy

    for item in src.rglob("*"):
        relative_path = item.relative_to(src)
        dest_path = dest / relative_path

        if item.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if exists != "ok" and dest_path.exists():
                match exists:
                    case "raise":
                        raise FileExistsError(f"The destination path '{dest_path}' already exists.")
                    case "warn":
                        _logger.warning(f"The destination path '{dest_path}' already exists.")
            copy_function(item, dest_path)
            if do_log:
                _logger.info(f"Copied {relative_path} to {dest_path}")


def move_dir_contents(
    src: Path, dest: Path, do_log: bool = False, exists: Literal["raise", "warn", "ok"] = "ok", n=0
) -> int:
    """
    Recursively moves the contents of the source directory to the destination directory.
    """
    if not src.is_dir():
        raise ValueError(f"The source path '{src}' is not a directory.")
    if not dest.is_dir():
        raise ValueError(f"The destination path '{dest}' is not a directory.")

    for item in src.iterdir():
        dest_path = dest / item.name

        if item.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
            move_dir_contents(item, dest_path, do_log=do_log, n=n)
            if any(item.iter()):
                raise FileExistsError(f"The path {item} still has contents after move.")
            item.rmdir()
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if exists != "ok" and dest_path.exists():
                match exists:
                    case "raise":
                        raise FileExistsError(f"The destination path '{dest_path}' already exists.")
                    case "warn":
                        _logger.warning(f"The destination path '{dest_path}' already exists.")
            shutil.move(str(item), str(dest_path))
            n += 1
            if do_log:
                _logger.info(f"Moved {item} to {dest_path}")

    return n


def read_n_to_last_line(path: Path, n: int = 1) -> str:
    """
    Reads the nth-to-last line from a file.

    This function reads a specific line from the end of a file without
    loading the entire file into memory. It traverses the file backwards to locate
    the desired line.

    :param Path path: The path to the file to read.
    :param int n: The position of the line from the end of the file (1-based index).
                 Defaults to 1, which retrieves the last line.
    :returns: The nth-to-last line of the file.
    """
    num_new_lines = 0
    with path.open("rb") as f:
        f.seek(0, SEEK_END)
        while True:
            if f.tell() == 0:
                if num_new_lines < n - 1:
                    raise ValueError(f"{n=} is larger than the number of lines in the file.")
                break

            f.seek(-1, SEEK_CUR)
            if f.read(1) == b"\n":
                num_new_lines += 1
            if num_new_lines >= n:
                break
            else:
                f.seek(-1, SEEK_CUR)
        return f.readline().decode().replace("\n", "")  # don't read last \n


def ask_ynx(prompt: str, print_fcn: Callable[[str], None] = print, timeout: int = None) -> bool:
    """
    Prompt the user for input until they enter 'y', 'n', or 'x'.
    """
    while True:
        resp = input(f"{prompt} [ynx]: ").strip().lower()
        if resp in ("y", "n", "x"):
            break

    if resp == "x":
        print_fcn("Aborted")
        sys.exit(1)

    return resp == "y"


@dataclass(frozen=True)
class PathInfo:
    """File metadata information."""

    path: Path
    inode: int
    device: int
    file_size: int
    last_modified: np.datetime64
    created_dttm: np.datetime64

    @staticmethod
    def extract_file_info(path: Path | str) -> "PathInfo":
        if isinstance(path, str):
            path = Path(path)
        stat = path.stat()
        return PathInfo(
            path,
            stat.st_ino,
            stat.st_dev,
            stat.st_size,
            dttms.from_unix(stat.st_mtime),
            dttms.from_unix(stat.st_ctime),
        )


def disk_usage(path: Path | str, follow_links: bool = False) -> int:
    """Disk Usage in bytes"""
    # https://man7.org/linux/man-pages/man1/du.1.html
    links = " -L " if follow_links else ""
    str_bytes = run_command_in_shell(f'du -s {links} -B1 "{path}"')
    return int(re.split(r"\s+", str_bytes, maxsplit=1)[0])


class CaptureLogs:
    def __init__(self, level=logging.INFO, return_result=True):
        self.level = level
        self.return_result = return_result

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log_capture = io.StringIO()
            stream_handler = logging.StreamHandler(log_capture)
            formatter = logging.Formatter("%(asctime)s [%(threadName)-14.14s] [%(levelname)-5.5s]  %(message)s")
            stream_handler.setFormatter(formatter)

            logger = logging.getLogger()
            old_level = logger.level
            logger.setLevel(self.level)
            logger.addHandler(stream_handler)

            try:
                result = func(*args, **kwargs)
            finally:
                logger.removeHandler(stream_handler)
                logger.setLevel(old_level)

            logs = log_capture.getvalue()
            return (result, logs) if self.return_result else logs

        return wrapper
