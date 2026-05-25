from pathlib import Path

from clio_services.alerts import Ticket
from clio_services.alerts.tickets import SchedulePreference
from clio_services.database import schema_for_object

if __name__ == "__main__":
    with Path(__file__).parent.absolute().joinpath("alerts_schema.sql").open("w") as f:
        f.write(schema_for_object(Ticket))
        f.write(schema_for_object(SchedulePreference, "asserted_from"))
