import pandas as pd

data_path = "/home/idennis/local/data"

tasks_dfn = "/home/idennis/local/dev/cli-o/bin/tasks.jsonl"

audit_db = "clickhouse+native://default:@localhost:4406/default"
# audit_db_readonly = "clickhouse+native://{username}:{password}@localhost:3106/default"

router_url = "http://localhost:4010"
router_token = "dev-token"

pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 500)
pd.set_option("display.width", 1000)
