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
            state.trace,
            [
                {"node": "first", "detail": "topic selected"},
                {"node": "second", "detail": "answer built"},
            ],
        )

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
