import pandas as pd

audit_db = "clickhouse+native://default:@localhost:4406/default"
# audit_db_readonly = "clickhouse+native://{username}:{password}@localhost:3106/default"

router_url = "http://localhost:4010"
router_token = "dev-token"

pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 500)
pd.set_option("display.width", 1000)
