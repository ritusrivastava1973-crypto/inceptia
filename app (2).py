import streamlit as st
from pathlib import Path
import json
from utils import load_state

st.set_page_config(page_title="Market Mayhem", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
#MainMenu, header, footer { visibility: hidden; }
[data-testid="stSidebarNav"],[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stToolbar"],.stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# Ensure state file exists on cold start
load_state()

# Redirect to trade page
st.switch_page("pages/trade.py")
