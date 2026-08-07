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

    def test_run_evidence_can_be_exported_after_execution(self) -> None:
        self.assertIn('id="exportRunButton"', self.html)
        self.assertIn("stochlab-${latestRunPayload.module_id}", self.javascript)


if __name__ == "__main__":
    unittest.main()
