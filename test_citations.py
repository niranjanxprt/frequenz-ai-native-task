#!/usr/bin/env python3
"""
Simple test to verify citation functionality
"""

import streamlit as st
from streamlit.components.v1 import html

st.title("🧪 Citation Test")

st.markdown("Testing different approaches to clickable citations:")

# Test 1: HTML component
st.subheader("1. HTML Component Method")
test_url = "https://github.com/frequenz-floss/frequenz-sdk-python"
test_title = "Frequenz SDK for Python - GitHub"

button_html = f"""
<div style="text-align: center; padding: 20px;">
    <a href="{test_url}" target="_blank" style="
        display: inline-block;
        background: linear-gradient(135deg, #62B5B1, #4a9999);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        font-size: 1em;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    " onmouseover="this.style.background='linear-gradient(135deg, #4a9999, #62B5B1)';"
       onmouseout="this.style.background='linear-gradient(135deg, #62B5B1, #4a9999)';">
        🔗 Click to Open GitHub
    </a>
</div>
"""

try:
    html(button_html, height=80)
    st.success("✅ HTML component method loaded successfully")
except Exception as e:
    st.error(f"❌ HTML component failed: {e}")

# Test 2: Markdown method
st.subheader("2. Markdown Method")
st.markdown(f"**🔗 [Click here to open GitHub]({test_url})**")

# Test 3: st.link_button method (if available)
st.subheader("3. Link Button Method")
try:
    if hasattr(st, "link_button"):
        st.link_button("🔗 Open with Link Button", test_url)
        st.success("✅ link_button available and working")
    else:
        st.warning("⚠️ st.link_button not available in this Streamlit version")
except Exception as e:
    st.error(f"❌ link_button failed: {e}")

st.markdown("---")
st.info(
    "If any of the above methods work, citations should be clickable in the main app!"
)
