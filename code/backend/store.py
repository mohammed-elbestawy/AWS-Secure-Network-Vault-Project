"""Storage backends.

MemoryStore is used for tests and local development. MySQLStore is the
production backend (RDS MySQL). Both expose the same small interface and both
make "read and burn" a single atomic operation.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone


class MemoryStore:
    def __init__(self):
        self._rows = {}
        self._lock = threading.Lock()

    def ping(self) -> bool:
        return True

    def create(self, id_, ciphertext, expires_at, max_views):
        with self._lock:
            self._rows[id_] = {
                "ciphertext": ciphertext,
                "expires_at": expires_at,
                "views": 0,
                "max_views": max_views,
            }

    def peek(self, id_, now):
        with self._lock:
            row = self._rows.get(id_)
            if row is None:
                return None
            if row["expires_at"] <= now:
                del self._rows[id_]
                return None
            return {
                "expires_at": row["expires_at"],
                "remaining_views": row["max_views"] - row["views"],
            }

    def reveal(self, id_, now):
        with self._lock:
            row = self._rows.get(id_)
            if row is None:
                return None
            if row["expires_at"] <= now:
                del self._rows[id_]
                return None
            row["views"] += 1
            remaining = row["max_views"] - row["views"]
            if remaining <= 0:
                del self._rows[id_]
            return row["ciphertext"], max(remaining, 0)

    def purge_expired(self, now):
        with self._lock:
            dead = [k for k, v in self._rows.items() if v["expires_at"] <= now]
            for k in dead:
                del self._rows[k]
            return len(dead)


class MySQLStore:
    """RDS MySQL backend. `connect` returns a new DB-API connection."""

    def __init__(self, connect):
        self._connect = connect

    def ping(self) -> bool:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        finally:
            conn.close()

    def create(self, id_, ciphertext, expires_at, max_views):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO secrets (id, ciphertext, expires_at, views, max_views) "
                    "VALUES (%s, %s, %s, 0, %s)",
                    (id_, ciphertext, expires_at, max_views),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def peek(self, id_, now):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT views, max_views, expires_at FROM secrets WHERE id = %s",
                    (id_,),
                )
                row = cur.fetchone()
            conn.rollback()
            if row is None:
                return None
            views, max_views, expires_at = row
            if expires_at <= now:
                return None
            return {"expires_at": expires_at, "remaining_views": max_views - views}
        finally:
            conn.close()

    def reveal(self, id_, now):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ciphertext, views, max_views, expires_at "
                    "FROM secrets WHERE id = %s FOR UPDATE",
                    (id_,),
                )
                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    return None
                ciphertext, views, max_views, expires_at = row
                if expires_at <= now:
                    cur.execute("DELETE FROM secrets WHERE id = %s", (id_,))
                    conn.commit()
                    return None
                views += 1
                if views >= max_views:
                    cur.execute("DELETE FROM secrets WHERE id = %s", (id_,))
                else:
                    cur.execute(
                        "UPDATE secrets SET views = %s WHERE id = %s", (views, id_)
                    )
            conn.commit()
            return ciphertext, max(max_views - views, 0)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def purge_expired(self, now):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM secrets WHERE expires_at <= %s", (now,))
                count = cur.rowcount
            conn.commit()
            return count
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
