"""Bounded live acceptance using only the reviewed, public PIB selection."""
import json
from pathlib import Path

import httpx

selection = json.loads(Path("outputs/submission-sources/published-selection.json").read_text(encoding="utf-8"))
records = {r["key"]: r for r in selection["records"]}
checks = [
    ("constitution", "Who was Chairman of the Drafting Committee?", "Ambedkar"),
    ("constitution", "On what date did the Constitution come into force?", "26 January 1950"),
    ("biography", "On what date was Ambedkar born?", "14 April 1891"),
]
results = []
with httpx.Client(base_url="http://127.0.0.1:8000/archive/", timeout=100, trust_env=False) as client:
    provider = client.get("research/provider").json()
    for key, question, expected in checks:
        r = client.post("research/ask", json={"question": question, "item_id": records[key]["id"]})
        r.raise_for_status()
        result = r.json()
        assert result["status"] == "answered", result["status"] + ": " + result.get("message", "")
        answer_text = " ".join(p["text"] for p in result["paragraphs"]).casefold()
        acceptable = {"26 January 1950": ["26 january 1950", "january 26, 1950"],
                      "14 April 1891": ["14 april 1891", "april 14, 1891"]}.get(expected, [expected.casefold()])
        assert result["paragraphs"] and any(value in answer_text for value in acceptable), answer_text
        for paragraph in result["paragraphs"]:
            for evidence in paragraph["evidence"]:
                source = next(s for s in result["sources"] if s["passage_id"] == evidence["passage_id"])
                assert source["item_id"] == records[key]["id"]
                assert source["revision"] == records[key]["revision"]
                assert evidence["quote"] in source["excerpt"]
                assert source["page_number"] is None, "Do not invent page numbers for plain text"
                assert client.get(source["reader_url"].replace("/archive/", "catalog/", 1).split('#')[0]).is_success
        results.append({"question": question, "expected": expected, "result": result})
        print("PASS cited live answer:", question)
    unsupported_response = client.post("research/ask", json={"question": "What did Ambedkar say about quantum computing?", "item_id": records["biography"]["id"]})
    unsupported_response.raise_for_status()
    unsupported = unsupported_response.json()
    assert unsupported["status"] == "insufficient_sources" and not unsupported["paragraphs"], unsupported
    absent_response = client.post("research/ask", json={"question": "What do the sources say about Martian horticulture?", "item_id": records["biography"]["id"], "language": "Language not in the selection"})
    absent_response.raise_for_status()
    absent = absent_response.json()
    assert absent["status"] == "insufficient_sources" and not absent["generation_attempted"]
    Path("outputs/deadline-live-research.json").write_text(
        json.dumps({"provider": provider, "answers": results, "unsupported_question": unsupported, "no_matching_evidence": absent}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("3 live cited answers passed; 1 unsupported-question abstention and 1 no-matching-evidence check passed")
