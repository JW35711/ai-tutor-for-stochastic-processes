"""State handoff functions used by LangGraph agent nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..workflow import AgentState, NodeOutcome
from ..recommendation import recommend_next
from ..mastery import MasteryState, update_mastery

if TYPE_CHECKING:
    from ..agent import StochasticTutorAgent


def assess(agent: "StochasticTutorAgent", state: AgentState) -> NodeOutcome:
    """Assessment Agent evaluates and persists one validated attempt."""

    concept_id_hint = state.assessment_input.get("concept_id") or state.concept_id
    concept_profile = next(
        (item for item in state.profile.get("knowledge_points", []) if item.get("concept_id") == concept_id_hint),
        {},
    )
    result = agent.assessment_agent.evaluate(
        state.assessment_input,
        current_concept_id=state.concept_id,
        existing_mastery=float(concept_profile.get("mastery_score", 0.0)),
        attempt_count=int(concept_profile.get("attempt_count", 0) or 0),
    )
    state.assessment_result = result.to_dict()
    attempt = state.assessment_input
    agent.memory.record_assessment(
        session_id=state.session_id,
        question_id=str(attempt["question_id"]),
        module_id=str(attempt["module_id"]),
        answer_index=int(attempt.get("answer_index", 0)),
        correct=bool(attempt["correct"]),
        bank_sha256=attempt.get("bank_sha256"),
    )
    concept_id = result.concept_id
    if concept_id:
        prior = agent.memory.concept_mastery(state.session_id, concept_id)
        existing = MasteryState(**prior[0]) if prior else MasteryState(concept_id=concept_id)
        updated = update_mastery(
            existing,
            correctness=result.correctness,
            hints_used=result.hints_used,
            misconception=(
                {"type": result.misconception_type, "summary": result.misconception_summary}
                if result.misconception_type else None
            ),
        )
        agent.memory.update_concept_mastery(session_id=state.session_id, state=updated.to_dict())
        agent.memory.record_learning_event(
            session_id=state.session_id,
            event_type="QUIZ_RESULT" if attempt.get("event_type") != "PRACTICE_ANSWER" else "PRACTICE_ATTEMPT",
            concept_id=concept_id,
            question_id=attempt.get("question_id"),
            payload={"correctness": result.correctness, "hints_used": result.hints_used, "status": updated.status, "grading_method": result.grading_method},
        )
    state.profile = agent.memory.profile(state.session_id)
    state.assessment_result["mastery"] = updated.to_dict() if concept_id else {}
    return NodeOutcome(
        f"assessment={state.assessment_result['correctness']}; "
        f"needs_review={state.assessment_result['needs_review']}"
    )


def recommend(agent: "StochasticTutorAgent", state: AgentState) -> NodeOutcome:
    """Curriculum Agent selects a catalog-backed next learning action."""

    recent_mistakes = []
    if state.assessment_result.get("needs_review"):
        recent_mistakes.append(state.assessment_result)
    decision = agent.curriculum_agent.decide(
        current_module_id=state.module_id,
        current_concept_id=state.assessment_result.get("concept_id") or state.concept_id,
        requested_topic=state.topic,
        profile=state.profile,
        recent_mistakes=recent_mistakes,
        learning_mode="review" if recent_mistakes else ("practice" if state.intent == "practice" else state.intent),
    )
    state.curriculum_decision = decision.to_dict()
    state.teaching_mode = str(state.curriculum_decision.get("teaching_mode") or "FOUNDATION")
    target_id = state.curriculum_decision.get("target_concept")
    state.current_concept_mastery = next(
        (item for item in state.profile.get("knowledge_points", []) if item.get("concept_id") == target_id),
        {"concept_id": target_id, "status": "NOT_STARTED", "mastery_score": 0.0, "attempt_count": 0, "hint_count": 0},
    )
    target_point = agent.curriculum_agent.concepts.get(target_id or "", {})
    state.prerequisite_mastery = {
        prerequisite: agent.curriculum_agent._mastery(state.profile, prerequisite)
        for prerequisite in target_point.get("prerequisites", [])
    }
    from ..recommendation import recommend_next_knowledge_point
    state.recommendation = recommend_next_knowledge_point(
        agent.curriculum_agent, state.profile, state.response_language, decision=decision
    )
    return NodeOutcome(
        f"recommended_action={decision.recommended_action}; "
        f"target={decision.target_concept or 'none'}"
    )
