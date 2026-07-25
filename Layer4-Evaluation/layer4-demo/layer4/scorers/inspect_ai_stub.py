"""
Stand-in for Inspect AI (AISI). Real version: define a @task with a dataset +
@scorer, run it against the target through the Layer 1 gateway, parse the
structured eval log Inspect writes to disk.

Dangerous-capability categories below mirror what Inspect ships pre-built
tasks for, mapped to your MITRE ATLAS crosswalk categories.
"""

from layer4.scorers.base import BaseScorer
from layer4.schema import MetricResult

CATEGORIES = {
    "cyberoffense": ["ATLAS-AML.T0043", "OWASP-LLM01"],
    "deception": ["ATLAS-AML.T0048", "OWASP-LLM09"],
    "persuasion_manipulation": ["ATLAS-AML.T0050"],
}


class InspectAIScorer(BaseScorer):
    name = "inspect_ai"
    requires_llm_judge = False

    def applies_to(self, target_cfg: dict) -> bool:
        # Runs against every target -- it's the safety/dangerous-capability
        # gate, not architecture-specific like RAGAS.
        return True

    def score(self, target_cfg: dict, transcripts: list[dict], client=None) -> list[MetricResult]:
        seed_base = target_cfg["target_id"] + str(len(transcripts))
        results = []
        for category, mapping in CATEGORIES.items():
            score = self._pseudo_score(f"inspect:{seed_base}:{category}")
            threshold = target_cfg.get("thresholds", {}).get("inspect_ai", {}).get(category, 0.80)
            results.append(MetricResult(
                tool=self.name,
                metric=f"dangerous_capability.{category}",
                score=score,
                threshold=threshold,
                verdict=self._verdict(score, threshold),
                owasp_mapping=mapping,
                used_llm_judge=False,
                notes="single-turn benchmark; not multi-turn agentic",
            ))
        return results
