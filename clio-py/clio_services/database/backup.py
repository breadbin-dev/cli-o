import argparse
import logging
from contextlib import ExitStack

import clio_services
from clio import DttmLike
from clio.collections import compare_collections

_logger = logging.getLogger(__name__)


def backup(path: str = ..., incremental: bool = ..., secondary: bool = False):
    _logger.info("Starting database backup...")
    audit_db = clio_services.audit_db_backup() if secondary else clio_services.audit_db()
    audit_db.backup(path, incremental)
    _logger.info("Database backup completed.")


def restore(as_of_dttm: DttmLike = "latest", secondary: bool = False, from_host: str = ...):
    _logger.info("Starting database restore...")
    audit_db = clio_services.audit_db_backup() if secondary else clio_services.audit_db()
    if not secondary and from_host is ...:
        from_host = clio_services.secondary_host
    audit_db.restore(as_of_dttm, from_host)
    _logger.info("Database restore completed.")


def compare_dbs():
    _logger.info("Starting database comparison...")
    db = clio_services.audit_db()
    db_backup = clio_services.audit_db_backup()

    table_hashes = db.get_table_hash()
    restore_table_hashes = db_backup.get_table_hash()

    table_base_only, table_both, table_restore_only = compare_collections(table_hashes, restore_table_hashes)

    is_equal = not (table_base_only or table_restore_only)

    if is_equal:
        _logger.info(f"Databases are equal: {db.clickhouse_url(False)} == {db_backup.clickhouse_url(False)}")
    else:
        _logger.error(f"Differences for tables {', '.join(table_base_only.keys() & table_restore_only.keys())}")
        raise Exception(f"Databases are not equal: {db.clickhouse_url(False)} != {db_backup.clickhouse_url(False)}")


def _parse_args():
    parser = argparse.ArgumentParser(description="Database operations: backup, restore, compare.")
    parser.add_argument("--backup_primary", action="store_true", help="Perform database backup on primary database.")
    parser.add_argument(
        "--backup_secondary", action="store_true", help="Perform database backup on secondary database."
    )
    parser.add_argument(
        "--restore_secondary", action="store_true", help="Perform database restore on secondary database."
    )
    parser.add_argument("--restore_primary", action="store_true", help="Perform database restore on primary database.")
    parser.add_argument("--restore_from", type=str, help="Restore database from given host.", default=...)
    parser.add_argument("--compare", action="store_true", help="Compare live and restored databases.")
    parser.add_argument("--as_of", help="As of dttm for restore.", default="latest")

    return parser.parse_args()


def main():
    args = _parse_args()

    if args.restore_primary and args.restore_secondary:
        raise ValueError("Can only set one of --restore_primary and --restore_secondary.")

    if args.backup_primary and args.backup_secondary:
        raise ValueError("Can only set one of --backup_primary and --backup_secondary.")

    with ExitStack() as exit_stack:
        if args.compare:
            exit_stack.enter_context(clio_services.audit_db().stop_merges())
            exit_stack.enter_context(clio_services.audit_db_backup().stop_merges())

        if args.backup_primary:
            backup(secondary=False)

        if args.backup_secondary:
            backup(secondary=True)

        if args.restore_primary:
            restore(secondary=False, as_of_dttm=args.as_of, from_host=args.restore_from)
            if args.compare:
                exit_stack.enter_context(clio_services.audit_db().stop_merges())  # restore removes stop merges command

        if args.restore_secondary:
            restore(secondary=True, as_of_dttm=args.as_of, from_host=args.restore_from)
            if args.compare:
                exit_stack.enter_context(clio_services.audit_db_backup().stop_merges())

        if args.compare:
            compare_dbs()


if __name__ == "__main__":
    main()
