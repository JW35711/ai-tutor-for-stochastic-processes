"""Real-browser fixtures for the student-facing StochLab release path."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Page, sync_playwright  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def e2e_server(tmp_path_factory: pytest.TempPathFactory) -> str:
    port = _free_port()
    runtime = tmp_path_factory.mktemp("stochlab-e2e")
    env = os.environ.copy()
    env.update(
        {
            "TUTOR_MEMORY_PATH": str(runtime / "learner.sqlite3"),
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            # The full browser suite intentionally exercises many endpoints;
            # keep its isolated server from sharing the production throttle.
            "API_RATE_LIMIT_PER_MINUTE": "1000",
            "PYTHONUNBUFFERED": "1",
        }
    )
    process = subprocess.Popen(
        [sys.executable, "server.py", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 45
    try:
        import urllib.request

        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise RuntimeError(f"isolated server exited early: {output[-4000:]}")
            try:
                with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("isolated server did not become healthy")
        yield base_url
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright_instance:
        browser_instance = playwright_instance.chromium.launch(headless=True)
        yield browser_instance
        browser_instance.close()


@pytest.fixture
def page(browser: Browser, e2e_server: str, request: pytest.FixtureRequest, tmp_path: Path) -> Page:
    context = browser.new_context(viewport={"width": 1440, "height": 900}, base_url=e2e_server)
    current_page = context.new_page()
    errors: list[dict[str, str]] = []

    def on_console(message: object) -> None:
        if getattr(message, "type", "") == "error":
            errors.append({"kind": "console", "text": getattr(message, "text", "")})

    def on_page_error(error: Exception) -> None:
        errors.append({"kind": "pageerror", "text": str(error)})

    def on_response(response: object) -> None:
        status = int(getattr(response, "status", 0))
        url = str(getattr(response, "url", ""))
        if status >= 500 and "127.0.0.1" in url:
            errors.append({"kind": "http", "text": f"{status} {url}"})

    current_page.on("console", on_console)
    current_page.on("pageerror", on_page_error)
    current_page.on("response", on_response)
    yield current_page
    if errors:
        target = ROOT / "artifacts" / "e2e_failures"
        target.mkdir(parents=True, exist_ok=True)
        safe_name = request.node.nodeid.replace("/", "_").replace("::", "_")
        current_page.screenshot(path=str(target / f"{safe_name}.png"), full_page=True)
        (target / f"{safe_name}.json").write_text(
            json.dumps({"url": current_page.url, "errors": errors}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        context.close()
        pytest.fail(f"browser errors: {errors}")
    context.close()


def wait_for_app(page: Page) -> None:
    page.goto("/")
    page.locator("#overviewView").wait_for(state="visible")
    page.locator("#courseView").wait_for(state="attached")
    page.wait_for_timeout(250)


def open_view(page: Page, view: str) -> None:
    page.locator(f'[data-view="{view}"]').first.click()
    page.locator(f"#{view}").wait_for(state="visible")
