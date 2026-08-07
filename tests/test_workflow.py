import unittest

from src.workflow import AgentState, NodeOutcome, StateGraph, WorkflowNode


class StateGraphTests(unittest.TestCase):
    def test_declared_nodes_mutate_one_shared_state_in_order(self) -> None:
        def first(state: AgentState) -> NodeOutcome:
            state.topic = "classified"
            return NodeOutcome("topic selected")

        def second(state: AgentState) -> NodeOutcome:
            state.answer = f"saw {state.topic}"
            return NodeOutcome("answer built")

        graph = StateGraph(
            [WorkflowNode("first", first), WorkflowNode("second", second)]
        )
        state = graph.invoke(AgentState(question="q", session_id="s"))
        self.assertEqual(state.answer, "saw classified")
        self.assertEqual(graph.node_names, ("first", "second"))
        self.assertEqual(
            [item["node"] for item in state.trace],
            ["first", "second"],
        )
        self.assertEqual(
            [item["detail"] for item in state.trace],
            ["topic selected", "answer built"],
        )
        self.assertTrue(all(item["status"] == "ok" for item in state.trace))
        self.assertTrue(all(item["duration_ms"] >= 0 for item in state.trace))

    def test_failed_node_is_recorded_before_error_is_raised(self) -> None:
        def fail(state: AgentState) -> NodeOutcome:
            raise ValueError("bad input")

        graph = StateGraph([WorkflowNode("guard", fail)])
        state = AgentState(question="q", session_id="s")
        with self.assertRaisesRegex(ValueError, "bad input"):
            graph.invoke(state)
        self.assertEqual(state.trace[0]["node"], "guard")
        self.assertEqual(state.trace[0]["status"], "error")
        self.assertIn("ValueError", state.trace[0]["detail"])

    def test_duplicate_node_names_are_rejected(self) -> None:
        handler = lambda state: NodeOutcome("ok")
        with self.assertRaisesRegex(ValueError, "unique"):
            StateGraph(
                [WorkflowNode("same", handler), WorkflowNode("same", handler)]
            )

    def test_empty_graph_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            StateGraph([])


if __name__ == "__main__":
    unittest.main()
