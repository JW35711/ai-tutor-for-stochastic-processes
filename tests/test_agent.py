import unittest

from src.agent import StochasticTutorAgent


class AgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = StochasticTutorAgent()

    def test_routes_chinese_poisson_question(self) -> None:
        self.assertEqual(self.agent.classify_module("泊松过程的等待时间"), "module01")

    def test_routes_brownian_before_random_walk(self) -> None:
        self.assertEqual(
            self.agent.classify_module("随机游走如何逼近布朗运动"),
            "module04",
        )

    def test_routes_all_eleven_modules(self) -> None:
        cases = {
            "用蒙特卡洛方法模拟掷骰子": "module00",
            "解释伯努利过程的几何等待时间": "module01",
            "离散时间随机游走中的赌徒破产": "module02",
            "连续时间随机游走的泊松跳跃时刻": "module03",
            "布朗运动为什么具有高斯增量": "module04",
            "离散时间马尔可夫链的平稳分布": "module05",
            "连续时间马尔可夫链的生成矩阵和停留时间": "module06",
            "M/M/1 queue 的排队稳定性": "module07",
            "非齐次泊松过程的 thinning algorithm": "module08",
            "自避免游走为什么会被路径困住": "module09",
            "圆上的粒子合并时间": "module10",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(self.agent.classify_module(question), expected)

    def test_explicit_module_number_wins(self) -> None:
        self.assertEqual(
            self.agent.classify_module("Module 10 里的随机游走规则是什么"),
            "module10",
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
        self.assertEqual(second["memory"]["modules"], ["module02", "module02"])

    def test_pending_module_returns_source_without_wrong_tool(self) -> None:
        response = self.agent.answer("解释非齐次泊松过程的 thinning algorithm")
        self.assertEqual(response["module_id"], "module08")
        self.assertIsNone(response["tool"])
        self.assertEqual(response["result"]["status"], "tool_pending")
        self.assertTrue(response["sources"])

    def test_module03_executes_continuous_random_walk_tool(self) -> None:
        response = self.agent.answer(
            "连续时间随机游走：跳跃率为2、时长为3、向上概率为0.6、路径数为100"
        )
        self.assertEqual(response["module_id"], "module03")
        self.assertEqual(response["tool"], "simulate_continuous_random_walk")
        self.assertEqual(response["parameters"]["rate"], 2.0)
        self.assertEqual(response["parameters"]["horizon"], 3.0)
        self.assertEqual(response["parameters"]["probability_up"], 0.6)
        self.assertEqual(
            {source["module_id"] for source in response["sources"]},
            {"module03"},
        )

    def test_module06_executes_two_state_ctmc_tool(self) -> None:
        response = self.agent.answer(
            "连续时间马尔可夫链：故障率为0.25、修复率为0.15、时长为80"
        )
        self.assertEqual(response["module_id"], "module06")
        self.assertEqual(response["tool"], "simulate_two_state_ctmc")
        self.assertEqual(response["parameters"]["failure_rate"], 0.25)
        self.assertEqual(response["parameters"]["repair_rate"], 0.15)
        self.assertEqual(response["result"]["stationary_distribution"], [0.375, 0.625])

    def test_module06_selects_birth_death_variant(self) -> None:
        response = self.agent.answer(
            "模拟出生死亡过程：出生率为0.35、死亡率为0.3、容量为6、路径数为100"
        )
        self.assertEqual(response["module_id"], "module06")
        self.assertEqual(response["tool"], "simulate_birth_death_process")
        self.assertEqual(response["parameters"]["capacity"], 6)
        self.assertEqual(len(response["result"]["stationary_distribution"]), 7)


if __name__ == "__main__":
    unittest.main()
