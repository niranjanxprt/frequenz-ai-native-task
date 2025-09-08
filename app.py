#!/usr/bin/env python3
"""
Streamlit app to:
- Load and visualize the JSON-LD graph produced by extract.py
- Answer natural-language questions using the query.py logic

Run:
  streamlit run app.py

If you don't have a JSON-LD yet, click "Extract JSON-LD" in the sidebar (needs network)
or run: python extract.py --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python --branch main
"""
from pathlib import Path
import json
from typing import Optional
import glob
import streamlit as st
import requests

import query as q
import visualize as viz


@st.cache_data(show_spinner=False)
def load_jsonld(path: Optional[str], uploaded_bytes: Optional[bytes]):
    if uploaded_bytes is not None:
        return json.loads(uploaded_bytes.decode("utf-8"))
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


st.set_page_config(page_title="Frequenz SDK — AI‑Native Graph", layout="wide")
st.title("Frequenz SDK — AI‑Native Knowledge Graph")
st.caption("Visualize the JSON‑LD and ask questions about the SDK")

# Accent styling for non-graph sections (keeps Graphviz neutral)
ACCENT = "#62B5B1"
st.markdown(
    f"""
    <style>
    :root {{ --accent: {ACCENT}; }}
    h1, h2, h3 {{ color: var(--accent) !important; }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: var(--accent) !important;
    }}
    .stButton>button {{
        border: 1px solid var(--accent) !important;
        background: var(--accent) !important;
        color: #0B1B1F !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {{
        border-color: var(--accent) !important;
    }}
    [data-baseweb="file-uploader"] {{
        border: 1px dashed var(--accent) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Extended UI accents beyond base theme
st.markdown(
    f"""
    <style>
    a, a:visited {{ color: var(--accent) !important; }}
    [data-baseweb=select] > div {{ border-color: var(--accent) !important; }}
    .stRadio > label, .stCheckbox > label {{ color: var(--accent) !important; }}
    .stSlider [data-baseweb=slider] div[data-testid=stTickBar] ~ div > div {{ background: var(--accent) !important; }}
    summary {{ color: var(--accent) !important; }}
    .stAlert > div {{ border-left: 4px solid var(--accent); }}
    pre code {{ border-left: 3px solid var(--accent); padding-left: 8px; display: block; }}
    ul li::marker {{ color: var(--accent); }}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    # Branding: show Frequenz logo if available or allow upload
    logo_candidates = []
    for ext in ("png", "jpg", "jpeg"):
        logo_candidates.extend(glob.glob(f"assets/*logo*.{ext}"))
        logo_candidates.extend(glob.glob(f"assets/*frequenz*.{ext}"))
        # also check repo root common names
        logo_candidates.extend(glob.glob(f"frequenz*logo*.{ext}"))
        logo_candidates.extend(glob.glob(f"*frequenz*.{ext}"))
    # Deduplicate while keeping order
    seen=set(); ordered=[]
    for p in logo_candidates:
        if p not in seen:
            seen.add(p); ordered.append(p)
    logo_path = ordered[0] if ordered else None
    if logo_path:
        st.image(logo_path, caption=None, width=180)
    else:
        up = st.file_uploader("Upload Frequenz logo (PNG/JPG)", type=["png", "jpg", "jpeg"], key="logo_up")
        if up is not None:
            st.image(up, caption=None, width=180)

    st.header("Data Source")
    default_path = "project_knowledge.jsonld"

    st.markdown("---")
    st.subheader("Extract JSON‑LD")
    repo_url = st.text_input(
        "Raw README URL (or GitHub /blob/ URL)",
        value="https://github.com/frequenz-floss/frequenz-sdk-python/blob/v1.x.x/README.md",
        help=(
            "Paste a full raw README URL (https://raw.githubusercontent.com/owner/repo/ref/README.md) "
            "or a GitHub web URL with /blob/ (it will be converted automatically)."
        ),
    )
    if st.button("Extract"):
        import extract

        try:
            ru = repo_url.strip()
            # Accept both github.com (with /blob/) and raw.githubusercontent.com
            if not (ru.startswith("https://raw.githubusercontent.com/") or ru.startswith("https://github.com/")):
                raise ValueError("URL must be a GitHub raw or web URL starting with https://raw.githubusercontent.com/ or https://github.com/.")
            md = extract.fetch_readme(ru)
            soup = extract.md_to_soup(md)
            sections = extract.extract_sections(soup)
            name = "Frequenz SDK for Python"
            desc = extract.first_paragraph(soup) or ""
            installs = extract.find_install_instructions(soup) or ["pip install frequenz-sdk"]
            features = extract.guess_features(sections)
            examples = extract.collect_code_examples(soup)
            jsonld = extract.build_jsonld(
                name,
                desc,
                installs,
                features,
                examples,
                "https://opensource.org/licenses/MIT",
                ["3.11", "3.12"],
            )
            Path(default_path).write_text(json.dumps(jsonld, indent=2), encoding="utf-8")
            st.session_state["data"] = jsonld
            st.success("Knowledge graph generated from README.")
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.info("Tip: Use the offline method below by uploading a README.md file.")

    # Removed offline README and JSON-LD upload to enforce a single-link workflow

    # Branding URL removed by request; local upload still supported above


data = st.session_state.get("data") or load_jsonld(default_path, None)

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
        nodes, edges = viz.build_nodes_edges(data)
        dot = viz.to_dot(nodes, edges)
        st.graphviz_chart(dot, use_container_width=True)

st.markdown("---")
st.subheader("Ask a question")
if not data:
    st.write("Load JSON‑LD first.")
else:
    # Show available embedded questions, if present
    embedded = [qobj.get("name", "") for qobj in (data.get("subjectOf") or []) if isinstance(qobj, dict) and qobj.get("@type") == "Question"]
    if embedded:
        st.caption("From JSON‑LD (FAQ):")
        sel = st.selectbox("Choose a question", options=[""] + embedded, index=0)
    else:
        sel = ""

    default_q = sel or "How do I install the sdk?"
    qtext = st.text_input("Your question", value=default_q)
    if st.button("Answer"):
        bucket = q.pick_bucket(qtext)
        ans = q.answer(data, bucket)
        st.caption(f"Bucket: {bucket}")
        if bucket == "example":
            st.code(ans, language="python")
        else:
            st.text(ans)
