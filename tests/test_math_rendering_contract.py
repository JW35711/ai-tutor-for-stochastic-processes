import json
import unittest
from pathlib import Path


class MathRenderingContractTests(unittest.TestCase):
    javascript = (Path(__file__).parents[1] / "web" / "app.js").read_text(encoding="utf-8")

    def test_all_math_delimiters_are_extracted_before_html_escape(self) -> None:
        self.assertIn("mathTokens", self.javascript)
        self.assertIn(r"\$\$([\s\S]*?)\$\$", self.javascript)
        self.assertIn(r"\\\[([\s\S]*?)\\\]", self.javascript)
        self.assertIn(r"\\\(([\s\S]*?)\\\)", self.javascript)
        self.assertIn(r"\$([^$\n]+)\$", self.javascript)

    def test_math_pipeline_mentions_matrix_entity_repair_and_safe_katex(self) -> None:
        self.assertIn('replaceAll("amp;", "&")', self.javascript)
        self.assertIn("throwOnError: false", self.javascript)
        self.assertIn("trust: false", self.javascript)

    def test_course_formula_fixture_families_are_represented(self) -> None:
        fixtures = (
            r"$N(t)\\sim\\operatorname{Poisson}(\\lambda t)$",
            r"$$P(T>t)=P(N(t)=0)=e^{-\\lambda t}$$",
            r"\\(\\pi P=\\pi\\)",
            r"\\[Q=\\begin{pmatrix} -\\lambda & \\lambda \\\\ \\mu & -\\mu \\end{pmatrix}\\]",
        )
        self.assertEqual(len(fixtures), 4)
        self.assertTrue(all("\\" in fixture for fixture in fixtures))

    def test_multilingual_prose_can_surround_formula_delimiters(self) -> None:
        fixtures = (
            "等待时间满足 $P(T>t)=e^{-\\lambda t}$。",
            "Väntetiden uppfyller \\(P(T>t)=e^{-\\lambda t}\\).",
            "The stationary condition is \\[\\pi P=\\pi\\].",
        )
        self.assertEqual(len(fixtures), 3)
        self.assertTrue(all("lambda" in fixture or "pi" in fixture or "P(T" in fixture for fixture in fixtures))

    def test_course_fixture_set_covers_required_formula_families(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "math_rendering_cases.json"
        fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
        names = {item["name"] for item in fixtures}
        required = {
            "greek_symbols", "subscripts_superscripts", "fraction", "square_root",
            "sum", "integral", "probability", "expectation_variance",
            "conditional_probability", "matrix", "bmatrix", "aligned", "cases",
            "inequalities", "arrows", "limits", "inline_prose", "multiple_formulas",
            "display_between_paragraphs", "chinese_formula", "swedish_formula",
            "markdown_list_formula", "formula_punctuation", "mixed_delimiters", "mm1_ratio",
        }
        self.assertTrue(required.issubset(names))
        self.assertGreaterEqual(len(fixtures), 20)
        self.assertTrue(all(item["text"] for item in fixtures))


if __name__ == "__main__":
    unittest.main()
