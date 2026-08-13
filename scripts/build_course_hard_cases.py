#!/usr/bin/env python3
"""Build the checked-in natural-question credibility set from verified cases.

The source locators and evidence phrases are copied from the existing reviewed
120-case set; only the student wording is varied here.  This keeps the hard
set grounded in the same corpus instead of inventing new claims.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evals" / "course_coverage_cases.json"
OUTPUT = ROOT / "evals" / "course_hard_cases.json"

ALIASES = {
    "m00-monte-carlo-estimation": "repeated random sampling to estimate a quantity",
    "m00-sample-mean": "the average computed from repeated trials",
    "m00-law-large-numbers": "why averages settle as the sample grows",
    "m00-standard-error": "the uncertainty of a Monte Carlo estimate",
    "m01-bernoulli-process": "independent yes-or-no trials over discrete slots",
    "m01-binomial-counts": "the number of successes in fixed Bernoulli slots",
    "m01-geometric-waiting-time": "the number of trials before the first success",
    "m01-poisson-process": "counts of arrivals with a constant rate in continuous time",
    "m02-random-walk-increments": "a path built by adding random up and down steps",
    "m02-drift-variance": "how step bias controls the mean and spread of a walk",
    "m02-hitting-probability": "the chance of reaching one boundary before another",
    "m02-absorption-time": "the number of steps until a boundary is reached",
    "m03-poisson-jump-times": "the random clock that triggers jumps in continuous time",
    "m03-continuous-time-path": "a path that stays constant between random jumps",
    "m03-rate-effects": "how changing the jump rate changes motion over a fixed horizon",
    "m04-brownian-increments": "independent Gaussian changes over disjoint time intervals",
    "m04-brownian-scaling": "the scaling that makes a random walk look Brownian",
    "m04-terminal-distribution": "the distribution of the process at a fixed time T",
    "m04-hitting-events": "whether a Brownian path reaches a specified level",
    "m05-transition-matrix": "the one-step probabilities between states",
    "m05-markov-property": "why the present state is enough for the next-step law",
    "m05-stationary-distribution": "a probability vector satisfying the invariant relation",
    "m05-absorption-and-ruin": "what happens when a chain reaches an absorbing boundary",
    "m06-holding-times": "the time a continuous-time chain waits in one state",
    "m06-generator-matrix": "the matrix of instantaneous transition rates",
    "m06-birth-death-process": "neighbouring upward and downward state changes",
    "m06-two-state-reliability": "failure and repair represented by two states",
    "m07-survival-and-hazard": "lifetime survival and instantaneous failure risk",
    "m07-series-parallel-systems": "how series and parallel arrangements change reliability",
    "m07-batch-buffer": "arrivals and service in a finite-capacity buffer",
    "m07-mm1-queue": "a single-server queue with Poisson arrivals and exponential service",
    "m08-time-varying-intensity": "an arrival rate that changes with time",
    "m08-thinning": "accepting candidate arrivals according to a changing intensity",
    "m08-integrated-intensity": "why integrating the rate gives the expected count",
    "m09-self-avoidance": "a walk that is not allowed to revisit a site",
    "m09-path-trapping": "how a growing path can run out of legal moves",
    "m09-stopping-length": "the distribution of the length at which paths stop",
    "m10-particle-motion": "random particles moving on a discrete circle",
    "m10-coalescence": "particles merging when they occupy the same location",
    "m10-coalescence-time": "the time until all moving particles form one cluster",
}

SWEDISH = {
    "m04-brownian-increments": "Vad betyder oberoende Gaussiska inkrement för Brownsk rörelse?",
    "m05-markov-property": "Varför räcker det aktuella tillståndet för Markovegenskapen?",
    "m05-stationary-distribution": "Vad betyder pi P = pi för en stationär fördelning?",
    "m08-thinning": "Hur fungerar tunningsalgoritmen för en tidsvarierande intensitet?",
}
CHINESE = {
    "m01-poisson-process": "为什么恒定速率的到达计数构成泊松过程？",
    "m04-brownian-scaling": "随机游走如何通过缩放逼近布朗运动？",
    "m05-stationary-distribution": "为什么平稳分布满足 πP=π？",
    "m09-self-avoidance": "自避免游走为什么不能只看当前位置？",
}


def main() -> None:
    source_cases = json.loads(SOURCE.read_text("utf-8"))
    curriculum = json.loads((ROOT / "data" / "curriculum.json").read_text("utf-8"))
    titles = {
        point["id"]: str(point["title"])
        for module in curriculum["modules"]
        for point in module["knowledge_points"]
    }
    by_concept: dict[str, dict] = {}
    for case in source_cases:
        by_concept.setdefault(str(case["concept_id"]), case)
    cases: list[dict] = []
    for concept_id, base in by_concept.items():
        anchor = ALIASES.get(concept_id, str(concept_id).replace("m", "").replace("-", " "))
        title = titles.get(concept_id, concept_id)
        # Use the reviewed curriculum title in two natural questions.  The
        # third variant is intentionally paraphrased to expose routing gaps.
        variants = [
            (f"I keep seeing {title} in the notebook. What does it mean in this stochastic-process model?", "definition", "en"),
            (f"Why does {title} behave that way, and what should I look for in a sample path?", "why", "en"),
            (f"Can you give a compact worked interpretation of {anchor}, including the main quantity I should compare with theory?", "example", "en"),
        ]
        if concept_id in SWEDISH:
            variants[1] = (SWEDISH[concept_id], "why", "sv")
        if concept_id in CHINESE:
            variants[2] = (CHINESE[concept_id], "why", "zh")
        for index, (question, question_type, language) in enumerate(variants, start=1):
            cases.append(
                {
                    "case_id": f"hard-{concept_id}-{index}",
                    "module_id": base["module_id"],
                    "concept_id": concept_id,
                    "question": question,
                    "language": language,
                    "question_type": question_type,
                    "expected_status": "SUPPORTED",
                    "answerable": True,
                    "gold_source_locators": base.get("gold_source_locators", []),
                    "acceptable_source_locators": base.get("acceptable_source_locators", []),
                    "gold_evidence_phrases": [str(item) for item in base.get("gold_evidence_phrases", [])[:2]],
                    "required_claims": base.get("required_claims", []),
                }
            )

    # Bad paths are part of the benchmark, not hidden hand-picked examples.
    partial = by_concept["m02-absorption-time"]
    cases.extend(
        [
            {
                "case_id": "hard-comparison-random-walk-self-avoiding",
                "module_id": "module02",
                "concept_id": "m02-random-walk-increments",
                "related_module_ids": ["module09"],
                "related_concept_ids": ["m09-self-avoidance"],
                "question": "Compare an ordinary random walk with a self-avoiding walk: what changes in the state information and the possible next step?",
                "language": "en",
                "question_type": "comparison",
                "expected_status": "SUPPORTED",
                "answerable": True,
                "gold_source_locators": by_concept["m02-random-walk-increments"].get("gold_source_locators", []) + by_concept["m09-self-avoidance"].get("gold_source_locators", []),
                "gold_evidence_phrases": ["random walk", "self-avoiding"],
                "required_claims": [],
            },
            {
                "case_id": "hard-notation-stationary-distribution",
                "module_id": "module05",
                "concept_id": "m05-stationary-distribution",
                "question": "What does the equation πP = π mean, and why does it not mean that the Markov chain stops moving?",
                "language": "en",
                "question_type": "misconception",
                "expected_status": "SUPPORTED",
                "answerable": True,
                "gold_source_locators": by_concept["m05-stationary-distribution"].get("gold_source_locators", []),
                "gold_evidence_phrases": ["stationary distribution", "πP"],
                "required_claims": [],
            },
            {
                "case_id": "hard-hint-stationary-distribution",
                "module_id": "module05",
                "concept_id": "m05-stationary-distribution",
                "question": "Give me a hint for finding a stationary distribution without solving the whole problem for me.",
                "language": "en",
                "question_type": "hint",
                "expected_status": "SUPPORTED",
                "answerable": True,
                "gold_source_locators": by_concept["m05-stationary-distribution"].get("gold_source_locators", []),
                "gold_evidence_phrases": ["stationary distribution"],
                "required_claims": [],
            },
            {
                "case_id": "hard-why-poisson-waiting",
                "module_id": "module01",
                "concept_id": "m01-poisson-process",
                "question": "If arrivals have constant rate λ, why is the event of waiting longer than t the same as observing zero arrivals before t?",
                "language": "en",
                "question_type": "why",
                "expected_status": "SUPPORTED",
                "answerable": True,
                "gold_source_locators": by_concept["m01-poisson-process"].get("gold_source_locators", []),
                "gold_evidence_phrases": ["Poisson process", "exponential"],
                "required_claims": [],
            },
            {
                "case_id": "hard-condition-hitting-time",
                "module_id": "module02",
                "concept_id": "m02-absorption-time",
                "question": "For a random walk, how would the expected time to absorption change if the starting state moved closer to the target boundary?",
                "language": "en",
                "question_type": "conditions",
                "expected_status": "SUPPORTED",
                "answerable": True,
                "gold_source_locators": by_concept["m02-absorption-time"].get("gold_source_locators", []),
                "gold_evidence_phrases": ["Absorption time"],
                "required_claims": [],
            },
            {
                "case_id": "hard-follow-up-brownian-scaling",
                "module_id": "module04",
                "concept_id": "m04-brownian-scaling",
                "question": "After changing the number of grid steps, what should I compare to decide whether the random walk still approximates Brownian motion?",
                "language": "en",
                "question_type": "follow_up",
                "expected_status": "SUPPORTED",
                "answerable": True,
                "gold_source_locators": by_concept["m04-brownian-scaling"].get("gold_source_locators", []),
                "gold_evidence_phrases": ["Brownian", "scaled random walk"],
                "required_claims": [],
            },
            {
                "case_id": "hard-partial-hitting-time-missing-conditions",
                "module_id": "module02",
                "concept_id": "m02-absorption-time",
                "question": "What is the exact expected hitting time for this random walk?",
                "language": "en",
                "question_type": "derivation",
                "expected_status": "PARTIAL",
                "answerable": False,
                "gold_source_locators": partial.get("gold_source_locators", []),
                "gold_evidence_phrases": partial.get("gold_evidence_phrases", [])[:2],
                "required_claims": [],
            },
            {
                "case_id": "hard-out-of-scope-travel-expenses",
                "module_id": None,
                "concept_id": None,
                "question": "Can an external contractor claim travel expenses?",
                "language": "en",
                "question_type": "out_of_scope",
                "expected_status": "OUT_OF_SCOPE",
                "answerable": False,
                "gold_source_locators": [],
                "gold_evidence_phrases": [],
                "required_claims": [],
            },
            {
                "case_id": "hard-out-of-scope-weather",
                "module_id": None,
                "concept_id": None,
                "question": "What will the weather be tomorrow in Stockholm?",
                "language": "en",
                "question_type": "out_of_scope",
                "expected_status": "OUT_OF_SCOPE",
                "answerable": False,
                "gold_source_locators": [],
                "gold_evidence_phrases": [],
                "required_claims": [],
            },
        ]
    )
    OUTPUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"wrote {len(cases)} cases covering {len(by_concept)} knowledge points")


if __name__ == "__main__":
    main()
