"""Alternative entrypoint for teams that want `deepeval test run` semantics
(pytest exit codes, `deepeval` CLI reporting) instead of layer4/runner.py's
JSON/HTML output. Both read the same suite.yaml/target/dataset, so pick
whichever fits your CI step better -- they aren't meant to run together.

Usage:
    deepeval test run tests/test_owasp_gate.py
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from layer4.config import SuiteConfig, TargetConfig, load_probes
from layer4.gateway_client import GatewayClient
from layer4.owasp_metrics import build_metric

SUITE = SuiteConfig.load("suite.yaml")
TARGET = TargetConfig.load(SUITE.target_path)
PROBES = load_probes(SUITE.dataset_path)
CLIENT = GatewayClient(TARGET)


@pytest.mark.parametrize("probe", PROBES, ids=[p["id"] for p in PROBES])
def test_owasp_probe(probe):
    category = probe["category"]
    threshold = SUITE.threshold_for(category)
    metric = build_metric(category, threshold, SUITE.deepeval_judge_model)

    response = CLIENT.query(probe["input"])

    test_case = LLMTestCase(
        input=probe["input"],
        actual_output=response["actual_output"],
        expected_output=probe.get("expected_behavior", ""),
        retrieval_context=response.get("retrieval_context"),
    )

    assert_test(test_case, [metric])
