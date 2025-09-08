#!/usr/bin/env python3
"""
extract.py
-----------
Extracts key information from the Frequenz SDK for Python README and generates a JSON-LD file
named `project_knowledge.jsonld`.

Usage:
    python extract.py [--repo-url URL] [--branch BRANCH] [--out OUTPATH]

Defaults:
    --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python
    --branch   main
    --out      ./project_knowledge.jsonld
"""
import argparse
import json
import re
from pathlib import Path

import requests
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from typing import Optional, List

RAW_DEFAULT = "https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python"
DEFAULT_BRANCH = "main"

def fetch_readme(repo_url: str, branch: str) -> str:
    """Fetch README text from a raw GitHub URL.

    Accepts either:
    - a full raw README URL (e.g., https://raw.githubusercontent.com/.../main/README.md), or
    - a repo raw base URL (e.g., https://raw.githubusercontent.com/org/repo), plus ``branch``.

    Tries several common filename variants and adds headers to reduce 403/429s.
    Raises a RuntimeError with guidance to use --local-readme if all attempts fail.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "ai-native-kg/0.1 (+https://github.com/)",
            "Accept": "text/plain, text/markdown, */*",
        }
    )
    # If a full README path was provided, try it directly first
    direct = []
    lower = repo_url.lower()
    if lower.endswith((".md", ".rst", ".txt")) or "/readme" in lower:
        direct.append(repo_url)
        # If the URL hardcodes /main/ but a different branch was selected, try swapping it in
        if "/main/" in repo_url and branch and branch != "main":
            direct.append(repo_url.replace("/main/", f"/{branch}/"))

    for url in direct:
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200 and len(r.text) > 120:
                return r.text
        except Exception:
            pass

    # Otherwise, construct candidates from base + branch + common names
    candidates = [
        "README.md",
        "README.MD",
        "Readme.md",
        "readme.md",
        "README.rst",
        "docs/README.md",
        "README",
    ]
    errors = []
    for fname in candidates:
        url = f"{repo_url}/{branch}/{fname}"
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200 and len(r.text) > 120:
                return r.text
            errors.append(f"{url} -> {r.status_code}")
        except Exception as e:
            errors.append(f"{url} -> {e}")
    raise RuntimeError(
        "Could not fetch README from "
        f"{repo_url}/{branch}. Tried: " + ", ".join(candidates) + ". "
        "Tip: run with --local-readme path/to/README.md to parse a local file."
    )

def md_to_soup(md_text: str) -> BeautifulSoup:
    html = MarkdownIt().render(md_text)
    return BeautifulSoup(html, "html.parser")

def extract_sections(soup: BeautifulSoup):
    # Build a mapping of h2/h3 section -> content (text + code)
    sections = {}
    current = None
    for el in soup.recursiveChildGenerator():
        if getattr(el, "name", None) in ("h1", "h2", "h3"):
            current = el.get_text(strip=True)
            sections[current.lower()] = []
        elif current is not None and getattr(el, "name", None) in ("p", "ul", "ol", "pre"):
            sections[current.lower()].append(el)
    return sections

def first_paragraph(soup: BeautifulSoup) -> str:
    p = soup.find("p")
    return p.get_text(" ", strip=True) if p else ""

def collect_code_examples(soup: BeautifulSoup, max_examples: int = 2):
    code_blocks = []
    for pre in soup.find_all("pre"):
        code = pre.get_text("\n", strip=True)
        if len(code) > 40:
            code_blocks.append(code)
        if len(code_blocks) >= max_examples:
            break
    return code_blocks

def find_install_instructions(soup: BeautifulSoup):
    # Look for common install strings
    text = soup.get_text("\n")
    candidates = []
    for line in text.splitlines():
        if "pip install" in line or "pip3 install" in line:
            candidates.append(line.strip())
    # Deduplicate but keep order
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out[:3]

def guess_features(sections: dict):
    # Try to find a "features" section or bullet lists near intro
    for key in sections:
        if "feature" in key:
            feats = []
            for el in sections[key]:
                for li in el.find_all("li"):
                    txt = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
                    if txt:
                        feats.append(txt)
            if feats:
                return feats[:10]
    # Fallback: look for bullets containing keywords
    feats = []
    for key in sections:
        for el in sections[key]:
            for li in el.find_all("li"):
                txt = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
                if any(k in txt.lower() for k in ["battery", "pv", "ev", "actor", "channel", "timeseries", "microgrid", "report", "trading"]):
                    feats.append(txt)
    return list(dict.fromkeys(feats))[:10]

def build_jsonld(
    name: str,
    desc: str,
    installs,
    features,
    examples,
    license_url: Optional[str],
    py_versions: Optional[List[str]],
):
    context = {
        "@vocab": "https://schema.org/",
        "fre": "https://frequenz.com/ontology#",
    }
    data = {
        "@context": context,
        "@type": "SoftwareApplication",
        "name": name,
        "applicationCategory": "Energy management / Microgrid orchestration",
        "description": desc,
        "programmingLanguage": "Python",
        "codeRepository": "https://github.com/frequenz-floss/frequenz-sdk-python",
        "author": {"@type": "Organization", "name": "Frequenz"},
        "isAccessibleForFree": True,
    }
    if license_url:
        data["license"] = license_url
    if py_versions:
        data["softwareRequirements"] = [f"Python {v}" for v in py_versions]
    if installs:
        data["installInstructions"] = {
            "@type": "HowTo",
            "name": "Install the Frequenz SDK for Python",
            "step": [{"@type": "HowToStep", "text": cmd} for cmd in installs],
        }
    if features:
        data["featureList"] = features
    if examples:
        data["exampleOfWork"] = [
            {
                "@type": "SoftwareSourceCode",
                "programmingLanguage": "Python",
                "codeSampleType": "example",
                "text": ex,
            }
            for ex in examples
        ]
    # Include a small FAQ as Question/Answer pairs for discoverability
    try:
        faq: List[dict] = []
        # Build canonical questions
        qas = [
            ("What is the Frequenz SDK for?", desc or ""),
        ]
        # Install
        steps = [s.get("text", "") for s in data.get("installInstructions", {}).get("step", [])]
        if steps:
            qas.append(("How do I install the SDK?", "Installation:\n- " + "\n- ".join(steps)))
        # Example
        exs = data.get("exampleOfWork", [])
        if exs:
            qas.append(("Show me an example of how to use it.", exs[0].get("text", "")))
        # Features
        feats = data.get("featureList", [])
        if feats:
            qas.append(("What features does it have?", "Key features:\n- " + "\n- ".join(feats)))
        # License
        if data.get("license"):
            qas.append(("What license is it under?", f"License: {data['license']}"))
        # Dependencies
        reqs = data.get("softwareRequirements", [])
        if reqs:
            qas.append(("Which Python versions does it require?", "Requirements:\n- " + "\n- ".join(reqs)))

        for q_text, a_text in qas:
            if not q_text or not a_text:
                continue
            faq.append(
                {
                    "@type": "Question",
                    "name": q_text,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": a_text,
                    },
                }
            )
        if faq:
            data["subjectOf"] = faq
    except Exception:
        # Non-fatal; FAQ is optional
        pass

    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-url", default=RAW_DEFAULT)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--out", default="project_knowledge.jsonld")
    ap.add_argument("--license-url", default="https://opensource.org/licenses/MIT")
    ap.add_argument("--python-versions", default="3.11,3.12", help="Comma-separated (e.g., 3.11,3.12)")
    ap.add_argument("--local-readme", default=None, help="Optional local README.md path to parse instead of fetching")
    args = ap.parse_args()

    if args.local_readme:
        md = Path(args.local_readme).read_text(encoding="utf-8")
    else:
        md = fetch_readme(args.repo_url, args.branch)
    soup = md_to_soup(md)
    sections = extract_sections(soup)

    name = "Frequenz SDK for Python"
    desc = first_paragraph(soup) or "A development kit to interact with the Frequenz development platform."
    installs = find_install_instructions(soup) or ["pip install frequenz-sdk"]
    features = guess_features(sections)
    examples = collect_code_examples(soup)
    py_versions = [v.strip() for v in args.python_versions.split(",") if v.strip()]

    jsonld = build_jsonld(name, desc, installs, features, examples, args.license_url, py_versions)
    Path(args.out).write_text(json.dumps(jsonld, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
