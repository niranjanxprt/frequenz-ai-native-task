#!/usr/bin/env python3
"""
Advanced Streamlit app with AI-enhanced responses using:
- Perplexity Sonar API (real-time web search)
- OpenAI GPT-4 API  
- Google Gemini API
- Enhanced semantic search
- GitIngest repository analysis

Run:
  streamlit run app_advanced.py --server.port 8502
"""

import sys
from pathlib import Path
import json
from typing import Optional, List, Dict, Tuple
import glob
import streamlit as st
import time

# Add src directory to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
sys.path.insert(0, str(src_dir))

import query as q
import visualize as viz
# Note: Legacy AI integration was in a separate module, but
# the advanced app doesn't use it directly anymore.
# Removing the import avoids ModuleNotFoundError if the file is absent.

try:
    import query_advanced
    GITINGEST_AVAILABLE = True
except ImportError:
    GITINGEST_AVAILABLE = False


def initialize_session_state():
    """Initialize session state variables for API keys and settings"""
    if 'perplexity_api_key' not in st.session_state:
        st.session_state.perplexity_api_key = ''
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = ''
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = ''
    if 'preferred_ai' not in st.session_state:
        st.session_state.preferred_ai = 'perplexity'
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []


@st.cache_data(show_spinner=False)
def load_jsonld(path: Optional[str], uploaded_bytes: Optional[bytes]):
    if uploaded_bytes is not None:
        return json.loads(uploaded_bytes.decode("utf-8"))
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


def render_api_key_section():
    """Render the API key configuration section in sidebar"""
    st.sidebar.header("🤖 AI Configuration")
    
    # API Key inputs
    with st.sidebar.expander("🔑 API Keys", expanded=False):
        st.session_state.perplexity_api_key = st.text_input(
            "Perplexity API Key",
            value=st.session_state.get('perplexity_api_key', ''),
            type="password",
            help="Get your key from https://www.perplexity.ai/settings/api",
            key="perplexity_key_input"
        )
        
        st.session_state.openai_api_key = st.text_input(
            "OpenAI API Key", 
            value=st.session_state.get('openai_api_key', ''),
            type="password",
            help="Get your key from https://platform.openai.com/api-keys",
            key="openai_key_input"
        )
        
        st.session_state.gemini_api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get('gemini_api_key', ''),
            type="password", 
            help="Get your key from https://aistudio.google.com/app/apikey",
            key="gemini_key_input"
        )
    
    # Show API status
    st.sidebar.subheader("API Status")
    apis_configured = []
    
    if st.session_state.perplexity_api_key:
        st.sidebar.success("✅ Perplexity: Connected")
        apis_configured.append('perplexity')
    else:
        st.sidebar.warning("⚠️ Perplexity: No API key")
    
    if st.session_state.openai_api_key:
        st.sidebar.success("✅ OpenAI: Connected")
        apis_configured.append('openai')
    else:
        st.sidebar.warning("⚠️ OpenAI: No API key")
    
    if st.session_state.gemini_api_key:
        st.sidebar.success("✅ Gemini: Connected")
        apis_configured.append('gemini')
    else:
        st.sidebar.warning("⚠️ Gemini: No API key")
    
    # Preferred AI selection
    if apis_configured:
        st.session_state.preferred_ai = st.sidebar.selectbox(
            "Preferred AI",
            apis_configured,
            index=0 if apis_configured[0] == st.session_state.get('preferred_ai') else 0
        )
    
    return apis_configured


# Initialize session state
initialize_session_state()

# Page configuration
st.set_page_config(
    page_title="Frequenz SDK — AI-Enhanced Assistant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and header
st.title("🤖 Frequenz SDK — AI-Enhanced Assistant")
st.caption("Powered by Perplexity Sonar, OpenAI GPT-4, Gemini + GitIngest Repository Analysis")

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
    seen = set()
    ordered = []
    for p in logo_candidates:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    if ordered:
        st.image(ordered[0], width=180)

    st.header("Data Source")
    default_path = "project_knowledge.jsonld"  # use same as basic app
    st.caption(f"Using: gitingest (live repository analysis)")

data = (
    st.session_state.get("data")
    or load_jsonld(default_path, None)
)

col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Summary")
    if not data:
        st.info("Load or generate a JSON‑LD file to begin.")
    else:
        st.markdown(f"- Name: **{data.get('name', '')}**")
        st.markdown(f"- Description: {data.get('description', '')}")
        st.markdown(f"- License: `{data.get('license', '')}`")
        st.markdown(f"- Repository: `{data.get('codeRepository', '')}`")
        reqs = data.get("softwareRequirements", [])
        if reqs:
            st.markdown("- Requirements: " + ", ".join(f"`{r}`" for r in reqs))

with col2:
    st.subheader("Graph")
    if not data:
        st.empty()
    else:
        view = st.selectbox(
            "Graph view", ["Interactive (PyVis)", "Static (Graphviz DOT)"], index=0
        )
        nodes, edges = viz.build_nodes_edges(data)
        dot = viz.to_dot(nodes, edges)
        if view == "Interactive (PyVis)":
            try:
                from streamlit.components.v1 import html as st_html

                html = viz.to_pyvis_html(
                    data, height="650px", accent="#62B5B1", dark=True
                )
                st_html(html, height=600)
                st.download_button(
                    "Download interactive HTML",
                    html,
                    file_name="project_graph.html",
                    mime="text/html",
                )
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
                    st.markdown(
                        f"**Source section:** `{top['label'].split(':', 1)[1]}`"
                    )
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
                                st.markdown(
                                    f"  • section: `{r['label'].split(':', 1)[1]}`"
                                )
                            rtxt = r["text"]
                            if r["label"] == "example" or (
                                "def " in rtxt or "import " in rtxt
                            ):
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
                labels = [label for label, _ in docs]
                model = SentenceTransformer("all-MiniLM-L6-v2")
                embs = model.encode(texts) if texts else []
                return model, labels, texts, embs

            if st.button("Answer (MiniLM)"):
                model, labels, texts, embs = _get_minilm(
                    json.dumps(data, sort_keys=True)
                )
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
                        st.caption(
                            f"Similarity: {float(sims[i0]):.2f}  •  Label: {labels[i0]}"
                        )
                        t0 = texts[i0]
                        if labels[i0].startswith("section:"):
                            st.markdown(
                                f"**Source section:** `{labels[i0].split(':', 1)[1]}`"
                            )
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
                                    st.markdown(
                                        f"- {lbl} (score={float(sims[int(i)]):.2f}) — {texts[int(i)][:160]}…"
                                    )
                                    if lbl.startswith("section:"):
                                        st.markdown(
                                            f"  • section: `{lbl.split(':', 1)[1]}`"
                                        )

        except Exception:
            st.info(
                "sentence-transformers not installed. Enable with: pip install sentence-transformers (and torch)."
            )
