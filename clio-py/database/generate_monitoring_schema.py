from pathlib import Path
from core.alerts import Ticket
from core.alerts.tickets import SchedulePreference
from core.monitoring.server_monitor import (
    FileSystemUsage,
    ProcessResources,
    CpuUsage,
    CpuUtilisation,
    MemoryUtilisation,
)
from database import schema_for_object

if __name__ == "__main__":
    with Path(__file__).parent.absolute().joinpath("monitoring_schema.sql").open("w") as f:
        f.write(schema_for_object(FileSystemUsage))
        f.write(schema_for_object(ProcessResources))
        f.write(schema_for_object(CpuUsage))
        f.write(schema_for_object(CpuUtilisation))
        f.write(schema_for_object(MemoryUtilisation))
        f.write(schema_for_object(Ticket))
        f.write(schema_for_object(SchedulePreference, "asserted_from"))
