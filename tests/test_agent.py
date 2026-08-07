import unittest

from src.agent import StochasticTutorAgent
from src.memory import LearnerMemory
from src.module_registry import module_catalog


class AgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = LearnerMemory(":memory:")
        self.agent = StochasticTutorAgent(memory=self.memory)

    def tearDown(self) -> None:
        self.memory.close()

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
        self.assertEqual(response["parameters"]["samples"], 2000)
        self.assertTrue(response["sources"])
        self.assertEqual(
            [item["node"] for item in response["trace"]],
            ["classify", "retrieve", "plan", "tool", "respond"],
        )

    def test_rejects_invalid_session_identifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "session_id"):
            self.agent.answer("模拟布朗运动", session_id=123)  # type: ignore[arg-type]

    def test_reads_number_before_path_unit(self) -> None:
        response = self.agent.answer("用300条路径模拟100步随机游走")
        self.assertEqual(response["parameters"]["paths"], 300)
        self.assertEqual(response["parameters"]["steps"], 100)

    def test_session_memory_counts_turns(self) -> None:
        first = self.agent.answer("模拟100步随机游走")
        second = self.agent.answer("再模拟200步随机游走", first["session_id"])
        self.assertEqual(second["memory"]["turns"], 2)
        self.assertEqual(second["memory"]["covered_modules"], ["module02"])
        self.assertEqual(second["memory"]["modules"][0]["attempts"], 2)

    def test_follow_up_inherits_module_tool_and_unchanged_parameters(self) -> None:
        first = self.agent.answer(
            "M/M/1 queue：到达率为0.75、服务率为1、时长为300、路径数为10"
        )
        second = self.agent.answer("再把到达率改成0.8", first["session_id"])
        self.assertEqual(second["module_id"], "module07")
        self.assertEqual(second["tool"], "simulate_mm1_queue")
        self.assertEqual(second["parameters"]["arrival_rate"], 0.8)
        self.assertEqual(second["parameters"]["service_rate"], 1.0)
        self.assertEqual(second["parameters"]["horizon"], 300.0)
        self.assertEqual(second["parameters"]["paths"], 10)
        self.assertTrue(second["context"]["module_inherited"])
        self.assertIn("horizon", second["context"]["parameters_inherited"])
        self.assertIn("inherited", second["trace"][2]["detail"])

    def test_follow_up_context_survives_new_agent_instance(self) -> None:
        first = self.agent.answer("泊松过程：强度为3、时长为4、路径数为20")
        restarted_agent = StochasticTutorAgent(memory=self.memory)
        second = restarted_agent.answer("路径数改成50", first["session_id"])
        self.assertEqual(second["module_id"], "module01")
        self.assertEqual(second["tool"], "simulate_poisson_process")
        self.assertEqual(second["parameters"]["rate"], 3.0)
        self.assertEqual(second["parameters"]["horizon"], 4.0)
        self.assertEqual(second["parameters"]["paths"], 50)

    def test_explicit_new_topic_does_not_inherit_previous_model(self) -> None:
        first = self.agent.answer("泊松过程：强度为3、时长为4")
        second = self.agent.answer("模拟布朗运动，T为2", first["session_id"])
        self.assertEqual(second["module_id"], "module04")
        self.assertEqual(second["tool"], "simulate_brownian_motion")
        self.assertFalse(second["context"]["module_inherited"])
        self.assertEqual(second["context"]["parameters_inherited"], [])

    def test_answer_exposes_diagnosis_and_adaptive_note(self) -> None:
        response = self.agent.answer("布朗运动的方差是根号T，对吗？")
        self.assertEqual(
            response["misconceptions"][0]["code"],
            "brownian_variance_sqrt_t",
        )
        self.assertIn("方差为 T", response["answer"])
        self.assertTrue(response["learning_note"])

    def test_all_modules_report_executable_tool_coverage(self) -> None:
        self.assertTrue(all(module["tool_ready"] for module in module_catalog()))

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

    def test_module01_selects_bernoulli_variant(self) -> None:
        response = self.agent.answer("伯努利过程：时间槽数为80、事件概率为0.25")
        self.assertEqual(response["module_id"], "module01")
        self.assertEqual(response["tool"], "simulate_bernoulli_process")
        self.assertEqual(response["parameters"]["probability"], 0.25)

    def test_module07_selects_reliability_buffer_and_queue_variants(self) -> None:
        cases = {
            "可靠性模型中的串联和并联系统": "analyze_reliability_system",
            "批量到达 buffer：到达概率为0.6": "simulate_batch_buffer",
            "M/M/1 queue：到达率为0.75、服务率为1": "simulate_mm1_queue",
        }
        for question, expected_tool in cases.items():
            with self.subTest(question=question):
                response = self.agent.answer(question)
                self.assertEqual(response["module_id"], "module07")
                self.assertEqual(response["tool"], expected_tool)

    def test_modules08_to10_execute_exploratory_tools(self) -> None:
        cases = {
            "非齐次泊松过程 thinning：基础强度为2": (
                "module08",
                "simulate_nhpp_thinning",
            ),
            "自避免游走：最大步数为1000、实验次数为100": (
                "module09",
                "simulate_self_avoiding_walk",
            ),
            "圆上粒子合并：圆周大小为12、粒子数为9、实验次数为100": (
                "module10",
                "simulate_coalescing_particles",
            ),
        }
        for question, (module_id, tool) in cases.items():
            with self.subTest(question=question):
                response = self.agent.answer(question)
                self.assertEqual(response["module_id"], module_id)
                self.assertEqual(response["tool"], tool)


if __name__ == "__main__":
    unittest.main()
