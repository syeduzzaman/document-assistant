"""Run a small deterministic benchmark against a running demo API. No third-party dependencies."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8080")
args = parser.parse_args()
cases = json.loads(Path(__file__).with_name("cases.json").read_text())
hits = reciprocal_ranks = supported = correct_refusals = 0
answerable = unanswerable = 0
results = []
for case in cases:
    request = Request(
        args.url.rstrip("/") + "/api/ask",
        data=json.dumps({"question": case["question"], "top_k": 3}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=90) as response:
        answer = json.load(response)
    if case["expected_filename"] is None:
        unanswerable += 1
        passed = answer["refused"] and not answer["sources"]
        correct_refusals += passed
    else:
        answerable += 1
        filenames = [source["filename"] for source in answer["sources"]]
        rank = next((index for index, name in enumerate(filenames, 1) if name == case["expected_filename"]), 0)
        hits += bool(rank)
        reciprocal_ranks += 1 / rank if rank else 0
        contains = case["expected_fragment"].casefold() in answer["answer"].casefold()
        supported += contains
        passed = bool(rank) and contains and not answer["refused"]
    results.append({"question": case["question"], "passed": bool(passed)})

report = {
    "cases": len(cases), "document_recall_at_3": hits / answerable,
    "document_mrr_at_3": reciprocal_ranks / answerable,
    "expected_answer_fragment_rate": supported / answerable,
    "unanswerable_refusal_accuracy": correct_refusals / unanswerable,
    "results": results,
}
print(json.dumps(report, indent=2))
raise SystemExit(0 if all(result["passed"] for result in results) else 1)
