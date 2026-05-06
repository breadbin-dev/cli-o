from __future__ import annotations
import functools
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from core.dbs import Database
    from core.process import ShutdownHandler
    from core.router import RouterClient

import settings


@functools.cache
def audit_db() -> Database:
    from core.dbs import Database

    rw_conn_str = (
        settings.audit_db.format(username=settings.audit_db_username, password=settings.audit_db_password)
        if settings.audit_db
        else None
    )
    if settings.audit_db_readonly is None:
        return Database(rw_conn_str)
    else:
        ro_conn_str = settings.audit_db_readonly.format(
            username=settings.audit_db_readonly_username, password=settings.audit_db_readonly_password
        )
        return Database(ro_conn_str, write_connection=rw_conn_str)


@functools.cache
def audit_db_backup() -> Database:
    from core.dbs import Database

    rw_conn_str = (
        settings.audit_db_backup.format(
            username=settings.audit_db_backup_username, password=settings.audit_db_backup_password
        )
        if settings.audit_db_backup
        else None
    )
    return Database(rw_conn_str)


@functools.cache
def shutdown_handler() -> ShutdownHandler:
    from core.process import ShutdownHandler

    return ShutdownHandler()


@functools.cache
def router_client() -> RouterClient:
    from core.router import RouterClient

    return RouterClient(settings.router_url, settings.router_token)
