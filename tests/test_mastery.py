import tempfile
import unittest
from pathlib import Path

from src.mastery import MASTERED, NEEDS_REVIEW, MasteryState, update_mastery
from src.memory import LearnerMemory


class KnowledgePointMasteryTests(unittest.TestCase):
    def test_only_assessed_evidence_changes_one_concept(self) -> None:
        first = update_mastery(MasteryState("m05-markov-property"), correctness=True)
        self.assertEqual(first.mastery_score, 0.19)
        self.assertEqual(first.status, "LEARNING")

    def test_wrong_answer_records_review_state(self) -> None:
        result = update_mastery(MasteryState("m04-terminal-distribution"), correctness=False, misconception={"type": "variance"})
        self.assertEqual(result.status, NEEDS_REVIEW)
        self.assertEqual(result.recent_misconceptions[0]["type"], "variance")

    def test_hints_reduce_gain_and_repeated_success_can_master(self) -> None:
        state = MasteryState("m05-stationary-distribution")
        for _ in range(3):
            state = update_mastery(state, correctness=True, hints_used=0)
        self.assertEqual(state.status, MASTERED)
        hinted = update_mastery(MasteryState("m05-markov-property"), correctness=True, hints_used=2)
        self.assertEqual(hinted.mastery_score, 0.10)

    def test_mastery_and_learning_events_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            memory = LearnerMemory(path)
            state = update_mastery(MasteryState("m01-poisson-process"), correctness=True)
            memory.update_concept_mastery(session_id="learner", state=state.to_dict())
            memory.record_learning_event(session_id="learner", event_type="PRACTICE_ANSWER", concept_id=state.concept_id)
            memory.close()
            reopened = LearnerMemory(path)
            self.assertEqual(reopened.concept_mastery("learner")[0]["concept_id"], "m01-poisson-process")
            self.assertEqual(reopened.learning_events("learner")[0]["event_type"], "PRACTICE_ANSWER")
            reopened.close()


if __name__ == "__main__":
    unittest.main()
