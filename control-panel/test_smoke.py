#!/usr/bin/env python3
"""Smoke tests for control-panel PR #24."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Isolate test DB
TEST_ROOT = Path(tempfile.mkdtemp(prefix="cp-test-"))
os.environ["CONTROL_PANEL_SECRET"] = "test-secret-key-for-ci"
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "testpass123"

PANEL = Path(__file__).resolve().parent
sys.path.insert(0, str(PANEL))

# Patch DB path before imports
import backend.database as db  # noqa: E402

db.DATA_DIR = TEST_ROOT / "data"
db.DB_PATH = db.DATA_DIR / "control_panel.db"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


class ControlPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        from backend.auth import ensure_default_admin

        ensure_default_admin()
        cls.client = TestClient(app)
        login = cls.client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "testpass123"},
        )
        assert login.status_code == 200, login.text
        cls.token = login.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_login_bad_password(self):
        r = self.client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "wrong"},
        )
        self.assertEqual(r.status_code, 401)

    def test_stats_authenticated(self):
        r = self.client.get("/api/stats", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ("total_jobs", "running", "success", "failed", "engagements"):
            self.assertIn(key, data)

    def test_settings_list(self):
        r = self.client.get("/api/settings", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        settings = r.json()
        self.assertGreater(len(settings), 5)
        keys = {s["key"] for s in settings}
        self.assertIn("app_name", keys)
        self.assertIn("default_target", keys)

    def test_settings_admin_update(self):
        r = self.client.put(
            "/api/settings/app_name",
            headers=self.headers,
            json={"value": "Test Panel"},
        )
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get("/api/settings/app_name", headers=self.headers)
        self.assertEqual(r2.json()["value"], "Test Panel")

    def test_settings_bulk_update(self):
        r = self.client.post(
            "/api/settings/bulk",
            headers=self.headers,
            json={"max_parallel_jobs": "3"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["updated"], "1")

    def test_tools_list(self):
        r = self.client.get("/api/tools", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        tools = r.json()
        self.assertGreaterEqual(len(tools), 7)
        ids = {t["id"] for t in tools}
        self.assertIn("waf_bypass_probe", ids)
        self.assertIn("bruter", ids)

    def test_engagement_crud(self):
        r = self.client.post(
            "/api/engagements",
            headers=self.headers,
            json={
                "name": "test-eng",
                "target_url": "https://example.com",
                "notes": "unit test",
            },
        )
        self.assertEqual(r.status_code, 200)
        eid = r.json()["id"]
        r2 = self.client.get("/api/engagements", headers=self.headers)
        self.assertTrue(any(e["id"] == eid for e in r2.json()))
        r3 = self.client.delete(f"/api/engagements/{eid}", headers=self.headers)
        self.assertEqual(r3.status_code, 200)

    def test_audit_log_admin(self):
        r = self.client.get("/api/audit", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_static_index(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers.get("content-type", ""))

    def test_static_assets(self):
        r = self.client.get("/assets/styles.css")
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get("/assets/app.js")
        self.assertEqual(r2.status_code, 200)

    def test_unauthenticated_rejected(self):
        r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 401)

    def test_job_runner_tools_defined(self):
        from backend import job_runner

        self.assertIn("waf_bypass_probe", job_runner.TOOLS)
        self.assertIn("engagement_recon", job_runner.TOOLS)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
