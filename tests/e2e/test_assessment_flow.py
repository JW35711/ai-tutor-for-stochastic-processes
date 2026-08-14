from .conftest import open_view, wait_for_app


def _open_practice(page):
    open_view(page, "courseView")
    page.locator('[data-module-id="module05"]').click()
    page.locator('[data-concept-id]').first.click()
    page.locator('[data-concept-action="practice"]').click()
    page.locator("#practicePanel").wait_for(state="visible")


def test_practice_feedback_hints_reference_and_retry(page):
    wait_for_app(page)
    _open_practice(page)
    panel = page.locator("#practicePanel")
    assert panel.locator(".practice-answer").is_visible()
    panel.locator("[data-practice-submit]").click()
    assert "practice-incomplete" in (panel.get_attribute("class") or "")
    panel.locator(".practice-answer").fill("not enough")
    panel.locator("[data-practice-submit]").click()
    page.wait_for_timeout(500)
    assert "practice-incorrect" in (panel.get_attribute("class") or "") or "practice-incomplete" in (panel.get_attribute("class") or "")
    page.locator("[data-practice-retry]").click()
    assert panel.locator(".practice-answer").input_value() == ""
    for _ in range(3):
        panel.locator("[data-practice-hint]").click()
        page.wait_for_timeout(300)
    assert panel.locator(".practice-hint").inner_text()
    panel.locator("[data-practice-reference]").click()
    assert panel.locator(".practice-reference").is_visible()


def test_quiz_wrong_and_correct_states(page):
    wait_for_app(page)
    open_view(page, "courseView")
    page.locator('[data-module-id="module05"]').click()
    page.locator('[data-concept-id]').first.click()
    page.locator('[data-concept-action="quiz"]').click()
    quiz = page.locator("#quizPanel")
    quiz.wait_for(state="visible")
    buttons = quiz.locator("[data-answer]")
    assert buttons.count() >= 2
    buttons.last.click()
    page.wait_for_timeout(500)
    assert quiz.locator(".incorrect-answer, .correct-answer").count() >= 1
    correct_index = int(quiz.locator(".correct-answer").get_attribute("data-answer"))
    quiz.locator("[data-quiz-next]").click()
    page.wait_for_timeout(100)
    quiz.locator(f"[data-answer='{correct_index}']").click()
    page.wait_for_timeout(500)
    assert quiz.locator(".correct-answer").count() >= 1
