import functools
import socket

_audit_db: str = None
_audit_db_username = None
_audit_db_password = None

_audit_db_readonly: str = None
_audit_db_readonly_username = None
_audit_db_readonly_password = None

_audit_db_backup: str = None
_audit_db_backup_username = None
_audit_db_backup_password = None

_router_url = None
_router_token = None

_tasks_dfn = None

hostname = socket.gethostname().split(".")[0].lower()
secondary_host = None


@functools.cache
def audit_db():
    from clio.dbs import Database

    rw_conn_str = _audit_db.format(username=_audit_db_username, password=_audit_db_password) if _audit_db else None
    if _audit_db_readonly is None:
        return Database(rw_conn_str)
    else:
        ro_conn_str = _audit_db_readonly.format(
            username=_audit_db_readonly_username, password=_audit_db_readonly_password
        )
        return Database(ro_conn_str, write_connection=rw_conn_str)


@functools.cache
def audit_db_backup():
    from clio.dbs import Database

    rw_conn_str = (
        _audit_db_backup.format(username=_audit_db_backup_username, password=_audit_db_backup_password)
        if _audit_db_backup
        else None
    )
    return Database(rw_conn_str)


@functools.cache
def shutdown_handler():
    from clio.process import ShutdownHandler

    return ShutdownHandler()


@functools.cache
def router_client():
    from clio.router import RouterClient

    return RouterClient(_router_url, _router_token)
