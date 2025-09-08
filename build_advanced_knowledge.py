#!/usr/bin/env python3
"""
build_advanced_knowledge.py
---------------------------
Create an enriched JSON‑LD knowledge file (v2) from a repo snapshot TXT
that contains the directory tree and embedded README content blocks.

Outputs:
  - project_knowledge_v2.jsonld
  - advanced_chunks.jsonl (optional, flat chunk index for retrieval)

Usage:
  python build_advanced_knowledge.py --snapshot frequenz-*.txt \
      --out project_knowledge_v2.jsonld --chunks advanced_chunks.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Tuple, List

import extract  # reuse markdown parsing + builders
import visualize as viz


def parse_snapshot(path: Path) -> Dict[str, str]:
    """Parse a snapshot TXT file into a mapping: file_path -> content.

    Assumes blocks marked as:
      ========\nFILE: <path>\n========\n<content>\n
    Returns empty string for files that have no content block.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    files: Dict[str, str] = {}
    current: str | None = None
    acc: List[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*FILE:\s*(.+)$", line.strip())
        if m:
            # flush previous
            if current is not None:
                files[current] = "\n".join(acc).strip()
            current = m.group(1).strip()
            acc = []
        else:
            if current is not None:
                acc.append(line)
    if current is not None:
        files[current] = "\n".join(acc).strip()
    return files


def build_v2_knowledge(files: Dict[str, str]) -> Dict:
    # Prefer README.md content
    readme_text = files.get("README.md") or ""
    if not readme_text:
        raise RuntimeError("Snapshot does not include README.md content block.")
    soup = extract.md_to_soup(readme_text)
    sections = extract.extract_sections(soup)
    name = "Frequenz SDK for Python"
    desc = extract.first_paragraph(soup) or "A development kit for the Frequenz platform."
    installs = extract.find_install_instructions(soup) or ["python3 -m pip install frequenz-sdk"]
    features = extract.guess_features(sections)
    examples = extract.collect_code_examples(soup)

    # Platforms + links
    py_vers, os_name, arch = extract.parse_supported_platforms(readme_text)
    docs_link, pypi_link = extract.parse_links(readme_text)

    data = extract.build_jsonld(
        name=name,
        desc=desc,
        installs=installs,
        features=features,
        examples=examples,
        license_url="https://opensource.org/licenses/MIT",
        py_versions=py_vers or ["3.11", "3.12"],
    )
    if os_name:
        data["operatingSystem"] = os_name
    if arch:
        data["processorRequirements"] = arch
    if docs_link:
        data["documentation"] = docs_link
    if pypi_link:
        data["downloadUrl"] = pypi_link
    data["issueTracker"] = "https://github.com/frequenz-floss/frequenz-sdk-python/issues"

    # Add README sections
    works = extract.sections_to_creativeworks(sections)
    if works:
        data["hasPart"] = works

    return data


def chunks_from_v2(data: Dict) -> List[Dict]:
    chunks: List[Dict] = []
    # core fields
    if data.get("description"):
        chunks.append({"label": "purpose", "text": data["description"], "source": "readme"})
    install = data.get("installInstructions") or {}
    for s in install.get("step", []):
        t = s.get("text", "")
        if t:
            chunks.append({"label": "install", "text": t, "source": "readme"})
    for ex in data.get("exampleOfWork", []) or []:
        t = ex.get("text", "")
        if t:
            chunks.append({"label": "example", "text": t, "source": "readme"})
    feats = data.get("featureList", []) or []
    if feats:
        chunks.append({"label": "features", "text": "\n".join(map(str, feats)), "source": "readme"})
    lic = data.get("license")
    if lic:
        chunks.append({"label": "license", "text": str(lic), "source": "readme"})
    reqs = data.get("softwareRequirements", []) or []
    if reqs:
        chunks.append({"label": "dependencies", "text": "\n".join(map(str, reqs)), "source": "readme"})
    # sections
    for part in data.get("hasPart", []) or []:
        lbl = f"section:{part.get('name','section')}"
        txt = part.get("text", "")
        if txt:
            chunks.append({"label": lbl, "text": txt, "source": "section"})
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="Path to the repo snapshot TXT file")
    ap.add_argument("--out", default="project_knowledge_v2.jsonld")
    ap.add_argument("--chunks", default="advanced_chunks.jsonl")
    ap.add_argument("--dot", default="project_knowledge_v2.dot", help="Path to write Graphviz DOT")
    ap.add_argument("--svg", default=None, help="Optional path to write SVG (requires Graphviz 'dot')")
    args = ap.parse_args()

    files = parse_snapshot(Path(args.snapshot))
    v2 = build_v2_knowledge(files)
    Path(args.out).write_text(json.dumps(v2, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")

    # Write DOT (and optional SVG)
    nodes, edges = viz.build_nodes_edges(v2)
    viz.write_dot(nodes, edges, Path(args.dot))
    print(f"Wrote DOT to {args.dot}")
    if args.svg:
        ok = viz.dot_to_svg(Path(args.dot), Path(args.svg))
        if ok:
            print(f"Wrote SVG to {args.svg}")
        else:
            print("SVG export failed or Graphviz 'dot' not found.")

    chunks = chunks_from_v2(v2)
    if chunks:
        with Path(args.chunks).open("w", encoding="utf-8") as f:
            for ch in chunks:
                f.write(json.dumps(ch, ensure_ascii=False) + "\n")
        print(f"Wrote {args.chunks} ({len(chunks)} chunks)")


if __name__ == "__main__":
    main()
