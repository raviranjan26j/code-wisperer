import streamlit as st
import os
import subprocess
import shutil
from git import Repo
from datetime import datetime

# --- Session Management ---
if "processing_complete" not in st.session_state: st.session_state.processing_complete = False
if "repo_url" not in st.session_state: st.session_state.repo_url = ""

def run_pipeline(repo_url):
    temp_dir = "./temp_repo"
    st.session_state.temp_dir = temp_dir
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    with st.spinner(" Extracting Repository..."):
        Repo.clone_from(repo_url, temp_dir)

    # run gitnexus analyze
    with  st.spinner("Analyzing Repository..."):
        subprocess.run(["npx", "--y", "gitnexus", "analyze"], cwd=temp_dir)
        st.session_state.repo_name = os.path.basename(repo_url.rstrip('/'))
        st.session_state.repo_owner = repo_url.split('/')[-2] if '/' in repo_url else "Unknown"
        readme_path = os.path.join(temp_dir, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                st.session_state.repo_description = f.read(100) + "..."
        else:
            st.session_state.repo_description = "No description provided."
        st.session_state.processing_complete = True

st.set_page_config(page_title="Repo Whisperer", layout="wide", initial_sidebar_state="collapsed")
st.title("🌐 Repo Whisperer")
# nav bar
with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="primary"):
            pass
    with col2:
        if st.button("📊 Dashboard", type="tertiary"):
            st.switch_page("pages/2_Dashboard.py")
    with col3:
        if st.button("🤖 Repo Chat", type="tertiary"):
            st.switch_page("pages/3_Chat.py")
    with col4:
        if st.button("⚙️ Settings", type="tertiary"):
            st.switch_page("pages/4_Settings.py")

if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""
repo_url = st.text_input("GitHub URL", 
    value=st.session_state.repo_url, 
    key="input_repo_url")
st.session_state.repo_url = repo_url

if st.button("🚀 Start Extraction"):
    if repo_url:
        run_pipeline(repo_url)
        st.session_state.processing_complete = True
        st.success("Extraction complete! Redirecting...")
        st.switch_page("pages/2_Dashboard.py")
