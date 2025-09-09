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
try:
    import networkx as nx  # optional
except Exception:  # pragma: no cover
    nx = None
try:
    from pyvis.network import Network  # optional
except Exception:  # pragma: no cover
    Network = None


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
        ("documentation", "documentation"),
        ("downloadUrl", "download"),
        ("issueTracker", "issues"),
        ("operatingSystem", "os"),
        ("processorRequirements", "arch"),
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


def build_nx_graph(data: dict):
    """Construct a NetworkX directed graph from the JSON-LD structure.

    Nodes carry attributes: label, shape. Edges carry attribute: label.
    """
    if nx is None:
        raise ImportError("networkx is not installed")
    nodes, edges = build_nodes_edges(data)
    G = nx.DiGraph()
    for nid, label, attrs in nodes:
        G.add_node(nid, label=label, **attrs)
    for src, dst, label in edges:
        G.add_edge(src, dst, label=label)
    return G


def nx_basic_metrics(G) -> Dict[str, object]:
    if nx is None:
        return {"nodes": 0, "edges": 0}
    metrics: Dict[str, object] = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
    }
    try:
        indeg = sorted(G.in_degree(), key=lambda x: x[1], reverse=True)[:3]
        outdeg = sorted(G.out_degree(), key=lambda x: x[1], reverse=True)[:3]
        metrics["top_in_degree"] = indeg
        metrics["top_out_degree"] = outdeg
    except Exception:
        pass
    return metrics


def _palette(accent: str = "#62B5B1", dark: bool = True) -> Dict[str, Dict[str, str]]:
    """Return a color palette per node group with border/background/highlight.

    Designed for dark backgrounds by default.
    """
    # Core brand-inspired colors
    teal = accent  # main accent
    purple = "#8B2D6F"
    blue = "#5C7AEA"
    amber = "#E2B714"
    coral = "#FF7F6E"
    lime = "#A3E635"
    cyan = "#22D3EE"
    gray = "#9CA3AF"
    bg_dark = "#2D1726" if dark else "#FFFFFF"
    text = "#E6EAEB" if dark else "#0B1221"

    def c(border, background):
        return {
            "border": border,
            "background": background,
            "highlight": {"border": border, "background": background},
        }

    return {
        "_meta": {"bg": bg_dark, "text": text},
        "root": c(teal, "#143A3A" if dark else "#D1FAE5"),
        "meta": c(blue, "#0F1A3A" if dark else "#DBEAFE"),
        "repo": c(teal, "#0E2A2A" if dark else "#D1FAE5"),
        "license": c(amber, "#3A2A0F" if dark else "#FEF3C7"),
        "author": c(purple, "#2A0F1E" if dark else "#FCE7F3"),
        "requirement": c(cyan, "#082F35" if dark else "#CFFAFE"),
        "feature": c(lime, "#12290A" if dark else "#ECFCCB"),
        "install": c(coral, "#3A1712" if dark else "#FFE4E6"),
        "install_step": c(coral, "#3A1712" if dark else "#FFE4E6"),
        "example": c(blue, "#0F1A3A" if dark else "#DBEAFE"),
        "question": c(gray, "#1F2937" if dark else "#F3F4F6"),
        "answer": c(gray, "#111827" if dark else "#F3F4F6"),
        "edge": teal,
    }


def _node_group(nid: str) -> str:
    if nid == "root":
        return "root"
    if nid in {"applicationCategory", "programmingLanguage"}:
        return "meta"
    if nid == "codeRepository":
        return "repo"
    if nid == "license":
        return "license"
    if nid == "author":
        return "author"
    if nid.startswith("req_"):
        return "requirement"
    if nid.startswith("feat_"):
        return "feature"
    if nid == "install":
        return "install"
    if nid.startswith("step_"):
        return "install_step"
    if nid.startswith("example_"):
        return "example"
    if nid.startswith("q_"):
        return "question"
    if nid.startswith("a_"):
        return "answer"
    return "meta"


def to_pyvis_html(
    data: dict,
    height: str = "600px",
    width: str = "100%",
    accent: str = "#62B5B1",
    dark: bool = True,
) -> str:
    """Return an interactive HTML (PyVis/vis.js) for the graph.

    Requires pyvis. Raises ImportError if missing.
    """
    if Network is None:
        raise ImportError("pyvis is not installed")
    G = build_nx_graph(data)
    colors = _palette(accent=accent, dark=dark)
    net = Network(height=height, width=width, directed=True, notebook=False, bgcolor=colors["_meta"]["bg"], font_color=colors["_meta"]["text"])
    # Revert to a stable barnes_hut configuration that keeps nodes visible
    try:
        net.barnes_hut(gravity=-2000, central_gravity=0.3, spring_length=150, spring_strength=0.05, damping=0.09)
    except Exception:
        pass
    # Provide UI buttons to tweak physics/interaction
    try:
        net.show_buttons(filter_=["physics", "interaction", "layout"])
    except Exception:
        pass
    # Add nodes
    for nid, attrs in G.nodes(data=True):
        label = attrs.get("label", nid)
        shape = attrs.get("shape", "dot")
        # Map shapes roughly
        shape_map = {
            "doubleoctagon": "ellipse",
            "ellipse": "ellipse",
            "note": "box",
            "component": "box",
            "folder": "box",
            "box": "box",
            "oval": "ellipse",
        }
        group = _node_group(nid)
        color = colors.get(group, {"border": accent, "background": "#111827"})
        net.add_node(
            nid,
            label=label,
            title=f"{group}: {label}",
            shape=shape_map.get(shape, "dot"),
            color=color,
            widthConstraint={"maximum": 260},
        )
    # Add edges
    for u, v, attrs in G.edges(data=True):
        label = attrs.get("label", "")
        net.add_edge(u, v, label=label, color=colors["edge"], arrows="to", physics=True, smooth=True)
    # Generate HTML string
    html = net.generate_html()
    # Simple legend appended below the graph
    legend = """
    <div style='font-family: system-ui, -apple-system, Segoe UI, Roboto; font-size: 12px; margin-top: 8px;'>
      <strong>Legend</strong> — Root (teal), Meta/Repo/License/Author, Requirements (cyan), Features (lime), Install (coral), Example (blue), Q/A (gray)
    </div>
    """
    return html.replace("</body>", legend + "</body>")


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
