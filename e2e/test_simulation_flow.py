from .conftest import open_view, wait_for_app


def test_simulation_catalogue_and_run(page):
    wait_for_app(page)
    open_view(page, "simulationLabView")
    page.locator("#simulationCatalogueGrid .experiment-card").first.wait_for()
    page.locator("#simulationSearch").fill("Poisson")
    page.locator("#simulationCatalogueGrid [data-open-experiment]").first.click()
    page.locator("#simulationDetail").wait_for(state="visible")
    assert page.locator("[data-run-experiment]").is_visible()
    page.locator("[data-run-experiment]").click()
    page.locator("#simulationView").wait_for(state="visible", timeout=60_000)
    assert page.locator("#simulationChart").bounding_box()["width"] > 100
    assert page.locator("#simulationLegend").inner_text()
    assert page.locator("#simulationMetrics").inner_text()
