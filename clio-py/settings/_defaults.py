import multiprocessing
import os
from typing import Literal

__throw = "__throw"

hostname = __throw
username = __throw
usergroup = None
env = "dev"
version = __throw
script_type = __throw
user_home = os.environ.get("HOME")

email_address = None
report_destinations = {}

audit_db = None
audit_db_username = None
audit_db_password = None

audit_db_readonly = None
audit_db_readonly_username = None
audit_db_readonly_password = None

audit_db_backup_username = None
audit_db_backup_password = None
audit_db_backup = None

router_url = None
router_token = None

chart_context: Literal["mpl", "mpld3", "plotly"] = "mpl"

# each process is independent (i.e. don't cache connections/resources between procs)
multiprocessing.set_start_method("spawn", True)
