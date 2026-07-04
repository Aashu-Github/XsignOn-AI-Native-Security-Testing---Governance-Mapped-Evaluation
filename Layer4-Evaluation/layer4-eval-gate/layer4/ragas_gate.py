"""RAGAS activation logic.

Answers the research doc's open question directly: activation is driven by
the explicit `type: rag` field in the target's YAML config (see
layer4/config.py:TargetConfig.is_rag), not by inference from the dataset
or the model's outputs. If a target isn't marked `type: rag`, this module
never runs and RAGAS contributes nothing to the verdict — matching the
"zero value for non-RAG targets" tradeoff noted in the research.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RagasResult:
    faithfulness: float
    answer_relevancy: float
    threshold: float

    @property
    def passed(self) -> bool:
        return self.faithfulness >= self.threshold and self.answer_relevancy >= self.threshold


def run_ragas(samples: list[dict], threshold: float, judge_model: str) -> RagasResult:
    """samples: list of {"question": str, "answer": str, "contexts": list[str]}

    Only called when TargetConfig.is_rag is True. Requires OPENAI_API_KEY
    (or your configured judge provider) to be set, since faithfulness and
    answer relevancy are both LLM-as-judge metrics.
    """
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import Faithfulness, ResponseRelevancy

    dataset = Dataset.from_dict(
        {
            "question": [s["question"] for s in samples],
            "answer": [s["answer"] for s in samples],
            "contexts": [s["contexts"] for s in samples],
        }
    )

    result = evaluate(
        dataset,
        metrics=[Faithfulness(), ResponseRelevancy()],
    )
    df = result.to_pandas()

    return RagasResult(
        faithfulness=float(df["faithfulness"].mean()),
        answer_relevancy=float(df["answer_relevancy"].mean()),
        threshold=threshold,
    )
