from .conftest import open_view, wait_for_app


def _ask(page, question):
    open_view(page, "tutorView")
    before = page.locator(".message").count()
    page.locator("#questionInput").fill(question)
    page.locator("#chatForm").evaluate("form => form.requestSubmit()")
    page.wait_for_function("count => document.querySelectorAll('.message').length > count + 1", arg=before, timeout=60_000)


def test_poisson_multi_turn_context_and_follow_up(page):
    wait_for_app(page)
    for question in (
        "What is a Poisson process?",
        "Why are the waiting times exponential?",
        "Show me.",
        "Set lambda to 4.",
        "What changed?",
    ):
        _ask(page, question)
    messages = page.locator(".message").all_inner_texts()
    assert any("Poisson" in message for message in messages)
    assert all(any(question in message for message in messages) for question in ("What is a Poisson process?", "Why are the waiting times exponential?", "Show me.", "Set lambda to 4.", "What changed?"))
    assert page.locator("#questionInput").is_editable()
    assert page.locator(".simulation-message-card").count() >= 1


def test_tutor_math_dom_is_katex_and_currency_is_plain_text(page):
    wait_for_app(page)
    open_view(page, "tutorView")
    formula_text = r"Inline $E[X]$ and $$P(T>t)=e^{-\lambda t}$$ \(\pi P=\pi\) \[Q=\begin{pmatrix}1 & 0\\0 & 1\end{pmatrix}\] Price $5"
    page.evaluate("text => window.addMessage('agent', text)", formula_text)
    page.wait_for_timeout(150)
    assert page.locator("#conversation .katex").count() >= 4
    text = page.locator("#conversation").inner_text()
    assert "amp;" not in text
    assert "$5" in text


def test_conversational_follow_up_and_social_turns_stay_in_scope(page):
    wait_for_app(page)
    _ask(page, "What is Brownian motion?")
    _ask(page, "Are you sure?")
    contextual = page.locator(".agent-message").last.inner_text()
    assert "outside the scope" not in contextual.lower()
    assert "Brownian" in contextual or "previous explanation" in contextual

    _ask(page, "OK you are smart")
    social = page.locator(".agent-message").last.inner_text()
    assert "outside the scope" not in social.lower()
    assert "continue" in social.lower()


def test_multilingual_social_and_general_turns(page):
    wait_for_app(page)
    _ask(page, "谢谢")
    assert "不客气" in page.locator(".agent-message").last.inner_text()
    _ask(page, "Tack")
    assert "Varsågod" in page.locator(".agent-message").last.inner_text()
    _ask(page, "What is Python?")
    answer = page.locator(".agent-message").last.inner_text()
    assert "Python" in answer
    assert "outside the scope" not in answer.lower()
