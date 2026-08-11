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
        self.assertIn("<title>Stochastic Processes</title>", self.html)
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

    def test_static_assets_and_math_renderer_are_linked(self) -> None:
        self.assertIn('href="/styles.css"', self.html)
        self.assertIn('src="/app.js"', self.html)
        self.assertIn("katex", self.html.lower())
        self.assertIn("renderTutorMarkdown", self.javascript)
        self.assertIn("throwOnError: false", self.javascript)
        self.assertIn("trust: false", self.javascript)

    def test_dynamic_learning_regions_have_accessible_semantics(self) -> None:
        self.assertIn('role="log"', self.html)
        self.assertIn('id="healthStatus" class="health-pill" role="status"', self.html)
        self.assertIn('maxlength="4000"', self.html)
        self.assertIn('role="group" aria-labelledby="quizQuestion"', self.javascript)
        self.assertIn('aria-pressed="${point.id === concept.id}"', self.javascript)

    def test_requests_are_bounded_and_reset_is_safe(self) -> None:
        self.assertIn("let mutationInFlight = false", self.javascript)
        self.assertIn("new AbortController()", self.javascript)
        self.assertIn("controller.abort()", self.javascript)
        self.assertIn("submitButton.disabled = true", self.javascript)
        self.assertIn("if (!response.ok)", self.javascript)

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
