#!/usr/bin/env python3
"""
query.py
---------
Loads `project_knowledge.jsonld` and answers simple natural-language questions by doing a
keyword-based semantic search over the structured JSON-LD content.
"""
import sys
import json
import re
from pathlib import Path

def load_knowledge(path="project_knowledge.jsonld"):
    return json.loads(Path(path).read_text(encoding="utf-8"))

BUCKETS = {
    "purpose": ["what is", "what's", "purpose", "use case", "for?", "why", "description", "overview"],
    "install": ["install", "pip", "pip3", "how to install", "setup", "requirements"],
    "example": ["example", "code", "snippet", "usage", "demo"],
    "features": ["feature", "component", "capability", "supports"],
    "license": ["license", "mit", "apache"],
    "dependencies": ["dependenc", "requires", "python", "version"],
}

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def pick_bucket(question: str) -> str:
    ql = question.lower()
    best, score = "purpose", 0
    for b, kws in BUCKETS.items():
        s = sum(1 for k in kws if k in ql)
        if s > score:
            best, score = b, s
    return best

def answer(data, bucket: str) -> str:
    if bucket == "purpose":
        return normalize(data.get("description", "No description available."))
    if bucket == "install":
        how = data.get("installInstructions", {})
        steps = [normalize(s.get("text", "")) for s in how.get("step", [])]
        return "Installation:\n- " + "\n- ".join(steps) if steps else "No install instructions found."
    if bucket == "example":
        exs = data.get("exampleOfWork", [])
        if not exs:
            return "No code example found."
        return exs[0].get("text", "No code example found.")
    if bucket == "features":
        feats = data.get("featureList", [])
        return "Key features:\n- " + "\n- ".join(feats) if feats else "No features found."
    if bucket == "license":
        return f"License: {data.get('license', 'Unknown')}"
    if bucket == "dependencies":
        reqs = data.get("softwareRequirements", [])
        return "Requirements:\n- " + "\n- ".join(reqs) if reqs else "No requirements listed."
    return "Sorry, I couldn't match your question. Try asking about installation, examples, features, or license."

def main():
    if len(sys.argv) < 2:
        print("Please provide a natural-language question, e.g., python query.py \"How do I install the sdk?\"")
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    data = load_knowledge()
    bucket = pick_bucket(question)
    print(answer(data, bucket))

if __name__ == "__main__":
    main()
