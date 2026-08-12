import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class WebContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text("utf-8")
        cls.javascript = (ROOT / "web" / "app.js").read_text("utf-8")

    def test_every_id_selector_used_by_javascript_exists(self) -> None:
        html_ids = set(re.findall(r'id="([^"]+)"', self.html))
        selectors = set(re.findall(r'querySelector\("#([^\"]+)"\)', self.javascript))
        self.assertEqual(selectors - html_ids, set())

    def test_student_page_is_english_and_uses_current_title(self) -> None:
        self.assertIn('<html lang="en">', self.html)
        self.assertIn("<title>Introduction to Stochastic Processes with Applications</title>", self.html)
        self.assertIn("Learn concepts, practice problems", self.html)
        for old_label in ("MODULE COVERAGE", "RAG EVIDENCE", "STATE GRAPH TRACE", "Export Profile"):
            self.assertNotIn(old_label, self.html + self.javascript)
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", self.html + self.javascript))

    def test_curriculum_is_loaded_from_the_backend(self) -> None:
        self.assertIn('fetchJson("/api/curriculum"', self.javascript)
        self.assertIn("activeModuleId", self.javascript)
        self.assertIn("currentConceptId", self.javascript)
        self.assertIn("stochasticTutorCurrentModule", self.javascript)
        self.assertIn("stochasticTutorCurrentConcept", self.javascript)
        self.assertNotIn('data-question="', self.html)

    def test_module_tabs_show_numbers_only(self) -> None:
        self.assertIn('aria-label="Module ${moduleNumber(item)}"', self.javascript)
        self.assertNotIn('module-tab-title">${escapeHtml(item.label)}', self.javascript)

    def test_static_assets_and_math_renderer_are_linked(self) -> None:
        self.assertIn('href="/styles.css"', self.html)
        self.assertIn('src="/app.js"', self.html)
        self.assertIn("katex", self.html.lower())
        self.assertIn("renderTutorMarkdown", self.javascript)
        self.assertIn("throwOnError: false", self.javascript)
        self.assertIn("trust: false", self.javascript)

    def test_latex_matrix_ampersands_are_preserved(self) -> None:
        self.assertIn("Extract LaTeX before HTML escaping", self.javascript)
        self.assertIn('.replaceAll("&amp;", "&")', self.javascript)
        self.assertIn("safeMath", self.javascript)

    def test_simulation_has_a_dedicated_full_width_view_and_legend(self) -> None:
        for element_id in (
            "simulationView",
            "simulationChart",
            "simulationLegend",
            "simulationMetrics",
            "simulationSources",
            "closeSimulationView",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
            self.assertIn(f'querySelector("#{element_id}")', self.javascript)
        self.assertIn("showSimulationView(payload)", self.javascript)
        self.assertIn("renderLegend(series, simulationLegend)", self.javascript)
        self.assertIn(".simulation-active", (ROOT / "web" / "styles.css").read_text("utf-8"))

    def test_dynamic_learning_regions_have_accessible_semantics(self) -> None:
        self.assertIn('role="log"', self.html)
        self.assertIn('id="healthStatus" class="health-pill" role="status"', self.html)
        self.assertIn('maxlength="4000"', self.html)
        self.assertIn('id="composerStatus"', self.html)
        self.assertIn('role="group" aria-labelledby="quizQuestion"', self.javascript)
        self.assertIn('aria-current="${point.id === concept.id ? "true" : "false"}"', self.javascript)
        self.assertIn('aria-controls="curriculumContent"', self.javascript)

    def test_requests_are_bounded_and_reset_is_safe(self) -> None:
        self.assertIn("let mutationInFlight = false", self.javascript)
        self.assertIn("new AbortController()", self.javascript)
        self.assertIn("controller.abort()", self.javascript)
        self.assertIn("submitButton.disabled = loading", self.javascript)
        self.assertIn("if (!response.ok)", self.javascript)

    def test_composer_supports_keyboard_submit_and_composition(self) -> None:
        self.assertIn("event.key !== \"Enter\"", self.javascript)
        self.assertIn("event.shiftKey", self.javascript)
        self.assertIn("event.isComposing", self.javascript)
        self.assertIn("compositionstart", self.javascript)
        self.assertIn("form.requestSubmit()", self.javascript)
        self.assertIn("autoGrowInput", self.javascript)
        self.assertIn("input.focus()", self.javascript)

    def test_student_ui_does_not_render_raw_retrieval_internals(self) -> None:
        self.assertNotIn("retrievedSources", self.javascript)
        self.assertNotIn("source.content", self.javascript)

    def test_debug_mode_exposes_routing_and_grounding_metadata(self) -> None:
        for field in (
            "module_id",
            "concept_id",
            "related_module_ids",
            "related_concept_ids",
            "tool_called",
            "llm_enabled",
            "llm_applied",
            "workflow",
            "trace",
            "sources",
        ):
            self.assertIn(f"{field}:", self.javascript)
        self.assertIn('get("debug") === "1"', self.javascript)


if __name__ == "__main__":
    unittest.main()
