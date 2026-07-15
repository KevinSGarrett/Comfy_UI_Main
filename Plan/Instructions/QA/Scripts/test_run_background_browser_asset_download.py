from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "run_background_browser_asset_download.py"
SPEC = importlib.util.spec_from_file_location("background_browser_download", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BackgroundBrowserDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "Chrome User Data"
        profile = self.source / "Default"
        (profile / "Network").mkdir(parents=True)
        (self.source / "Local State").write_text("{}\n", encoding="utf-8")
        (profile / "Preferences").write_text("{}\n", encoding="utf-8")
        connection = sqlite3.connect(profile / "Network/Cookies")
        connection.execute("create table cookies (host_key text, name text, encrypted_value blob)")
        connection.execute("insert into cookies values (?, ?, ?)", (".civitai.com", "session", b"encrypted"))
        connection.commit()
        connection.close()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_seed_profile_copies_browser_managed_cookie_db_without_serializing_values(self) -> None:
        target = self.root / "Dedicated Headless Profile"
        marker = MODULE.seed_browser_profile(self.source, "Default", target)
        self.assertFalse(marker["cookie_values_serialized"])
        self.assertTrue(marker["profile_stored_outside_project"])
        copied = sqlite3.connect(target / "Default/Network/Cookies")
        try:
            count = copied.execute("select count(*) from cookies where host_key = '.civitai.com'").fetchone()[0]
        finally:
            copied.close()
        self.assertEqual(count, 1)
        serialized = (target / "COMFY_UI_MAIN_HEADLESS_PROFILE.json").read_text(encoding="utf-8")
        self.assertNotIn("encrypted", serialized)

    def test_profile_refresh_removes_only_subtrees(self) -> None:
        profile_root = self.root / "profile"
        subtree = profile_root / "Default/IndexedDB"
        subtree.mkdir(parents=True)
        (subtree / "data").write_text("x", encoding="utf-8")
        MODULE.remove_profile_subtree(subtree, profile_root)
        self.assertFalse(subtree.exists())
        with self.assertRaises(MODULE.BackgroundBrowserError):
            MODULE.remove_profile_subtree(profile_root, profile_root)

    def test_default_profile_location_is_outside_project(self) -> None:
        project = Path("C:/Comfy_UI_Main").resolve()
        profile = MODULE.DEFAULT_HEADLESS_PROFILE.resolve()
        with self.assertRaises(ValueError):
            profile.relative_to(project)

    def test_dedicated_profile_initialization_does_not_copy_source_profile(self) -> None:
        target = self.root / "Dedicated"
        marker = MODULE.initialize_browser_profile(target)
        self.assertEqual(marker["profile_kind"], "dedicated_persistent_headless")
        self.assertFalse(marker["source_profile_copied"])
        self.assertTrue((target / "Default").is_dir())

    def test_session_cookie_is_loaded_from_environment_without_serializing_value(self) -> None:
        secret = "example-session-value"
        with patch.dict(os.environ, {"CIVITAI_SESSION_COOKIE": f"__Secure-civ-token={secret}"}, clear=False):
            cookie = MODULE.session_cookie_from_environment()
        self.assertIsNotNone(cookie)
        assert cookie is not None
        self.assertEqual(cookie["name"], "__Secure-civ-token")
        self.assertEqual(cookie["value"], secret)
        public_view = {"session_cookie_injected": True, "cookie_values_reported": False}
        self.assertNotIn(secret, json.dumps(public_view))

    def test_session_cookie_missing_is_a_supported_api_first_state(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(MODULE.session_cookie_from_environment())


if __name__ == "__main__":
    unittest.main()
