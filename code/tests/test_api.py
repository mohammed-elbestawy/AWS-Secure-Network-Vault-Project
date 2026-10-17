import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import create_app  # noqa: E402
from store import MemoryStore  # noqa: E402

BLOB = "A" * 64
VALID_ID = "A" * 32


class Clock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with open(os.path.join(self.tmp.name, "index.html"), "w") as fh:
            fh.write("<h1>vault</h1>")
        self.clock = Clock()
        self.store = MemoryStore()
        self.app = create_app(store=self.store, frontend_dir=self.tmp.name, clock=self.clock)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, **overrides):
        body = {"ciphertext": BLOB, "ttl": 3600, "max_views": 1}
        body.update(overrides)
        return self.client.post("/api/secrets", json=body)

    # --- create -----------------------------------------------------------
    def test_create_returns_id_and_expiry(self):
        resp = self.create()
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertRegex(data["id"], r"^[A-Za-z0-9_-]{32}$")
        self.assertEqual(data["expires_at"], "2026-01-01T13:00:00Z")

    def test_ids_are_unique(self):
        ids = {self.create().get_json()["id"] for _ in range(50)}
        self.assertEqual(len(ids), 50)

    def test_rejects_invalid_ciphertext_characters(self):
        for bad in ["a b" * 20, "<script>" + "A" * 40, "A" * 39 + "=", "'; DROP TABLE secrets;--" + "A" * 20]:
            self.assertEqual(self.create(ciphertext=bad).status_code, 400, bad)

    def test_rejects_wrong_sizes(self):
        self.assertEqual(self.create(ciphertext="A" * 10).status_code, 400)
        self.assertEqual(self.create(ciphertext="A" * 7169).status_code, 400)
        self.assertEqual(self.create(ciphertext="A" * 20000).status_code, 413)

    def test_rejects_bad_ttl_and_views(self):
        for ttl in [0, 60, 99999999, "3600", None, True, 3600.5]:
            self.assertEqual(self.create(ttl=ttl).status_code, 400, ttl)
        for views in [0, 6, -1, "1", True, 1.5]:
            self.assertEqual(self.create(max_views=views).status_code, 400, views)

    def test_rejects_non_json_and_wrong_shapes(self):
        resp = self.client.post("/api/secrets", data="ciphertext=AAAA", content_type="text/plain")
        self.assertEqual(resp.status_code, 415)
        resp = self.client.post("/api/secrets", json=["x"])
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post("/api/secrets", data="{not json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_rejects_oversized_body(self):
        resp = self.client.post("/api/secrets", data="x" * 40000, content_type="application/json")
        self.assertEqual(resp.status_code, 413)

    # --- read and burn ----------------------------------------------------
    def test_reveal_burns_after_one_view(self):
        sid = self.create().get_json()["id"]
        first = self.client.post(f"/api/secrets/{sid}/reveal")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json(), {"ciphertext": BLOB, "remaining_views": 0})
        second = self.client.post(f"/api/secrets/{sid}/reveal")
        self.assertEqual(second.status_code, 404)

    def test_multiple_views_count_down(self):
        sid = self.create(max_views=3).get_json()["id"]
        remaining = [self.client.post(f"/api/secrets/{sid}/reveal").get_json()["remaining_views"] for _ in range(3)]
        self.assertEqual(remaining, [2, 1, 0])
        self.assertEqual(self.client.post(f"/api/secrets/{sid}/reveal").status_code, 404)

    def test_status_does_not_burn(self):
        sid = self.create().get_json()["id"]
        for _ in range(5):
            resp = self.client.get(f"/api/secrets/{sid}/status")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()["remaining_views"], 1)
        self.assertEqual(self.client.post(f"/api/secrets/{sid}/reveal").status_code, 200)

    def test_get_on_reveal_does_not_burn(self):
        sid = self.create().get_json()["id"]
        self.assertEqual(self.client.get(f"/api/secrets/{sid}/reveal").status_code, 404)
        self.assertEqual(self.client.get(f"/api/secrets/{sid}/status").status_code, 200)
        self.assertEqual(self.client.post(f"/api/secrets/{sid}/reveal").status_code, 200)

    def test_expired_secret_is_gone(self):
        sid = self.create(ttl=3600).get_json()["id"]
        self.clock.advance(3601)
        self.assertEqual(self.client.get(f"/api/secrets/{sid}/status").status_code, 404)
        self.assertEqual(self.client.post(f"/api/secrets/{sid}/reveal").status_code, 404)

    def test_unknown_and_malformed_ids_look_the_same(self):
        for sid in [VALID_ID, "short", "A" * 33, "' OR 1=1 --", "%00" * 10, "A" * 31 + "!"]:
            resp = self.client.post(f"/api/secrets/{sid}/reveal")
            self.assertEqual(resp.status_code, 404, sid)
            self.assertEqual(resp.get_json(), {"error": "not_found"})

    def test_purge_removes_only_expired(self):
        old = self.create(ttl=3600).get_json()["id"]
        fresh = self.create(ttl=86400).get_json()["id"]
        self.clock.advance(7200)
        self.assertEqual(self.store.purge_expired(self.clock()), 1)
        self.assertEqual(self.client.get(f"/api/secrets/{old}/status").status_code, 404)
        self.assertEqual(self.client.get(f"/api/secrets/{fresh}/status").status_code, 200)

    def test_concurrent_reveal_only_one_winner(self):
        sid = self.create(max_views=1).get_json()["id"]
        results = []

        def worker():
            client = self.app.test_client()
            results.append(client.post(f"/api/secrets/{sid}/reveal").status_code)

        threads = [threading.Thread(target=worker) for _ in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count(200), 1)
        self.assertEqual(results.count(404), 24)

    # --- headers, health, static -----------------------------------------
    def test_security_headers_present(self):
        resp = self.client.get("/healthz")
        self.assertIn("script-src 'self'", resp.headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", resp.headers["Content-Security-Policy"])
        self.assertEqual(resp.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp.headers["Referrer-Policy"], "no-referrer")

    def test_api_responses_are_not_cacheable(self):
        sid = self.create().get_json()["id"]
        for resp in [self.client.get("/api/health"), self.client.get(f"/api/secrets/{sid}/status")]:
            self.assertEqual(resp.headers["Cache-Control"], "no-store")

    def test_health_endpoints(self):
        self.assertEqual(self.client.get("/healthz").get_json(), {"status": "ok"})
        self.assertEqual(self.client.get("/api/health").status_code, 200)

    def test_health_reports_database_down(self):
        class Broken(MemoryStore):
            def ping(self):
                raise RuntimeError("down")

        client = create_app(store=Broken(), frontend_dir=self.tmp.name, clock=self.clock).test_client()
        self.assertEqual(client.get("/api/health").status_code, 503)

    def test_root_serves_index_for_alb_health_check(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"vault", resp.data)

    def test_static_traversal_is_blocked(self):
        for path in ["/../backend/app.py", "/%2e%2e/backend/app.py", "/nope.txt", "/api/unknown"]:
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_logs_do_not_contain_full_ids(self):
        sid = self.create().get_json()["id"]
        with self.assertLogs(self.app.logger, level="INFO") as captured:
            self.client.post(f"/api/secrets/{sid}/reveal")
        text = "\n".join(captured.output)
        self.assertNotIn(sid, text)
        self.assertIn(sid[:6] + "...", text)


if __name__ == "__main__":
    unittest.main()
