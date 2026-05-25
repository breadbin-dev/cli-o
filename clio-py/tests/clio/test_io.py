import tempfile
import threading
from pathlib import Path
from time import sleep

import pandas as pd
import pytest

from clio import empty_frame, empty_series
from clio.io import relative_path_to_target, LockFile, FileCache, read_n_to_last_line


@pytest.mark.parametrize(
    "target, link_name, expected",
    [
        ("/a/b/c", "/a/b/d", "c"),
        ("/a/b/c", "/d/e", "/a/b/c"),
        ("/a/b", "/a/d/e", "../b"),
        ("/a/b/c", "/a/d/e/f", "../../b/c"),
        ("/a/b/c", "/a/d", "b/c"),
        ("/a/b/c/d", "/a/e", "b/c/d"),
        ("/a/bb", "/a/bc", "bb"),
    ],
)
def test_relative_path_to_target(target, link_name, expected):
    assert relative_path_to_target(target, link_name) == expected


class MockOperation:
    def __init__(self, file):
        self.reads = 0
        self.writes = 0
        self.lock = threading.Lock()
        self.file = file

    def read(self):
        with LockFile(self.file).read():
            with self.lock:
                self.reads += 1

    def write(self):
        with LockFile(self.file).write():
            with self.lock:
                self.writes += 1


def test_lock_file_reads():
    with tempfile.NamedTemporaryFile() as temp:
        lf = LockFile(temp.name)
        op = MockOperation(lf.lock_file)

        with lf.read():
            for i in range(3):
                threading.Thread(target=op.write).start()

            for i in range(3):
                threading.Thread(target=op.read).start()

            sleep(2)
            assert op.reads == 3
            assert op.writes == 0

        sleep(2)
        assert op.reads == 3
        assert op.writes == 3


def test_lock_file_writes():
    with tempfile.NamedTemporaryFile() as temp:
        lf = LockFile(temp.name)
        op = MockOperation(lf.lock_file)

        with lf.write():
            for i in range(3):
                threading.Thread(target=op.write).start()

            for i in range(3):
                threading.Thread(target=op.read).start()

            sleep(2)
            assert op.reads == 0
            assert op.writes == 0

        sleep(2)
        assert op.reads == 3
        assert op.writes == 3


@pytest.mark.parametrize("frame", [pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), empty_frame()])
def test_file_cache_frame(frame):
    with tempfile.TemporaryDirectory() as temp:
        fc = FileCache(temp)
        with fc.loc("frame") as cache:
            assert cache.read() is None
            cache.write(frame)

        with fc.loc("frame") as cache:
            pd.testing.assert_frame_equal(frame, cache.read())


@pytest.mark.parametrize("series", [pd.Series([1, 2, 3], name="data"), empty_series(name="series")])
def test_file_cache_series(series):
    with tempfile.TemporaryDirectory() as temp:
        fc = FileCache(temp)
        with fc.loc("series") as cache:
            assert cache.read() is None
            cache.write(series)

        with fc.loc("series") as cache:
            pd.testing.assert_series_equal(series, cache.read())


@pytest.mark.parametrize("frame", [pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), empty_frame()])
def test_file_cache_walk_forward(frame):
    with tempfile.TemporaryDirectory() as temp:
        fc = FileCache(temp)
        with fc.loc("frame", "a", "b", current_key=...) as cache:
            assert cache.read() is None
            cache.write(frame)

        with fc.loc("frame", "a", "c", current_key=...) as cache:
            assert cache.read() is None
            pd.testing.assert_frame_equal(frame, cache.read_current())


def test_read_n_to_last_line():
    with tempfile.NamedTemporaryFile() as temp:
        temp = Path(temp.name)
        with temp.open("w") as file:
            file.write("This is a test file\nor is it?\nyes it is.")
        assert read_n_to_last_line(temp) == "yes it is."


def test_read_n_to_last_line_offset():
    with tempfile.NamedTemporaryFile() as temp:
        temp = Path(temp.name)
        with temp.open("w") as file:
            file.write("This is a test file\nor is it?\nyes it is.")
        assert read_n_to_last_line(temp, 2) == "or is it?"


def test_read_n_to_last_line_single_line():
    with tempfile.NamedTemporaryFile() as temp:
        temp = Path(temp.name)
        with temp.open("w") as file:
            file.write("This is a test file.")
        assert read_n_to_last_line(temp, 1) == "This is a test file."


def test_read_n_to_last_line_empty_line():
    with tempfile.NamedTemporaryFile() as temp:
        temp = Path(temp.name)
        with temp.open("w") as file:
            file.write("This is a test file.\nTest\n")
        assert read_n_to_last_line(temp, 1) == ""


def test_read_n_to_last_line_whitespace_line():
    with tempfile.NamedTemporaryFile() as temp:
        temp = Path(temp.name)
        with temp.open("w") as file:
            file.write("This is a test file.\nTest\n\t")
        assert read_n_to_last_line(temp, 1) == "\t"
