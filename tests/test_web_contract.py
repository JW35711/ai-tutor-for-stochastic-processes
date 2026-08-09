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
        selectors = set(re.findall(r'querySelector\("#([^"]+)"\)', self.javascript))
        self.assertEqual(selectors - html_ids, set())

    def test_dashboard_exposes_key_agent_evidence(self) -> None:
        for label in (
            "MODULE COVERAGE",
            "RAG EVIDENCE",
            "LEARNER PROFILE",
            "RETRIEVED SOURCES",
            "STATE GRAPH TRACE",
            "WAITING",
        ):
            self.assertIn(label, self.html)
        self.assertIn('id="appVersion"', self.html)
        self.assertIn("health.version", self.javascript)
        self.assertIn("SAFETY ${safety?.passed", self.javascript)

    def test_dashboard_has_prompts_covering_all_modules(self) -> None:
        prompts = re.findall(r'data-question="([^"]+)"', self.html)
        self.assertGreaterEqual(len(prompts), 11)
        for concept in (
            "蒙特卡洛",
            "伯努利",
            "泊松",
            "随机游走",
            "布朗运动",
            "马尔可夫链",
            "连续时间马尔可夫链",
            "出生死亡",
            "可靠性",
            "M/M/1",
            "非齐次泊松",
            "自避免游走",
            "粒子合并",
        ):
            self.assertTrue(any(concept in prompt for prompt in prompts), concept)

    def test_static_assets_are_linked(self) -> None:
        self.assertIn('href="/styles.css"', self.html)
        self.assertIn('src="/app.js"', self.html)

    def test_dynamic_ui_does_not_require_inline_styles(self) -> None:
        self.assertNotIn('style="', self.javascript)
        self.assertIn("<progress", self.javascript)

    def test_retrieval_evidence_can_show_grounded_excerpt(self) -> None:
        self.assertIn("查看证据摘录", self.javascript)
        self.assertIn("source.content", self.javascript)
        self.assertIn("source.query_expansions", self.javascript)
        self.assertIn("title_sparse", self.javascript)

    def test_team_trace_and_review_interval_are_rendered(self) -> None:
        self.assertIn("payload.teaching_team", self.javascript)
        self.assertIn("item.role_name", self.javascript)
        self.assertIn("item.responsibility", self.javascript)
        self.assertIn("review_interval_days", self.javascript)
        self.assertIn("建议 ${recommendation.review_interval_days} 天后复习", self.javascript)

    def test_run_evidence_can_be_exported_after_execution(self) -> None:
        self.assertIn('id="exportRunButton"', self.html)
        self.assertIn("stochlab-${latestRunPayload.module_id}", self.javascript)
        self.assertIn("payload.run_sha256", self.javascript)

    def test_learner_can_export_a_separate_versioned_profile(self) -> None:
        self.assertIn('id="exportProfileButton"', self.html)
        self.assertIn("/export`", self.javascript)
        self.assertIn("stochlab-learning-profile", self.javascript)
        self.assertIn("safeSessionLabel", self.javascript)

    def test_failed_server_deletion_does_not_orphan_learner_data(self) -> None:
        fetch_helper = self.javascript.split(
            "async function fetchJson",
            maxsplit=1,
        )[1].split("function escapeHtml", maxsplit=1)[0]
        reset_handler = self.javascript.split(
            'resetButton.addEventListener("click"',
            maxsplit=1,
        )[1]
        self.assertIn("if (!response.ok)", fetch_helper)
        self.assertIn("await fetchJson", reset_handler)
        self.assertIn("catch (error)", reset_handler)
        self.assertIn("会话标识仍保留", reset_handler)
        self.assertLess(
            reset_handler.index("catch (error)"),
            reset_handler.index("sessionId = null"),
        )

    def test_dynamic_learning_regions_have_accessible_semantics(self) -> None:
        self.assertIn('role="log"', self.html)
        self.assertIn('id="healthStatus" class="health-pill" role="status"', self.html)
        self.assertIn('maxlength="4000"', self.html)
        self.assertIn('role="group" aria-labelledby="quizQuestion"', self.javascript)
        self.assertIn('aria-pressed="false"', self.javascript)
        self.assertIn("correct-answer", self.javascript)

    def test_writes_are_mutually_exclusive_and_requests_are_bounded(self) -> None:
        self.assertIn("let mutationInFlight = false", self.javascript)
        self.assertIn("if (!beginMutation", self.javascript)
        self.assertIn("new AbortController()", self.javascript)
        self.assertIn("controller.abort()", self.javascript)
        self.assertIn('response.headers.get("X-Request-ID")', self.javascript)
        self.assertIn('form.setAttribute("aria-busy"', self.javascript)

    def test_provider_fallback_is_visible_in_health_status(self) -> None:
        self.assertIn("embedding_circuit?.state", self.javascript)
        self.assertIn("provider_circuit?.state", self.javascript)
        self.assertIn("Agent online · fallback", self.javascript)


if __name__ == "__main__":
    unittest.main()
