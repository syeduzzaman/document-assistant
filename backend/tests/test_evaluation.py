import json
from pathlib import Path

import pytest

CASES = json.loads((Path(__file__).resolve().parents[2] / "evaluations/cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[case["question"] for case in CASES])
def test_retrieval_and_answer_evaluation(sample_client, case):
    response = sample_client.post("/api/ask", json={"question": case["question"], "top_k": 3})
    assert response.status_code == 200
    answer = response.json()
    if case["expected_filename"] is None:
        assert answer["refused"] and not answer["sources"]
    else:
        assert not answer["refused"]
        assert case["expected_filename"] in [source["filename"] for source in answer["sources"]]
        assert case["expected_fragment"].casefold() in answer["answer"].casefold()
        assert all(source["text"] and source["page"] >= 1 for source in answer["sources"])
