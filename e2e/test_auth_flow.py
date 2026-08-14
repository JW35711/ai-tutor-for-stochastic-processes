import uuid

from .conftest import open_view, wait_for_app


def _register(page, username):
    page.locator("[data-auth-mode='register']").click()
    page.locator("#authForm input[name='username']").fill(username)
    page.locator("#authForm input[name='password']").fill("stochlab-pass-123")
    page.locator("#authForm").locator("button[type='submit']").click()
    page.locator(".auth-user").wait_for()


def test_register_logout_login_and_session_isolation(page, browser, e2e_server):
    wait_for_app(page)
    alpha = f"alpha_{uuid.uuid4().hex[:8]}"
    _register(page, alpha)
    page.locator("[data-view='courseView']").click()
    page.locator("[data-module-id='module05']").click()
    page.locator("[data-concept-id]").first.click()
    page.locator("[data-concept-action='practice']").click()
    page.locator(".practice-answer").fill("I do not know yet")
    page.locator("[data-practice-submit]").click()
    page.wait_for_timeout(500)
    page.locator("[data-auth-logout]").click()
    page.locator("[data-auth-mode='register']").click()
    beta = f"beta_{uuid.uuid4().hex[:8]}"
    page.locator("#authForm input[name='username']").fill(beta)
    page.locator("#authForm input[name='password']").fill("stochlab-pass-123")
    page.locator("#authForm").locator("button[type='submit']").click()
    page.locator(".auth-user").wait_for()
    beta_session = page.evaluate("() => fetch('/api/auth/me').then(response => response.json()).then(payload => payload.user.session_id)")
    open_view(page, "progressView")
    assert page.locator("#learnerProfile").inner_text() == "No learning record yet."
    page.locator("[data-auth-logout]").click()
    page.locator("[data-auth-mode='login']").click()
    page.locator("#authForm input[name='username']").fill(alpha)
    page.locator("#authForm input[name='password']").fill("stochlab-pass-123")
    page.locator("#authForm").locator("button[type='submit']").click()
    page.locator(".auth-user").wait_for()
    alpha_me = page.evaluate("() => fetch('/api/auth/me').then(response => response.json())")
    spoofed = page.evaluate("sessionId => fetch('/api/profile?session_id=' + encodeURIComponent(sessionId)).then(response => response.json())", beta_session)
    assert spoofed["profile"]["session_id"] == alpha_me["user"]["session_id"]
    open_view(page, "progressView")
    assert "No learning record yet." not in page.locator("#learnerProfile").inner_text()
