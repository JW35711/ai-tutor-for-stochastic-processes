import unittest

from src.agent import StochasticTutorAgent


class AgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = StochasticTutorAgent()

    def test_routes_chinese_poisson_question(self) -> None:
        self.assertEqual(self.agent.classify_topic("泊松过程的等待时间"), "poisson")

    def test_routes_brownian_before_random_walk(self) -> None:
        self.assertEqual(
            self.agent.classify_topic("随机游走如何逼近布朗运动"),
            "brownian_motion",
        )

    def test_answer_contains_tool_source_and_trace(self) -> None:
        response = self.agent.answer("用2000个样本做蒙特卡洛实验估计π")
        self.assertEqual(response["tool"], "run_monte_carlo_pi")
        self.assertTrue(response["sources"])
        self.assertEqual(
            [item["node"] for item in response["trace"]],
            ["classify", "retrieve", "plan", "tool", "respond"],
        )

    def test_session_memory_counts_turns(self) -> None:
        first = self.agent.answer("模拟100步随机游走")
        second = self.agent.answer("再模拟200步随机游走", first["session_id"])
        self.assertEqual(second["memory"]["turns"], 2)


if __name__ == "__main__":
    unittest.main()
