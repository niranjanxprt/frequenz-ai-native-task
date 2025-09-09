#!/usr/bin/env python3
"""
Streamlit app (advanced) — adds an optional MiniLM embeddings retriever
in addition to the baseline TF‑IDF semantic search. The rest of the UI
(extraction + graph views) mirrors app.py so you can run both versions.

Run:
  streamlit run app_advanced.py

Notes:
- MiniLM uses sentence-transformers (optional). If not installed, the
  tab explains how to enable it and still lets you use TF‑IDF.
- No dependency changes are required; this file guards imports.
"""
from pathlib import Path
import json
from typing import Optional, List, Dict, Tuple
import glob
import streamlit as st

import query as q
import visualize as viz


@st.cache_data(show_spinner=False)
def load_jsonld(path: Optional[str], uploaded_bytes: Optional[bytes]):
    if uploaded_bytes is not None:
        return json.loads(uploaded_bytes.decode("utf-8"))
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


st.set_page_config(page_title="Frequenz SDK — Advanced Semantic App", layout="wide")
st.title("Frequenz SDK — Advanced Semantic App (TF‑IDF + MiniLM)")
st.caption("Visualize the JSON‑LD, then ask questions using TF‑IDF or optional MiniLM embeddings")

# Accent styling for non-graph sections
ACCENT = "#62B5B1"
st.markdown(
    f"""
    <style>
    :root {{ --accent: {ACCENT}; }}
    h1, h2, h3 {{ color: var(--accent) !important; }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: var(--accent) !important; }}
    .stButton>button {{ border: 1px solid var(--accent) !important; background: var(--accent) !important; color: #0B1B1F !important; }}
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {{ border-color: var(--accent) !important; }}
    [data-baseweb="file-uploader"] {{ border: 1px dashed var(--accent) !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    # Logo discovery
    logo_candidates = []
    for ext in ("png", "jpg", "jpeg"):
        logo_candidates.extend(glob.glob(f"assets/*logo*.{ext}"))
        logo_candidates.extend(glob.glob(f"assets/*frequenz*.{ext}"))
        logo_candidates.extend(glob.glob(f"frequenz*logo*.{ext}"))
        logo_candidates.extend(glob.glob(f"*frequenz*.{ext}"))
    seen = set(); ordered = []
    for p in logo_candidates:
        if p not in seen:
            seen.add(p); ordered.append(p)
    if ordered:
        st.image(ordered[0], width=180)

    st.header("Data Source")
    default_path = "data/project_knowledge_v2.jsonld"  # advanced KG by default
    st.caption(f"Using: {default_path}")

data = st.session_state.get("data") or load_jsonld(default_path, None) or load_jsonld("project_knowledge.jsonld", None)

col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Summary")
    if not data:
        st.info("Load or generate a JSON‑LD file to begin.")
    else:
        st.markdown(f"- Name: **{data.get('name','')}**")
        st.markdown(f"- Description: {data.get('description','')}")
        st.markdown(f"- License: `{data.get('license','')}`")
        st.markdown(f"- Repository: `{data.get('codeRepository','')}`")
        reqs = data.get("softwareRequirements", [])
        if reqs:
            st.markdown("- Requirements: " + ", ".join(f"`{r}`" for r in reqs))

with col2:
    st.subheader("Graph")
    if not data:
        st.empty()
    else:
        view = st.selectbox("Graph view", ["Interactive (PyVis)", "Static (Graphviz DOT)"], index=0)
        nodes, edges = viz.build_nodes_edges(data)
        dot = viz.to_dot(nodes, edges)
        if view == "Interactive (PyVis)":
            try:
                from streamlit.components.v1 import html as st_html
                html = viz.to_pyvis_html(data, height="650px", accent="#62B5B1", dark=True)
                st_html(html, height=600)
                st.download_button("Download interactive HTML", html, file_name="project_graph.html", mime="text/html")
            except Exception as e:
                st.error(f"Interactive view unavailable: {e}. Falling back to static.")
                st.graphviz_chart(dot, use_container_width=True)
        else:
            st.graphviz_chart(dot, use_container_width=True)

st.markdown("---")
st.subheader("Summarize Repo")
if data:
    if st.button("Summarize Repo"):
        st.markdown("**Name:** " + data.get("name", ""))
        desc = data.get("description", "")
        if desc:
            st.markdown(desc)
        # Install summary
        how = data.get("installInstructions", {})
        steps = [s.get("text", "") for s in how.get("step", [])]
        if steps:
            st.markdown("**Install:**\n- " + "\n- ".join(steps))
        # Features if any
        feats = data.get("featureList", [])
        if feats:
            st.markdown("**Key features:**\n- " + "\n- ".join(map(str, feats[:5])))
        # Platforms
        reqs = data.get("softwareRequirements", [])
        osn = data.get("operatingSystem")
        arch = data.get("processorRequirements")
        lines = []
        if reqs:
            lines.append("Python: " + ", ".join(reqs))
        if osn:
            lines.append("OS: " + osn)
        if arch:
            lines.append("Architectures: " + arch)
        if lines:
            st.markdown("**Supported platforms:**\n- " + "\n- ".join(lines))
        # Links
        links = []
        if data.get("documentation"):
            links.append(f"Docs: {data['documentation']}")
        if data.get("downloadUrl"):
            links.append(f"PyPI: {data['downloadUrl']}")
        if data.get("issueTracker"):
            links.append(f"Issues: {data['issueTracker']}")
        if links:
            st.markdown("**Links:**\n- " + "\n- ".join(links))
        # Example snippet
        exs = data.get("exampleOfWork", [])
        if exs:
            st.markdown("**Example:**")
            st.code(exs[0].get("text", ""), language="python")
tabs = st.tabs(["Semantic (TF‑IDF)", "Semantic (MiniLM)"])

def _build_chunks(payload: Dict) -> List[Tuple[str, str]]:
    docs: List[Tuple[str, str]] = []
    desc = payload.get("description")
    if desc:
        docs.append(("purpose", desc))
    install = payload.get("installInstructions") or {}
    steps = install.get("step") or []
    if steps:
        docs.append(("install", "\n".join(s.get("text", "") for s in steps)))
    exs = payload.get("exampleOfWork", [])
    if exs:
        docs.append(("example", exs[0].get("text", "")))
    feats = payload.get("featureList", [])
    if feats:
        docs.append(("features", "\n".join(map(str, feats))))
    lic = payload.get("license")
    if lic:
        docs.append(("license", str(lic)))
    reqs = payload.get("softwareRequirements", [])
    if reqs:
        docs.append(("dependencies", "\n".join(map(str, reqs))))
    # Add section-level chunks
    parts = payload.get("hasPart", []) or []
    for part in parts:
        name = str(part.get("name", "section")).strip()
        text = str(part.get("text", "")).strip()
        if text:
            docs.append((f"section:{name}", text))
    return docs


# Tab 1 — TF‑IDF
with tabs[0]:
    if not data:
        st.info("Load or generate a JSON‑LD file to begin.")
    else:
        default_q = "How do I install the sdk?"
        qtext = st.text_input("Your question", value=default_q, key="q_fast")
        topk = st.slider("Results", 1, 5, 3, key="k_fast")

        @st.cache_resource(show_spinner=False)
        def _get_retriever(payload_json: str):
            return q.TfidfRetriever.from_data(json.loads(payload_json))

        if st.button("Answer (TF‑IDF)"):
            try:
                retriever = _get_retriever(json.dumps(data, sort_keys=True))
                results = retriever.search(qtext, top_k=topk)
            except Exception:
                results = q.retrieve_semantic(qtext, data, top_k=topk)
            if not results:
                st.error("No relevant content found.")
            else:
                top = results[0]
                st.caption(f"Match: {top['label']} (score={top['score']:.2f})")
                if top["label"].startswith("section:"):
                    st.markdown(f"**Source section:** `{top['label'].split(':',1)[1]}`")
                txt = top["text"]
                if top["label"] == "example" or ("def " in txt or "import " in txt):
                    st.code(txt, language="python")
                    if st.button("Summarize code", key="sum_fast"):
                        st.markdown(_summarize_code(txt))
                else:
                    st.text(txt)
                if len(results) > 1:
                    with st.expander("Other relevant snippets"):
                        for r in results[1:]:
                            st.markdown(f"- {r['label']} (score={r['score']:.2f})")
                            if r["label"].startswith("section:"):
                                st.markdown(f"  • section: `{r['label'].split(':',1)[1]}`")
                            rtxt = r["text"]
                            if r["label"] == "example" or ("def " in rtxt or "import " in rtxt):
                                st.code(rtxt, language="python")
                            else:
                                st.text(rtxt)


# Tab 2 — MiniLM (optional)
with tabs[1]:
    if not data:
        st.info("Load or generate a JSON‑LD file to begin.")
    else:
        default_q2 = "What is the Frequenz SDK for?"
        qtext2 = st.text_input("Your question", value=default_q2, key="q_trf")
        topk2 = st.slider("Results", 1, 5, 3, key="k_trf")

        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity

            @st.cache_resource(show_spinner=True)
            def _get_minilm(payload_json: str):
                payload = json.loads(payload_json)
                docs = _build_chunks(payload)
                texts = [t for _, t in docs]
                labels = [l for l, _ in docs]
                model = SentenceTransformer('all-MiniLM-L6-v2')
                embs = model.encode(texts) if texts else []
                return model, labels, texts, embs

            if st.button("Answer (MiniLM)"):
                model, labels, texts, embs = _get_minilm(json.dumps(data, sort_keys=True))
                if not texts:
                    st.error("No content to search.")
                else:
                    qv = model.encode([qtext2])
                    sims = cosine_similarity(qv, embs)[0]
                    order = sims.argsort()[::-1][:topk2]
                    if len(order) == 0:
                        st.warning("No semantic results.")
                    else:
                        i0 = int(order[0])
                        st.caption(f"Similarity: {float(sims[i0]):.2f}  •  Label: {labels[i0]}")
                        t0 = texts[i0]
                        if labels[i0].startswith("section:"):
                            st.markdown(f"**Source section:** `{labels[i0].split(':',1)[1]}`")
                        if labels[i0] == "example" or ("def " in t0 or "import " in t0):
                            st.code(t0, language="python")
                            if st.button("Summarize code", key="sum_trf"):
                                st.markdown(_summarize_code(t0))
                        else:
                            st.text(t0)
                        if len(order) > 1:
                            with st.expander("Other relevant matches"):
                                for i in order[1:]:
                                    lbl = labels[int(i)]
                                    st.markdown(f"- {lbl} (score={float(sims[int(i)]):.2f}) — {texts[int(i)][:160]}…")
                                    if lbl.startswith("section:"):
                                        st.markdown(f"  • section: `{lbl.split(':',1)[1]}`")
                                
        except Exception:
            st.info("sentence-transformers not installed. Enable with: pip install sentence-transformers (and torch).")


def _summarize_code(code: str) -> str:
    """Heuristic code summary: imports, function defs, SDK keywords, line count."""
    lines = [ln.rstrip() for ln in code.splitlines()]
    import re
    imports = [ln for ln in lines if ln.strip().startswith("import ") or ln.strip().startswith("from ")]
    defs = [ln.strip() for ln in lines if re.match(r"^(async\s+def|def)\s+", ln.strip())]
    sdk_refs = sorted(set([w for w in ["frequenz", "microgrid", "initialize", "ResamplerConfig", "receiver", "asyncio"] if w in code]))
    bullets = [
        f"- Lines: {len(lines)}",
        f"- Imports: {', '.join(imports[:5])}{'…' if len(imports) > 5 else ''}" if imports else "- Imports: none",
        f"- Functions: {', '.join(defs[:3])}{'…' if len(defs) > 3 else ''}" if defs else "- Functions: none",
        f"- SDK refs: {', '.join(sdk_refs)}" if sdk_refs else "- SDK refs: none",
    ]
    return "\n".join(["**Code summary**:"] + bullets)
