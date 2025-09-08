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

with st.sidebar:
    # Branding: show Frequenz logo if available or allow upload
    logo_candidates = []
    for ext in ("png", "jpg", "jpeg"):
        logo_candidates.extend(glob.glob(f"assets/*logo*.{ext}"))
        logo_candidates.extend(glob.glob(f"assets/*frequenz*.{ext}"))
    logo_path = logo_candidates[0] if logo_candidates else None
    if logo_path:
        st.image(logo_path, caption=None, width=180)
    else:
        up = st.file_uploader("Upload Frequenz logo (PNG/JPG)", type=["png", "jpg", "jpeg"], key="logo_up")
        if up is not None:
            st.image(up, caption=None, width=180)

    st.header("Data Source")
    default_path = "project_knowledge.jsonld"
    path = st.text_input("JSON‑LD path", value=default_path)
    uploaded = st.file_uploader("…or upload JSON‑LD", type=["json", "jsonld"])  # optional override

    st.markdown("---")
    st.subheader("Extract JSON‑LD")
    repo_url = st.text_input(
        "Repo raw base URL",
        value="https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python",
        help="Raw GitHub base for the repo (no trailing slash for file)",
    )
    branch = st.text_input("Branch", value="main")
    if st.button("Extract from README.md"):
        import extract

        try:
            md = extract.fetch_readme(repo_url, branch)
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
            st.success(f"Wrote {default_path}")
        except Exception as e:
            st.error(f"Extraction failed: {e}")

    # Offline/local README extraction
    readme_up = st.file_uploader("Upload README.md for offline extraction", type=["md", "markdown"], key="readme_up")
    if st.button("Extract from uploaded README.md"):
        if readme_up is None:
            st.warning("Please upload a README.md file first.")
        else:
            import extract
            try:
                md = readme_up.read().decode("utf-8")
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
                st.success(f"Wrote {default_path} from uploaded README")
            except Exception as e:
                st.error(f"Local extraction failed: {e}")

    st.markdown("---")
    st.subheader("Branding")
    logo_url = st.text_input("Logo URL (optional)", value="")
    if st.button("Download logo to assets/") and logo_url:
        try:
            r = requests.get(logo_url, timeout=15)
            r.raise_for_status()
            assets_dir = Path("assets"); assets_dir.mkdir(parents=True, exist_ok=True)
            out = assets_dir / "frequenz-logo.png"
            out.write_bytes(r.content)
            st.success(f"Saved logo to {out}")
        except Exception as e:
            st.error(f"Logo download failed: {e}")


data = load_jsonld(path, uploaded.getvalue() if uploaded else None)

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
