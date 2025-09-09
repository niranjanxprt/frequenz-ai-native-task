#!/usr/bin/env python3
"""
extract.py
-----------
Extracts key information from the Frequenz SDK for Python README and generates a JSON-LD file
named `project_knowledge.jsonld`.

Usage:
    python extract.py [--repo-url URL] [--out OUTPATH]

Defaults:
    --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python
    --out      ./project_knowledge.jsonld
"""
import argparse
import json
import re
from pathlib import Path

import requests
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from typing import Optional, List, Tuple

RAW_DEFAULT = "https://github.com/frequenz-floss/frequenz-sdk-python/blob/v1.x.x/README.md"
DEFAULT_BRANCH = "main"

def _to_raw_from_github_web(url: str) -> Optional[str]:
    """Convert a GitHub web URL with /blob/ to a raw URL.

    Example:
      https://github.com/org/repo/blob/v1.x.x/README.md
      -> https://raw.githubusercontent.com/org/repo/v1.x.x/README.md
    """
    if not url.startswith("https://github.com/"):
        return None
    try:
        parts = url.split("github.com/")[1].split("/")
        # Expect: owner/repo/blob/ref/path...
        if len(parts) >= 4 and parts[2] == "blob":
            owner, repo, _, ref = parts[:4]
            path = "/".join(parts[4:])
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
        # Some URLs may be /raw/
        if len(parts) >= 4 and parts[2] == "raw":
            owner, repo, _, ref = parts[:4]
            path = "/".join(parts[4:])
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    except Exception:
        return None
    return None

def fetch_readme(repo_url: str, ref: Optional[str] = None) -> str:
    """Fetch README text from a raw GitHub URL.

    Accepts either:
    - a full raw README URL (e.g., https://raw.githubusercontent.com/.../main/README.md), or
    - a repo raw base URL (e.g., https://raw.githubusercontent.com/org/repo).

    If a repo base is given, tries common branches (main, master) and README name variants.
    Adds headers to reduce 403/429. Raises RuntimeError with guidance for --local-readme.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "ai-native-kg/0.1 (+https://github.com/)",
            "Accept": "text/plain, text/markdown, */*",
        }
    )
    # Normalize GitHub web URLs (with /blob/ or /raw/) to raw URLs
    norm = _to_raw_from_github_web(repo_url.strip())
    if norm:
        repo_url = norm

    # If a full README path (raw) was provided, try it directly first
    lower = repo_url.lower().strip()
    if lower.startswith("https://raw.githubusercontent.com/") and (
        lower.endswith((".md", ".rst", ".txt")) or "/readme" in lower
    ):
        try:
            r = session.get(repo_url, timeout=20)
            if r.status_code == 200 and len(r.text) > 120:
                return r.text
        except Exception:
            pass

    # Otherwise, treat as repo base and construct candidates from common branches
    readme_names = [
        "README.md",
        "README.MD",
        "Readme.md",
        "readme.md",
        "README.rst",
        "docs/README.md",
        "README",
    ]
    branches = [ref] if ref else ["main", "master"]
    tried = []
    for br in branches:
        for fname in readme_names:
            url = f"{repo_url.rstrip('/')}/{br}/{fname}"
            try:
                r = session.get(url, timeout=20)
                if r.status_code == 200 and len(r.text) > 120:
                    return r.text
                tried.append(f"{url} -> {r.status_code}")
            except Exception as e:
                tried.append(f"{url} -> {e}")
    raise RuntimeError(
        "Could not fetch README. Tried:\n- "
        + "\n- ".join(tried)
        + "\nTip: run with --local-readme path/to/README.md to parse a local file."
    )

def md_to_soup(md_text: str) -> BeautifulSoup:
    html = MarkdownIt().render(md_text)
    return BeautifulSoup(html, "html.parser")

def parse_supported_platforms(md_text: str) -> Tuple[Optional[List[str]], Optional[str], Optional[str]]:
    """Parse the "Supported Platforms" section from README markdown.

    Returns (python_versions, operating_system, architectures)
    where python_versions is a list of version strings like ["3.11","3.12","3.13"].
    """
    py_vers: Optional[List[str]] = None
    os_name: Optional[str] = None
    arch: Optional[str] = None
    lines = md_text.splitlines()
    in_section = False
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## supported platforms"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") and i != 0:
                break  # next section
            # bullets like "- **Python:** 3.11 .. 3.13"
            low = line.lower().strip()
            if low.startswith("- **python:**") or low.startswith("- **python:"):
                # extract versions
                rest = line.split(":", 1)[-1]
                # patterns: "3.11 .. 3.13" or comma list
                import re as _re
                m = _re.search(r"(\d+\.\d+)\s*\.\.\s*(\d+\.\d+)", rest)
                if m:
                    start = m.group(1)
                    end = m.group(2)
                    try:
                        s_major, s_minor = map(int, start.split("."))
                        e_major, e_minor = map(int, end.split("."))
                        if s_major == e_major:
                            py_vers = [f"{s_major}.{x}" for x in range(s_minor, e_minor + 1)]
                        else:
                            py_vers = [start, end]
                    except Exception:
                        py_vers = [start, end]
                else:
                    vers = [v.strip() for v in rest.replace("**", "").split(",") if v.strip()]
                    if vers:
                        py_vers = vers
            elif low.startswith("- **operating system:**"):
                os_name = line.split(":", 1)[-1].strip().strip("*")
            elif low.startswith("- **architectures:**"):
                arch = line.split(":", 1)[-1].strip().strip("*")
    return py_vers, os_name, arch

def parse_links(md_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse documentation and PyPI links from README markdown text."""
    import re as _re
    docs = None
    pypi = None
    m = _re.search(r"https://frequenz[-\w\.]+/frequenz-sdk-python/?", md_text)
    if m:
        docs = m.group(0)
    m2 = _re.search(r"https://pypi\.org/project/[\w\-_.]+/?", md_text)
    if m2:
        pypi = m2.group(0)
    return docs, pypi

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

def sections_to_creativeworks(sections: dict, max_sections: int = 8, max_chars: int = 4000):
    """Convert parsed sections into a list of CreativeWork entries for JSON‑LD.

    Aggregates text from paragraphs/lists/code blocks. Truncates long content.
    """
    works: List[dict] = []
    count = 0
    for title_lc, elements in sections.items():
        # Skip very short pseudo titles
        if not title_lc or len(title_lc) < 3:
            continue
        # Reconstruct text content
        parts: List[str] = []
        for el in elements:
            try:
                t = el.get_text("\n", strip=True)
                if t:
                    parts.append(t)
            except Exception:
                continue
        text = "\n\n".join(parts).strip()
        if not text:
            continue
        if len(text) > max_chars:
            text = text[: max_chars - 1] + "…"
        works.append({
            "@type": "CreativeWork",
            "name": title_lc,
            "text": text,
        })
        count += 1
        if count >= max_sections:
            break
    return works

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
    ap.add_argument(
        "--ref",
        default=None,
        help="Optional branch or tag (e.g., main, master, v1.x.x) when using a repo base URL",
    )
    # Branch selection removed; we try common branches automatically
    ap.add_argument("--out", default="project_knowledge.jsonld")
    ap.add_argument("--license-url", default="https://opensource.org/licenses/MIT")
    ap.add_argument("--python-versions", default="3.11,3.12", help="Comma-separated (e.g., 3.11,3.12)")
    ap.add_argument("--local-readme", default=None, help="Optional local README.md path to parse instead of fetching")
    args = ap.parse_args()

    if args.local_readme:
        md = Path(args.local_readme).read_text(encoding="utf-8")
    else:
        md = fetch_readme(args.repo_url, ref=args.ref)
    soup = md_to_soup(md)
    sections = extract_sections(soup)

    name = "Frequenz SDK for Python"
    desc = first_paragraph(soup) or "A development kit to interact with the Frequenz development platform."
    installs = find_install_instructions(soup) or ["pip install frequenz-sdk"]
    features = guess_features(sections)
    examples = collect_code_examples(soup)
    # Try to discover supported platforms & links from README
    detected_py, os_name, arch = parse_supported_platforms(md)
    docs_link, pypi_link = parse_links(md)
    # Final python versions: prefer detected, else CLI default
    py_versions = detected_py or [v.strip() for v in args.python_versions.split(",") if v.strip()]

    jsonld = build_jsonld(name, desc, installs, features, examples, args.license_url, py_versions)
    # Add section-level creative works for improved retrieval
    has_part = sections_to_creativeworks(sections)
    if has_part:
        jsonld["hasPart"] = has_part
    if os_name:
        jsonld["operatingSystem"] = os_name
    if arch:
        jsonld["processorRequirements"] = arch
    if docs_link:
        jsonld["documentation"] = docs_link
    if pypi_link:
        jsonld["downloadUrl"] = pypi_link
    # Issue tracker link (predictable from repository)
    jsonld["issueTracker"] = "https://github.com/frequenz-floss/frequenz-sdk-python/issues"
    Path(args.out).write_text(json.dumps(jsonld, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
