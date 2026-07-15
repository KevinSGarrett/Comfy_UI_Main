#!/usr/bin/env python3
"""Download an exact resolved asset in hidden Chromium and verify its source hash."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
MANAGER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py"
DEFAULT_CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
DEFAULT_SOURCE_USER_DATA = Path.home() / "AppData/Local/Google/Chrome/User Data"
DEFAULT_HEADLESS_PROFILE = Path.home() / "AppData/Local/ComfyUIMain/CivitaiHeadlessProfile"
DEFAULT_SESSION_COOKIE_ENV = "CIVITAI_SESSION_COOKIE"
PROFILE_FILES = ("Preferences", "Secure Preferences")
PROFILE_DIRECTORIES = ("Local Storage", "Session Storage", "IndexedDB", "WebStorage")


class BackgroundBrowserError(RuntimeError):
    def __init__(self, classification: str, message: str) -> None:
        super().__init__(message)
        self.classification = classification


def load_manager(project_root: Path):
    path = project_root / MANAGER_PATH.relative_to(ROOT)
    spec = importlib.util.spec_from_file_location("model_asset_acquisition", path)
    if spec is None or spec.loader is None:
        raise BackgroundBrowserError("ACQUISITION_MANAGER_LOAD_FAILED", f"Cannot load acquisition manager: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    try:
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
    finally:
        source_connection.close()


def remove_profile_subtree(path: Path, profile_root: Path) -> None:
    resolved = path.resolve()
    root = profile_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise BackgroundBrowserError("UNSAFE_PROFILE_REFRESH_PATH", f"Profile refresh path escapes dedicated root: {resolved}") from exc
    if resolved == root:
        raise BackgroundBrowserError("UNSAFE_PROFILE_REFRESH_PATH", "Refusing to recursively remove the dedicated profile root")
    shutil.rmtree(resolved)


def seed_browser_profile(source_root: Path, source_profile: str, target_root: Path) -> dict[str, Any]:
    source = source_root / source_profile
    if not source.is_dir() or not (source_root / "Local State").is_file():
        raise BackgroundBrowserError("SOURCE_BROWSER_PROFILE_MISSING", f"Chrome profile not found: {source}")
    target = target_root / "Default"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / "Local State", target_root / "Local State")
    for name in PROFILE_FILES:
        candidate = source / name
        if candidate.is_file():
            shutil.copy2(candidate, target / name)
    for name in PROFILE_DIRECTORIES:
        candidate = source / name
        destination = target / name
        if not candidate.is_dir():
            continue
        if destination.exists():
            remove_profile_subtree(destination, target_root)
        shutil.copytree(
            candidate,
            destination,
            ignore=shutil.ignore_patterns("Cache", "Code Cache", "GPUCache", "CacheStorage", "*.tmp"),
        )
    source_cookies = source / "Network/Cookies"
    if not source_cookies.is_file():
        raise BackgroundBrowserError("SOURCE_BROWSER_COOKIES_MISSING", "Chrome Cookies database is missing")
    sqlite_backup(source_cookies, target / "Network/Cookies")
    marker = {
        "schema_version": "1.0",
        "source_browser": "Google Chrome",
        "source_profile": source_profile,
        "cookie_values_serialized": False,
        "profile_stored_outside_project": True,
    }
    (target_root / "COMFY_UI_MAIN_HEADLESS_PROFILE.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    return marker


def initialize_browser_profile(target_root: Path, refresh: bool = False) -> dict[str, Any]:
    target_root.mkdir(parents=True, exist_ok=True)
    default_profile = target_root / "Default"
    if refresh and default_profile.exists():
        remove_profile_subtree(default_profile, target_root)
    default_profile.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema_version": "1.1",
        "browser": "Google Chrome",
        "profile_kind": "dedicated_persistent_headless",
        "cookie_values_serialized": False,
        "profile_stored_outside_project": True,
        "source_profile_copied": False,
    }
    (target_root / "COMFY_UI_MAIN_HEADLESS_PROFILE.json").write_text(
        json.dumps(marker, indent=2) + "\n", encoding="utf-8"
    )
    return marker


def session_cookie_from_environment(variable_name: str = DEFAULT_SESSION_COOKIE_ENV) -> dict[str, Any] | None:
    raw = os.environ.get(variable_name, "").strip()
    if not raw:
        return None
    candidates: list[tuple[str, str]] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            name, value = part.split("=", 1)
            candidates.append((name.strip(), value.strip()))
        else:
            candidates.append(("__Secure-civ-token", part))
    preferred = ("__Secure-civ-token", "__Secure-civitai-token")
    selected = next((item for name in preferred for item in candidates if item[0] == name), None)
    if selected is None and len(candidates) == 1:
        selected = candidates[0]
    if selected is None or not selected[0] or not selected[1]:
        raise BackgroundBrowserError(
            "BACKGROUND_BROWSER_SESSION_COOKIE_INVALID",
            f"{variable_name} must contain one Civitai session cookie name/value pair",
        )
    return {
        "name": selected[0],
        "value": selected[1],
        "domain": ".civitai.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "Lax",
    }


def download_headless(
    manager,
    manifest: dict[str, Any],
    chrome_path: Path,
    profile_root: Path,
    output_dir: Path,
    timeout_seconds: int,
    session_cookie: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any]]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BackgroundBrowserError("PLAYWRIGHT_RUNTIME_MISSING", "Python Playwright is not installed") from exc

    if not chrome_path.is_file():
        raise BackgroundBrowserError("CHROMIUM_EXECUTABLE_MISSING", f"Chrome executable not found: {chrome_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = str(manifest["install"]["local_filename"])
    destination = output_dir / filename
    download_url = str(manifest["source_metadata"]["download_url"])
    cookie_count = 0
    suggested_filename = ""
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_root),
            executable_path=str(chrome_path),
            headless=True,
            accept_downloads=True,
            downloads_path=str(output_dir),
            args=[
                "--profile-directory=Default",
                "--headless=new",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-sync",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-position=-32000,-32000",
            ],
        )
        try:
            if session_cookie:
                context.add_cookies([session_cookie])
            cookie_count = len(context.cookies(["https://civitai.com"]))
            page = context.pages[0] if context.pages else context.new_page()
            try:
                with page.expect_download(timeout=timeout_seconds * 1000) as download_info:
                    try:
                        page.goto(download_url, wait_until="commit", timeout=timeout_seconds * 1000)
                    except PlaywrightError:
                        pass
                download = download_info.value
            except PlaywrightTimeoutError as exc:
                body = ""
                try:
                    body = page.locator("body").inner_text(timeout=2000)[:500]
                except PlaywrightError:
                    pass
                lowered = body.lower()
                auth_markers = (
                    "unauthorized",
                    "logged in",
                    "log in",
                    "verify to continue",
                    "quick check",
                    "couldn't verify you automatically",
                )
                classification = (
                    "BACKGROUND_BROWSER_SESSION_REAUTH_REQUIRED"
                    if any(marker in lowered for marker in auth_markers)
                    else "BACKGROUND_BROWSER_DOWNLOAD_TIMEOUT"
                )
                raise BackgroundBrowserError(classification, f"Headless browser did not emit a download: {body}") from exc
            suggested_filename = download.suggested_filename
            download.save_as(str(destination))
        finally:
            context.close()
    proof = manager.verify_candidate(manifest, destination)
    return destination, {
        "headless": True,
        "visible_window_created": False,
        "browser": "Google Chrome",
        "browser_profile_path": str(profile_root),
        "civitai_cookie_count": cookie_count,
        "session_cookie_injected": bool(session_cookie),
        "cookie_values_reported": False,
        "suggested_filename": suggested_filename,
        "sha256": proof["sha256"],
        "bytes": proof["bytes"],
    }


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chrome-path", type=Path, default=DEFAULT_CHROME)
    parser.add_argument("--source-user-data", type=Path, default=DEFAULT_SOURCE_USER_DATA)
    parser.add_argument("--source-profile", default="Default")
    parser.add_argument("--headless-profile", type=Path, default=DEFAULT_HEADLESS_PROFILE)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--refresh-profile", action="store_true")
    parser.add_argument("--session-cookie-env", default=DEFAULT_SESSION_COOKIE_ENV)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--wire", action="store_true")
    parser.add_argument("--object-info-url", default="http://127.0.0.1:8188/object_info")
    args = parser.parse_args()
    root = args.project_root.resolve()
    manager = load_manager(root)
    manager.load_env(root)
    manifest_path = manager.project_path(root, args.manifest)
    output_dir = args.output_dir or (root / "runtime_artifacts/model_acquisition/browser_inbox")
    output_dir = manager.project_path(root, output_dir)
    profile_root = args.headless_profile.resolve()
    try:
        marker = profile_root / "COMFY_UI_MAIN_HEADLESS_PROFILE.json"
        if args.refresh_profile or not marker.is_file():
            seed = initialize_browser_profile(profile_root, refresh=args.refresh_profile)
        else:
            seed = json.loads(marker.read_text(encoding="utf-8"))
        session_cookie = session_cookie_from_environment(args.session_cookie_env)
        manifest = manager.load_json(manifest_path)
        path, browser = download_headless(
            manager,
            manifest,
            args.chrome_path.resolve(),
            profile_root,
            output_dir,
            args.timeout_seconds,
            session_cookie,
        )
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "classification": "BACKGROUND_BROWSER_DOWNLOAD_HASH_VERIFIED",
            "request_id": manifest["request"]["request_id"],
            "downloaded_path": manager.relative_or_absolute(root, path),
            "browser": browser,
            "profile_seed": seed,
            "installed": False,
            "registered": False,
            "content_based_suppression": False,
            "secret_values_reported": False,
        }
        if args.install:
            manifest["acquisition_method"] = "background_headless_browser_authenticated_profile"
            installed = manager.finalize(root, manifest, path, args.wire, args.object_info_url)
            result["classification"] = "BACKGROUND_BROWSER_DOWNLOAD_INSTALLED_REGISTERED_AND_QUEUED"
            result["installed"] = True
            result["registered"] = True
            result["installation"] = installed
        print(json.dumps(result, indent=2))
        return 0
    except (BackgroundBrowserError, manager.AcquisitionError) as exc:
        classification = getattr(exc, "classification", "BACKGROUND_BROWSER_DOWNLOAD_FAILED")
        print(json.dumps({"classification": classification, "error": manager.redact(str(exc)), "secret_values_reported": False}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
