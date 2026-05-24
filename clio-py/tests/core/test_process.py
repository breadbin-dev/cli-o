import os
import gc


from core.process import process_status, ProcessStatus, ProcessStatusContext


def test_process_status_current_process():
    status = process_status()

    assert isinstance(status, ProcessStatus)
    assert status.Pid > 0
    assert status.VmPeak > 0
    assert status.VmSize > 0
    assert status.VmHWM > 0
    assert status.VmRSS > 0


def test_process_status_with_pid():
    pid = os.getpid()
    status = process_status(pid=pid)

    assert isinstance(status, ProcessStatus)
    assert status.Pid == pid
    assert status.VmPeak > 0


def test_process_status_fields_are_ints():
    status = process_status()

    assert isinstance(status.Pid, int)
    assert isinstance(status.VmPeak, int)
    assert isinstance(status.VmSize, int)
    assert isinstance(status.VmHWM, int)
    assert isinstance(status.VmRSS, int)
    assert isinstance(status.RssAnon, int)
    assert isinstance(status.RssFile, int)
    assert isinstance(status.RssShmem, int)


def test_process_status_context_manager():
    with ProcessStatusContext() as psc:
        x = [i for i in range(1000)]  # noqa
        y = [i for i in range(10000000)]  # noqa
        del y
        gc.collect()

    assert psc.before is not None
    assert psc.after is not None
    assert isinstance(psc.before, ProcessStatus)
    assert isinstance(psc.after, ProcessStatus)
    assert psc.before.Pid == psc.after.Pid
    assert psc.after.VmPeak > psc.before.VmPeak
    assert psc.after.VmHWM > psc.after.VmRSS


def test_process_status_serialization():
    status = process_status()

    status_dict = status.__to_dict__()
    assert isinstance(status_dict, dict)
    assert "ProcessStatus" in status_dict
    inner_dict = status_dict["ProcessStatus"]
    assert "Pid" in inner_dict
    assert "VmPeak" in inner_dict
    assert "VmRSS" in inner_dict

    restored = ProcessStatus.__from_dict__(status_dict)
    assert isinstance(restored, ProcessStatus)
    assert restored == status
    assert restored.Pid == status.Pid
    assert restored.VmRSS == status.VmRSS


def test_process_status_context_serialization():
    with ProcessStatusContext() as psc:
        x = [i for i in range(1000)]  # noqa

    context_dict = psc.__to_dict__()
    assert isinstance(context_dict, dict)
    assert "ProcessStatusContext" in context_dict
    inner_dict = context_dict["ProcessStatusContext"]
    assert "before" in inner_dict
    assert "after" in inner_dict
    assert inner_dict["before"] is not None
    assert inner_dict["after"] is not None

    restored = ProcessStatusContext.__from_dict__(context_dict)
    assert isinstance(restored, ProcessStatusContext)
    assert isinstance(restored.before, ProcessStatus)
    assert isinstance(restored.after, ProcessStatus)
    assert restored.pid == psc.pid
