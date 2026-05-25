from pathlib import Path
from clio_services.database import schema_for_object
from clio_services.monitoring.server_monitor import (
    FileSystemUsage,
    ProcessResources,
    CpuUsage,
    CpuUtilisation,
    MemoryUtilisation,
)

if __name__ == "__main__":
    with Path(__file__).parent.absolute().joinpath("monitoring_schema.sql").open("w") as f:
        f.write(schema_for_object(FileSystemUsage))
        f.write(schema_for_object(ProcessResources))
        f.write(schema_for_object(CpuUsage))
        f.write(schema_for_object(CpuUtilisation))
        f.write(schema_for_object(MemoryUtilisation))
