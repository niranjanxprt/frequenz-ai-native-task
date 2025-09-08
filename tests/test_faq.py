import json
from pathlib import Path


def test_jsonld_has_faq_questions():
    data = json.loads(Path("project_knowledge.jsonld").read_text(encoding="utf-8"))
    faq = data.get("subjectOf") or []
    assert isinstance(faq, list)
    # Expect at least 6 canonical questions
    names = {q.get("name") for q in faq if isinstance(q, dict)}
    expected = {
        "What is the Frequenz SDK for?",
        "How do I install the SDK?",
        "Show me an example of how to use it.",
        "What features does it have?",
        "What license is it under?",
        "Which Python versions does it require?",
    }
    missing = expected - names
    assert not missing, f"Missing FAQ questions: {missing}"

