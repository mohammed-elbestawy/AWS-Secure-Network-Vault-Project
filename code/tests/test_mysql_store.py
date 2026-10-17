"""Exercises the SQL flow of MySQLStore against a fake DB-API connection.

This does not replace a test against a real MySQL server, but it catches
mistakes in the transaction logic (locking read, burn, rollback paths).
"""
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from store import MySQLStore  # noqa: E402

NOW = datetime(2026, 1, 1, 12, 0, 0)


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.conn.log.append((" ".join(sql.split()), params))
        if sql.lstrip().upper().startswith("DELETE") and "expires_at" in sql:
            self.rowcount = 3

    def fetchone(self):
        return self.conn.row


class FakeConn:
    def __init__(self, row=None):
        self.row = row
        self.log = []
        self.events = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.events.append("commit")

    def rollback(self):
        self.events.append("rollback")

    def close(self):
        self.events.append("close")


def store_with(conn):
    return MySQLStore(lambda: conn)


class MySQLStoreTests(unittest.TestCase):
    def test_reveal_uses_locking_read_and_deletes_on_last_view(self):
        conn = FakeConn(("CT", 0, 1, NOW + timedelta(hours=1)))
        result = store_with(conn).reveal("id", NOW)
        self.assertEqual(result, ("CT", 0))
        self.assertIn("FOR UPDATE", conn.log[0][0])
        self.assertTrue(conn.log[1][0].startswith("DELETE FROM secrets"))
        self.assertEqual(conn.events, ["commit", "close"])

    def test_reveal_increments_views_when_more_remain(self):
        conn = FakeConn(("CT", 1, 3, NOW + timedelta(hours=1)))
        result = store_with(conn).reveal("id", NOW)
        self.assertEqual(result, ("CT", 1))
        self.assertTrue(conn.log[1][0].startswith("UPDATE secrets SET views"))
        self.assertEqual(conn.log[1][1], (2, "id"))

    def test_reveal_expired_deletes_and_returns_none(self):
        conn = FakeConn(("CT", 0, 1, NOW - timedelta(seconds=1)))
        self.assertIsNone(store_with(conn).reveal("id", NOW))
        self.assertTrue(conn.log[1][0].startswith("DELETE FROM secrets"))
        self.assertEqual(conn.events[0], "commit")

    def test_reveal_missing_rolls_back(self):
        conn = FakeConn(None)
        self.assertIsNone(store_with(conn).reveal("id", NOW))
        self.assertEqual(conn.events, ["rollback", "close"])

    def test_peek_never_writes(self):
        conn = FakeConn((1, 3, NOW + timedelta(hours=1)))
        info = store_with(conn).peek("id", NOW)
        self.assertEqual(info["remaining_views"], 2)
        self.assertTrue(all(q[0].startswith("SELECT") for q in conn.log))

    def test_purge_returns_deleted_count(self):
        conn = FakeConn()
        self.assertEqual(store_with(conn).purge_expired(NOW), 3)
        self.assertEqual(conn.events, ["commit", "close"])

    def test_queries_are_parameterised(self):
        conn = FakeConn(("CT", 0, 1, NOW + timedelta(hours=1)))
        evil = "x' OR '1'='1"
        store_with(conn).reveal(evil, NOW)
        for sql, params in conn.log:
            self.assertNotIn(evil, sql)
            self.assertIn("%s", sql)


if __name__ == "__main__":
    unittest.main()
