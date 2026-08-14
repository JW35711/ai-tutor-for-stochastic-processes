from .conftest import open_view, wait_for_app


def test_course_navigation_and_stable_concepts(page):
    wait_for_app(page)
    open_view(page, "courseView")
    page.locator('[data-module-id="module00"]').click()
    page.locator('[data-concept-id]').first.wait_for()
    first = page.locator('[data-concept-id]').first.get_attribute("data-concept-id")
    assert first
    page.locator('[data-module-id="module05"]').click()
    assert page.locator('[data-concept-id]').count() >= 3
    page.locator('[data-module-id="module10"]').click()
    assert page.locator('[data-concept-id]').count() >= 3
    page.go_back()
    page.go_forward()
    assert page.locator('[data-module-id="module10"]').get_attribute("aria-selected") == "true"
