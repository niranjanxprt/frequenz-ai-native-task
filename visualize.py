#!/usr/bin/env python3
"""
visualize.py
-------------
Create a simple graph visualization of the JSON-LD knowledge in project_knowledge.jsonld.

Outputs Graphviz DOT by default, and can optionally render to SVG if Graphviz's
`dot` binary is installed.

Usage:
  python visualize.py --in project_knowledge.jsonld --out project_knowledge.dot
  python visualize.py --format svg --out project_knowledge.svg

With Poetry:
  poetry run visualize --format svg --out project_knowledge.svg
"""
import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Optional


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\"", "\\\"")


def truncate(s: str, n: int = 60) -> str:
    s = s.strip()
    return (s[: n - 1] + "…") if len(s) > n else s


def build_nodes_edges(data: dict):
    nodes = []  # list of (id, label, attrs)
    edges = []  # list of (src, dst, label)

    root_id = "root"
    root_label = data.get("name", "Software")
    nodes.append((root_id, root_label, {"shape": "doubleoctagon"}))

    # Simple string fields
    for key, label in [
        ("applicationCategory", "category"),
        ("programmingLanguage", "language"),
        ("codeRepository", "codeRepository"),
        ("license", "license"),
    ]:
        val = data.get(key)
        if val:
            nid = key
            nodes.append((nid, str(val), {"shape": "box"}))
            edges.append((root_id, nid, label))

    # Author
    author = data.get("author")
    if isinstance(author, dict):
        nid = "author"
        nodes.append((nid, author.get("name", "Author"), {"shape": "ellipse"}))
        edges.append((root_id, nid, "author"))

    # Requirements
    reqs = data.get("softwareRequirements", []) or []
    for i, r in enumerate(reqs, 1):
        nid = f"req_{i}"
        nodes.append((nid, str(r), {"shape": "box"}))
        edges.append((root_id, nid, "requires"))

    # Features
    feats = data.get("featureList", []) or []
    for i, f in enumerate(feats, 1):
        nid = f"feat_{i}"
        nodes.append((nid, truncate(str(f), 50), {"shape": "note"}))
        edges.append((root_id, nid, "feature"))

    # Install instructions
    how = data.get("installInstructions") or {}
    if how:
        nid = "install"
        nodes.append((nid, how.get("name", "Install"), {"shape": "folder"}))
        edges.append((root_id, nid, "install"))
        for i, step in enumerate(how.get("step", []), 1):
            sid = f"step_{i}"
            nodes.append((sid, truncate(step.get("text", ""), 50), {"shape": "box"}))
            edges.append((nid, sid, f"step {i}"))

    # Examples
    exs = data.get("exampleOfWork", []) or []
    for i, ex in enumerate(exs, 1):
        eid = f"example_{i}"
        label = f"Example {i} ({ex.get('programmingLanguage','')})".strip()
        nodes.append((eid, label, {"shape": "component"}))
        edges.append((root_id, eid, "example"))

    # FAQ Questions
    faq = data.get("subjectOf", []) or []
    for i, q in enumerate(faq, 1):
        if not isinstance(q, dict) or q.get("@type") != "Question":
            continue
        qid = f"q_{i}"
        qlabel = q.get("name", f"Question {i}")
        nodes.append((qid, truncate(str(qlabel), 60), {"shape": "oval"}))
        edges.append((root_id, qid, "question"))
        ans = q.get("acceptedAnswer")
        if isinstance(ans, dict):
            aid = f"a_{i}"
            alabel = truncate(ans.get("text", ""), 60)
            nodes.append((aid, alabel, {"shape": "box"}))
            edges.append((qid, aid, "answer"))

    return nodes, edges


def read_streamlit_theme(config_path: str = ".streamlit/config.toml") -> Dict[str, str]:
    # Kept for compatibility, but unused when rendering default-styled graphs.
    return {}


def to_dot(nodes, edges, theme: Optional[Dict[str, str]] = None) -> str:
    def attrs_to_str(attrs: dict) -> str:
        if not attrs:
            return ""
        parts = [f"{k}=\"{esc(str(v))}\"" for k, v in attrs.items()]
        return " [" + ", ".join(parts) + "]"

    lines = [
        "digraph G {",
        "  rankdir=LR;",
        "  node [shape=box, style=rounded, fontsize=10];",
    ]
    for nid, label, attrs in nodes:
        lines.append(f"  {nid} [label=\"{esc(label)}\"]{attrs_to_str(attrs)};")
    for src, dst, label in edges:
        lines.append(f"  {src} -> {dst} [label=\"{esc(label)}\"];\n")
    lines.append("}")
    return "\n".join(lines)


def write_dot(nodes, edges, out_path: Path):
    out_path.write_text(to_dot(nodes, edges), encoding="utf-8")


def dot_to_svg(dot_path: Path, svg_path: Path) -> bool:
    try:
        cmd = ["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except FileNotFoundError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", default="project_knowledge.jsonld")
    ap.add_argument("--out", dest="out_path", default="project_knowledge.dot")
    ap.add_argument("--format", choices=["dot", "svg"], default="dot")
    args = ap.parse_args()

    data = json.loads(Path(args.in_path).read_text(encoding="utf-8"))
    nodes, edges = build_nodes_edges(data)

    out = Path(args.out_path)
    if args.format == "dot":
        write_dot(nodes, edges, out)
        print(f"Wrote DOT to {out}")
        return

    # For SVG, write DOT to a temp sibling and try converting with graphviz
    dot_path = out.with_suffix(".dot")
    write_dot(nodes, edges, dot_path)
    ok = dot_to_svg(dot_path, out)
    if ok:
        print(f"Wrote SVG to {out}")
    else:
        print("Graphviz 'dot' not found or failed. DOT was written to:", dot_path)


if __name__ == "__main__":
    main()
