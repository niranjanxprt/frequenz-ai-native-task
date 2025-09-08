"""
branding.py
-----------
Streamlit UI helpers to apply Frequenz-like branding with accent colors and a hero header.

Usage:
  import branding
  branding.inject_branding()
"""
from __future__ import annotations

import streamlit as st


def inject_branding(
    primary: str = "#10D0B0",  # teal accent from site/brand
    secondary: str = "#8B2D6F",  # magenta/purple accent from site hero
    bg_dark: str = "#0B1221",
    bg_panel: str = "#16202F",
    text: str = "#E6F4F1",
):
    css = f"""
    <style>
    :root {{
      --brand-primary: {primary};
      --brand-secondary: {secondary};
      --brand-bg: {bg_dark};
      --brand-panel: {bg_panel};
      --brand-text: {text};
    }}
    /* Primary button + widgets */
    .stButton>button {{
      background: var(--brand-primary) !important;
      color: #0b1b1f !important;
      border: none !important;
    }}
    .stButton>button:hover {{ filter: brightness(0.95); }}

    /* Hero header */
    .brand-hero {{
      padding: 18px 16px; margin: 0 0 12px 0; border-radius: 8px;
      background: linear-gradient(110deg, rgba(16,208,176,0.18), rgba(139,45,111,0.22));
      border: 1px solid rgba(255,255,255,0.06);
    }}
    .brand-title {{ font-size: 1.15rem; font-weight: 600; color: var(--brand-text); margin: 0; }}
    .brand-sub {{ font-size: 0.9rem; color: #cbe6e2; margin-top: 2px; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def hero(title: str, subtitle: str | None = None):
    with st.container():
        st.markdown(
            f"<div class='brand-hero'><div class='brand-title'>{title}</div>"
            + (f"<div class='brand-sub'>{subtitle}</div>" if subtitle else "")
            + "</div>",
            unsafe_allow_html=True,
        )

