from .conftest import wait_for_app


def test_ui_and_query_language_can_differ(page):
    wait_for_app(page)
    page.locator("#languageSelect").select_option("sv")
    page.locator('[data-view="tutorView"]').first.click()
    page.locator("#questionInput").fill("Explain the Markov property")
    page.locator("#chatForm").evaluate("form => form.requestSubmit()")
    page.locator(".agent-message").last.wait_for(state="visible", timeout=60_000)
    assert page.locator("#questionInput").is_visible()
    page.locator("#languageSelect").select_option("zh")
    assert page.locator('[data-view="courseView"]').first.inner_text()
