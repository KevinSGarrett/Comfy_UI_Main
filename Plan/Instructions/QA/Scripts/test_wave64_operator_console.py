from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
APP = ROOT / "Plan/07_IMPLEMENTATION/operator_console"
ROUTES = {"Home", "Projects", "Character Library", "Scene Builder", "Shot Timeline", "Pose & Masks", "Image Workspace", "Video Workspace", "Audio Workspace", "AV Workspace", "Runs", "QA & Compare", "Models & Capabilities", "Runtime & Workers", "Assets", "Settings & Admin"}


@pytest.fixture()
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((APP / "index.html").as_uri())
        yield page
        browser.close()


def test_exact_domain_navigation_and_hidden_internals(page):
    assert set(page.locator("nav button").all_text_contents()) == ROUTES
    text = page.locator("body").inner_text().lower()
    for forbidden in ("credential", "fencing token", "raw node", "absolute path"):
        assert forbidden not in text


def test_operator_modes_and_live_projection(page):
    assert page.locator("#modeControl button").count() == 4
    assert page.locator("#dagList li").count() == 5
    assert "body mask certificate missing" in page.locator(".issues").inner_text().lower()


def test_builder_validates_and_previews_expected_dag(page):
    page.get_by_role("button", name="New job").click()
    page.get_by_role("button", name="Preview DAG").click()
    assert "Character package is required" in page.locator("#formError").inner_text()
    page.locator("#character").select_option("c01-r014")
    page.locator("#scene").select_option("scene04-r009")
    page.locator("#media").select_option("av")
    page.get_by_role("button", name="Preview DAG").click()
    assert page.locator("#dagPreview li").count() == 6
    assert "Plan audio and sync" in page.locator("#dagPreview").inner_text()


def test_submission_never_claims_execution(page):
    page.get_by_role("button", name="New job").click()
    page.locator("#character").select_option("c01-r014")
    page.locator("#scene").select_option("scene04-r009")
    page.get_by_role("button", name="Queue controller request").click()
    assert "Submission is unavailable" in page.locator("#stateBanner").inner_text()


def test_cancel_and_reconnect_are_explicit_states(page):
    page.get_by_role("button", name="Cancel attempt").click()
    assert page.get_by_role("button", name="Cancelling").is_disabled()
    assert "command recorded" in page.locator("#stateBanner").inner_text()
    page.get_by_role("button", name="Reconnect").click()
    assert page.locator("#connectionLabel").inner_text() == "Reconciling"


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
def test_no_horizontal_page_overflow(page, width, height):
    page.set_viewport_size({"width": width, "height": height})
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
