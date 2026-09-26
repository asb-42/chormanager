"""Shared fixtures for the Web-E2E tier (M0 Gerüst, aktiv ab M3/M4).

Contract for M3/M4: when the web app exists, replace the
``pytest.mark.skip`` markers in the spec files and implement these
fixtures for real:

* ``web_base_url`` — already functional (env ``WEB_BASE_URL``).
* ``seeded_formation`` — create project + event + singers +
  availability via the backend API and return their ids/URLs.
* ``web_page`` — a logged-in Playwright ``Page`` (requires
  ``playwright`` + browsers, installed in M3, NOT in M0).

Until then every spec in this directory is skipped with reason
"Web-App (M1-M3) ausstehend" and the suite stays green.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def web_base_url() -> str:
    """Base URL of the web app under test (M1+)."""
    return os.environ.get("WEB_BASE_URL", "http://localhost:8000")


@pytest.fixture
def seeded_formation(web_base_url):
    """Seed project/event/singers via backend API (implement in M3)."""
    pytest.skip("Web-App (M1-M3) ausstehend: kein Seed möglich")


@pytest.fixture
def web_page(seeded_formation):
    """Logged-in Playwright page (implement in M3: playwright install)."""
    pytest.skip("Web-App (M1-M3) ausstehend: kein Browser-Setup")
