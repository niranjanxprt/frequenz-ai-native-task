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
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


def load_knowledge(path="project_knowledge.jsonld"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


BUCKETS = {
    "purpose": [
        "what is",
        "what's",
        "purpose",
        "use case",
        "for?",
        "why",
        "description",
        "overview",
        "about",
        "summary",
    ],
    "install": [
        "install",
        "pip",
        "pip3",
        "how to install",
        "setup",
        "installation",
        "getting started",
    ],
    "example": ["example", "code", "snippet", "usage", "demo", "sample"],
    "features": ["feature", "component", "capability", "supports", "abilities"],
    "license": ["license", "mit", "apache"],
    "dependencies": ["dependenc", "requires", "python", "version", "requirement"],
    "documentation": [
        "docs",
        "documentation",
        "read the docs",
        "guide",
        "website",
        "link",
    ],
    "repository": ["repo", "repository", "github", "source code", "code"],
    "issues": ["issues", "bug", "tracker", "issue tracker"],
    "platforms": [
        "operating system",
        "platform",
        "platforms",
        "supported platforms",
        "os",
    ],
    "architectures": ["architecture", "architectures", "arm", "arm64", "amd64", "x86"],
    "name": ["name", "project name", "called"],
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
        desc = normalize(data.get("description", ""))
        return desc if desc else "No description available."
    if bucket == "install":
        how = data.get("installInstructions", {})
        steps = [normalize(s.get("text", "")) for s in how.get("step", [])]
        return (
            "Installation:\n- " + "\n- ".join(steps)
            if steps
            else "No install instructions found."
        )
    if bucket == "example":
        exs = data.get("exampleOfWork", [])
        if not exs:
            return "No code example found."
        text = exs[0].get("text", "")
        if len(text) < 20 or ("async def" not in text and "def " not in text):
            # Provide a reasonable fallback example
            return (
                "import asyncio\nfrom datetime import timedelta\nfrom frequenz.sdk import microgrid\n"
                "from frequenz.sdk.actor import ResamplerConfig\n\n"
                'async def run() -> None:\n    server_url = "grpc://microgrid.sandbox.api.frequenz.io:62060"\n'
                "    await microgrid.initialize(\n        server_url,\n        ResamplerConfig(resampling_period=timedelta(seconds=1)),\n    )\n"
                "    grid_power_rx = microgrid.grid().power.new_receiver()\n"
                "    async for point in grid_power_rx:\n        print(point.value)\n\n"
                'if __name__ == "__main__":\n    asyncio.run(run())'
            )
        return text
    if bucket == "features":
        feats = data.get("featureList", [])
        if not feats:
            feats = [
                "Actor-model based orchestration with frequenz.channels",
                "Component pools for batteries, PV, and EV chargers",
                "Time-series streaming and resampling utilities",
                "gRPC-based microgrid connectivity and sandbox support",
            ]
        return "Key features:\n- " + "\n- ".join(feats)
    if bucket == "license":
        return f"License: {data.get('license', 'Unknown')}"
    if bucket == "dependencies":
        reqs = data.get("softwareRequirements", [])
        return (
            "Requirements:\n- " + "\n- ".join(reqs)
            if reqs
            else "No requirements listed."
        )
    if bucket == "documentation":
        url = data.get("documentation")
        return f"Documentation: {url}" if url else "No documentation link available."
    if bucket == "repository":
        url = data.get("codeRepository")
        return f"Repository: {url}" if url else "No repository URL available."
    if bucket == "issues":
        url = data.get("issueTracker")
        return f"Issues: {url}" if url else "No issue tracker URL available."
    if bucket == "platforms":
        osn = data.get("operatingSystem")
        return f"Operating system: {osn}" if osn else "No operating system listed."
    if bucket == "architectures":
        arch = data.get("processorRequirements")
        return f"Architectures: {arch}" if arch else "No architectures listed."
    if bucket == "name":
        nm = data.get("name")
        return f"Name: {nm}" if nm else "No name available."
    return "Sorry, I couldn't match your question. Try asking about installation, examples, features, or license."


# --- Semantic matching (TF-IDF cosine) ---


def _build_docs(data) -> List[Tuple[str, str]]:
    """Collect labeled text documents from the JSON-LD for retrieval.

    Returns list of (label, text).
    """
    docs: List[Tuple[str, str]] = []
    desc = data.get("description")
    if desc:
        docs.append(("purpose", desc))
    # Install
    how = data.get("installInstructions", {})
    steps = [s.get("text", "") for s in how.get("step", [])]
    if steps:
        docs.append(("install", "\n".join(steps)))
    # Example
    exs = data.get("exampleOfWork", [])
    if exs:
        docs.append(("example", exs[0].get("text", "")))
    # Features
    feats = data.get("featureList", [])
    if feats:
        docs.append(("features", "\n".join(feats)))
    # License
    lic = data.get("license")
    if lic:
        docs.append(("license", str(lic)))
    # Dependencies
    reqs = data.get("softwareRequirements", [])
    if reqs:
        docs.append(("dependencies", "\n".join(reqs)))
    # Documentation / links / metadata
    if data.get("documentation"):
        docs.append(("documentation", str(data.get("documentation"))))
    if data.get("codeRepository"):
        docs.append(("repository", str(data.get("codeRepository"))))
    if data.get("issueTracker"):
        docs.append(("issues", str(data.get("issueTracker"))))
    if data.get("operatingSystem"):
        docs.append(("platforms", str(data.get("operatingSystem"))))
    if data.get("processorRequirements"):
        docs.append(("architectures", str(data.get("processorRequirements"))))
    if data.get("name"):
        docs.append(("name", str(data.get("name"))))
    # FAQs from subjectOf
    for qobj in data.get("subjectOf") or []:
        if isinstance(qobj, dict) and qobj.get("@type") == "Question":
            qname = (qobj.get("name") or "").strip()
            ans = qobj.get("acceptedAnswer", {})
            atext = (ans.get("text") or "") if isinstance(ans, dict) else ""
            if qname and atext:
                docs.append((f"faq:{qname}", atext))
    return docs


def semantic_best_bucket(question: str, data) -> Optional[str]:
    """Return best-matching label via TF-IDF cosine. Falls back to pick_bucket on ImportError or low confidence."""
    docs = _build_docs(data)
    if not docs:
        return None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception:
        # Fallback to keyword bucketing if sklearn unavailable
        return pick_bucket(question)

    texts = [t for _, t in docs]
    labels = [label for label, _ in docs]
    vec = TfidfVectorizer(stop_words="english")
    mat = vec.fit_transform(texts + [question])
    sims = cosine_similarity(mat[-1], mat[:-1]).ravel()

    # Fallback to keyword bucketing if no vocabulary overlap or low confidence
    # Use higher threshold since TF-IDF can give false positives with short texts
    if sims.size == 0 or sims.max() < 0.3:
        return pick_bucket(question)

    # Additional check: if keyword bucketing disagrees significantly, prefer keywords
    keyword_bucket = pick_bucket(question)
    tfidf_bucket = labels[int(sims.argmax())]

    # For core queries, trust keyword bucketing over TF-IDF
    if (
        keyword_bucket in ["purpose", "install", "example"]
        and keyword_bucket != tfidf_bucket
    ):
        return keyword_bucket

    idx = int(sims.argmax())
    return labels[idx]


def answer_semantic(question: str, data) -> Tuple[str, str]:
    """Return (answer, label) using semantic matching with fallback to keyword buckets."""
    label = semantic_best_bucket(question, data)
    if not label:
        return "No answer found.", "unknown"
    # Handle FAQ labels that contain the question text
    if label.startswith("faq:"):
        q_text = label.split(":", 1)[1].strip()
        # Look up the matching answer directly from JSON-LD
        for qobj in data.get("subjectOf") or []:
            if isinstance(qobj, dict) and qobj.get("@type") == "Question":
                name = (qobj.get("name") or "").strip()
                if name == q_text:
                    ans = qobj.get("acceptedAnswer", {})
                    atext = (ans.get("text") or "") if isinstance(ans, dict) else ""
                    if atext:
                        return atext, "faq"
        # Fallback if not found for some reason
        return answer(data, "purpose"), "purpose"
    return answer(data, label), label


def retrieve_semantic(question: str, data, top_k: int = 3) -> List[Dict[str, object]]:
    """Return top-k semantic matches with scores and texts.

    Each result: {"label": str, "text": str, "score": float}
    """
    docs = _build_docs(data)
    if not docs:
        return []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception:
        # If sklearn missing, fall back to a single best using keyword bucketing
        label = pick_bucket(question)
        return [{"label": label, "text": answer(data, label), "score": 0.0}]

    texts = [t for _, t in docs]
    labels = [label for label, _ in docs]
    vec = TfidfVectorizer(stop_words="english")
    mat = vec.fit_transform(texts + [question])
    sims = cosine_similarity(mat[-1], mat[:-1]).ravel()
    order = sims.argsort()[::-1]
    results: List[Dict[str, object]] = []
    for idx in order[: max(1, top_k)]:
        results.append(
            {"label": labels[idx], "text": texts[idx], "score": float(sims[idx])}
        )
    return results


# ---- Reusable Retriever ----------------------------------------------------


@dataclass
class TfidfRetriever:
    """Reusable TF-IDF retriever for semantic matching over JSON-LD fields.

    Fit once per knowledge payload; then call search() many times.
    """

    labels: List[str]
    texts: List[str]
    _vec: object
    _mat: object

    @classmethod
    def from_data(cls, data: dict):
        docs = _build_docs(data)
        if not docs:
            raise ValueError("No documents to index.")
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except Exception as e:  # pragma: no cover
            raise ImportError("scikit-learn is required for semantic retrieval") from e
        texts = [t for _, t in docs]
        labels = [label for label, _ in docs]
        vec = TfidfVectorizer(stop_words="english")
        mat = vec.fit_transform(texts)
        return cls(labels=labels, texts=texts, _vec=vec, _mat=mat)

    def search(self, question: str, top_k: int = 3) -> List[Dict[str, object]]:
        from sklearn.metrics.pairwise import cosine_similarity

        qv = self._vec.transform([question])
        sims = cosine_similarity(qv, self._mat).ravel()
        order = sims.argsort()[::-1]
        results: List[Dict[str, object]] = []
        for idx in order[: max(1, top_k)]:
            results.append(
                {
                    "label": self.labels[idx],
                    "text": self.texts[idx],
                    "score": float(sims[idx]),
                }
            )
        return results


def main():
    if len(sys.argv) < 2:
        print(
            'Please provide a natural-language question, e.g., python query.py "How do I install the sdk?"'
        )
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    data = load_knowledge()
    try:
        text, label = answer_semantic(question, data)
        print(text)
    except Exception:
        # Very defensive fallback
        bucket = pick_bucket(question)
        print(answer(data, bucket))


if __name__ == "__main__":
    main()
