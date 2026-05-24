import dataclasses
import json
import math
import random
import re
import logging
from typing import Literal

import pandas as pd
from tabulate import tabulate

import settings
from core import services, DttmLike, dbs, dttms, strs, Keyed, Key, arrays
from core.alerts import Ticket
from core.collections import ensure_list
from core.strs import from_jsonl


def _read_checks():
    result = {}

    if settings.tasks_dfn is None:
        return result

    for task in from_jsonl(settings.tasks_dfn):
        task_dfn = task["task"]
        check = task_dfn.get("check")
        if check is not None:
            task_name = task["name"]
            task_key = task_dfn["key"].split(":")[0]
            result[task_key] = task_name, check

    return result


sos_tickets = set()


class TicketsWidget:

    """ticketing system"""

    def __init__(self):
        self._slack_support = (None, None)

        self._schedule_allocator = ScheduleAllocator(
            options=["MonAM", "MonPM", "TueAM", "TuePM", "WedAM", "WedPM", "ThuAM", "ThuPM", "FriAM", "FriPM"]
        )

    def status(
        self,
        from_dttm: DttmLike = "T-3M",
        to_dttm: DttmLike = "now",
        group: str = None,
        closed: bool = False,
        _decorator=None,
    ):
        """
        list ops genie tickets
        :param from_dttm: from dttm
        :param to_dttm: to dttm
        :param group: the check key
        :param closed: also show closed tickets
        :param ops_genie: go directly to ops genie
        :param _decorator: hints for rendering the result
        """

        df = self._tickets(from_dttm, to_dttm, group=group, closed=closed)

        df["ack"] = "ack"
        df["close"] = ""
        df.loc[df["open"], "close"] = "close"

        tasks = _read_checks()
        df["key"] = [a.split("|")[1].split(":")[0] for a in df["id"]]
        df["task"] = [tasks.get(k, [""])[0] for k in df["key"]]
        df["command"] = [tasks.get(k, ["", ""])[1] for k in df["key"]]

        if _decorator is not None:
            _decorator.drill(df, "tickets.ack -t &quot;%s&quot;", "ack", lambda row: row["id"])
            _decorator.drill(df, "tickets.close -t &quot;%s&quot;", "close", lambda row: row["id"])
            _decorator.drill(df, "tasks.run -t &quot;%s&quot;", "task")
            _decorator.drill(df, "%s", "command")

        return df.loc[:, ("id", "message", "owner", "ack", "close", "task", "command", "dttm")]

    def create(self, id: str, message: str, sos: bool = False):
        """
        create ops genie ticket
        :param id: our ticket reference (can be duplicate)
        :param message: the ticket message
        :param sos: also raise via sos
        """
        group = id.split(":", 1)[0]
        now = dttms.now()
        ticket = Ticket(now, id, group, message, True, False, "", now)
        services.audit_db().insert(ticket)

    def _ticket(self, id):
        db = services.audit_db()
        ticket = db.select(Ticket, f"select distinct on (id) * from ticket where id = '{id}' order by dttm desc")
        if len(ticket) == 0:
            raise Exception(f"unknown ticket: {id}")
        return ticket[0]

    def _tickets(self, from_dttm, to_dttm, group=None, closed=False, as_frame=True):
        db = services.audit_db()
        sql = f"select distinct on (id) * from ticket where {dbs.sql_dttms(from_dttm, to_dttm)}"
        if group:
            sql += f" and group = '{group}'"

        sql += " order by dttm desc"

        if not closed:
            sql = f"select * from ({sql}) where open"

        if as_frame:
            return db.query(sql)
        else:
            return db.select(Ticket, sql)

    def _user(self, user, _username):
        if user:
            return user
        if _username:
            return _username
        raise Exception("user not specified")

    def ack(self, ticket: str, user: str = None, _username=None):
        """
        acknowledge ticket
        :param ticket: id of ticket
        :param user: override ack'ing user
        """
        update = self._ticket(ticket)
        update.acknowledged = True
        update.owner = self._user(user, _username)
        update.dttm = dttms.now()
        services.audit_db().insert(update)

    def close(self, ticket: str, user: str = None, _username=None):
        """
        close ticket
        :param ticket: id of ticket
        :param user: override closing user
        """
        update = self._ticket(ticket)
        update.open = False
        update.owner = self._user(user, _username)
        update.dttm = dttms.now()
        services.audit_db().insert(update)

    def update(self, ticket: str, message: str):
        """
        update ticket
        :param ticket: id of ticket
        :param message: updated message
        """
        update = self._ticket(ticket)
        update.message = message
        update.dttm = dttms.now()
        services.audit_db().insert(update)

    def bulk(self, key: str, tickets: str | dict, mode: Literal["add", "diff"], _username=None):
        """
        bulk create/close of tickets based on existing keys
        :param key: the root of the ticket key
        :param tickets: json map of key: message
        :param mode: whether to diff tickets, or just add
        """
        if isinstance(tickets, str):
            tickets = json.loads(tickets)

        existing = self.status(group=key)
        if len(existing) == 0:
            existing = {}
        else:
            existing = {k: v for k, v in zip(existing["id"].values, existing["message"].values)}
        to_close = [] if mode == "add" else [t for t in existing if t not in tickets]

        for ticket in to_close:
            self.close(ticket, _username=_username)
            logging.info(f"Closed ticket [{ticket}]")

        is_sos = key in sos_tickets
        for ticket, msg in tickets.items():
            msg = msg.replace("'", "`")  # DB safety
            if ticket not in existing:
                self.create(ticket, msg, sos=is_sos)
                logging.info(f"Opened ticket [{ticket}: {msg}]")
            elif msg[:130] != existing[ticket][:130]:
                self.update(ticket, msg)
                logging.info(f"Updating ticket [{ticket}: {msg}]")

    def cover(
        self,
        from_dttm: DttmLike = "now",
        to_dttm: DttmLike = ...,
        user: str = ...,
        prefs: str = None,
        _username: str = None,
    ):
        """
        add/remove an override to the coverage schedule
        :param schedule: schedule name
        :param from_dttm: from dttm or period (e.g. MonAM for monday morning)
        :param to_dttm: to dttm will default to end of period
        :param user: the user to add/remove
        :param remove: remove the override
        :param prefs: set your schedule prefs (up to +10, -10) in the form +2:-2 for each day monday-friday
        """

        if prefs is not None:
            if user is ...:
                user = _username
            self._schedule_allocator.save_prefs(user, prefs, from_dttm, to_dttm)
            return self.cover_prefs(_username=user)
        else:
            raise Exception("rota functionality")

    def cover_prefs(self, users: list[str] = None, _username: str = None):
        """
        show schedule prefs
        :param users: list of usernames (*) for all
        """

        if users is None:
            users = _username

        if users is not None and users == ["*"]:
            users = ...

        prefs = self._schedule_allocator.get_prefs(users)
        dfs = []

        for user, pref in prefs.items():
            df = pd.DataFrame(columns=pref.keys(), index=[user], data=[pref.values()])
            dfs.append(df)

        return arrays.concat(*dfs)

    def update_schedule(self, as_of_dttm: DttmLike = ..., commit: bool = False):
        """
        Generate a schedule based on user preferences
        :param as_of_dttm: as of dttm (default to this saturday for the following week)
        :param commit: commit the schedule to ops genie
        """

        if as_of_dttm is ...:
            as_of_dttm = dttms.parse_dttm("Sat+11am", to_dttm=True)  # next week

        prefs = self._schedule_allocator.get_prefs(as_of_dttm=as_of_dttm)
        allocs = self._schedule_allocator.allocate(prefs)
        df = pd.DataFrame(columns=allocs.keys(), index=[as_of_dttm], data=[allocs.values()])

        if commit:
            for option, user in allocs.items():
                from_dttm, to_dttm = dttms.parse_schedule_dttms(option, ..., now_dttm=as_of_dttm)
                self.cover(from_dttm=from_dttm, to_dttm=to_dttm, user=user)

            tbl = tabulate(df, headers=allocs.keys(), tablefmt="plain", showindex=True)
            logging.info(tbl)

        return df


@dataclasses.dataclass
class SchedulePreference(Keyed):
    username: str
    prefs: str
    asserted_from: DttmLike = None
    asserted_to: DttmLike = None

    __nullable_fields__ = ["asserted_to"]

    def key(self) -> Key:
        return Key(self.username)


class ScheduleAllocator:
    def __init__(self, options):
        self.options = options

    def validate_prefs(self, prefs: list[str] | str):
        if isinstance(prefs, str):
            prefs = re.split(r"[\s:]+", prefs)
        assert len(prefs) == len(self.options), f"len(prefs)[{len(prefs)}] must match len(options)[{len(self.options)}]"
        prefs = {o: int(p) for o, p in zip(self.options, prefs)}
        assert sum(v for v in prefs.values() if v > 0) <= len(self.options), f"upvotes limited to {len(self.options)}"
        assert sum(v for v in prefs.values() if v < 0) >= -len(
            self.options
        ), f"downvotes limited to -{len(self.options)}"
        return prefs

    def save_prefs(self, username: str, prefs: str, from_dttm: DttmLike, to_dttm: DttmLike):
        prefs = self.validate_prefs(prefs)
        assert username is not None

        from_dttm = dttms.as_dttm(from_dttm)
        if to_dttm is ...:
            to_dttm = None
        elif to_dttm is not None:
            to_dttm = dttms.as_dttm(to_dttm)
        prefs = SchedulePreference(username, strs.to_json(prefs), asserted_from=from_dttm, asserted_to=to_dttm)
        db = services.audit_db()
        pref = self.get_prefs(usernames=[username], parsed=False)
        if pref:
            assert len(pref) == 1
            prev_pref = pref[0]
            db.update(
                f"alter table schedule_preference update asserted_to = '{from_dttm}' where username = '{username}'"
                f" and asserted_from = '{dttms.format_dttm_sql(prev_pref.asserted_from)}'",
            )
        db.insert(prefs)

    def get_prefs(self, usernames=..., as_of_dttm=..., parsed=True):
        if as_of_dttm is ...:
            as_of_dttm = dttms.now()

        query = f"select * from schedule_preference where {dbs.sql_asof(as_of_dttm)}"
        if usernames is not ...:
            usernames = ensure_list(usernames)
            query += f" AND username in {dbs.sql_list(usernames)}"
        prefs = services.audit_db().select(SchedulePreference, query)
        if parsed:
            return {p.username: strs.from_json(p.prefs) for p in prefs}
        else:
            return prefs

    def _next_alloc(self, votes, results, allocs, max_alloc):
        max_votes = {o: max(up.values()) for o, up in votes.items()}
        max_vote = max(max_votes.values())
        option = random.choice([o for o, v in max_votes.items() if v == max_vote])
        user = random.choice([u for u, p in votes[option].items() if p == max_vote])
        results[option] = user
        votes.pop(option)
        allocs[user] = (alloc := allocs[user] + 1)
        if alloc == max_alloc:
            [v.pop(user) for v in votes.values()]

    def allocate(self, user_prefs):
        user_prefs = user_prefs.copy()
        max_alloc = math.ceil(len(self.options) / len(user_prefs))
        allocs = {u: 0 for u in user_prefs.keys()}
        votes = {o: {u: p[o] for u, p in user_prefs.items()} for o in self.options}
        results = {}
        while votes:
            self._next_alloc(votes, results, allocs, max_alloc)
        return {o: results[o] for o in self.options}


if __name__ == "__main__":
    tw = TicketsWidget()

    def main():
        import logging
        import settings
        from core.widget import WidgetWrapper

        logging.info(settings.process_descriptor())

        router = services.router_client()
        WidgetWrapper.host_object("tickets", tw, router)

    main()
