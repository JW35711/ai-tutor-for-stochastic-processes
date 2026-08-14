from .conftest import wait_for_app


def test_mobile_views_fit_without_horizontal_overflow(page):
    page.set_viewport_size({"width": 390, "height": 844})
    wait_for_app(page)
    for view in ("overviewView", "courseView", "tutorView", "simulationLabView", "progressView"):
        page.locator(f'[data-view="{view.replace("View", "")}View"]').first.click()
        page.locator(f"#{view}").wait_for(state="visible")
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 2")
