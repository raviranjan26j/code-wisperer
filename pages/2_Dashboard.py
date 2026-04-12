import os
import streamlit as st

# 1. Guard: Ensure user has processed the repo
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

import git
from datetime import datetime

st.title("🌐 Repo Whisperer")

st.markdown("""
    <style>
    .fixed-nav {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 15px 20px;
        z-index: 9999;
        border-bottom: 1px solid #e6e9ef;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    .main-content { padding-top: 80px; }
    </style>
    """, unsafe_allow_html=True)

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="tertiary"):
            st.switch_page("app1.py")
    with col2:
        if st.button("📊 Dashboard", type="primary"):
            pass
    with col3:
        if st.button("🤖 Repo Chat", type="tertiary"):
            st.switch_page("pages/3_Chat.py")
    with col4:
        if st.button("⚙️ Settings", type="tertiary"):
            st.switch_page("pages/4_Settings.py")


def fetch_insights():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir) 
    
    repo_path = os.path.join(project_root, "temp_repo")

    # Check if path exists for debugging
    if not os.path.exists(repo_path):
        st.error(f"Could not find repository at: {repo_path}")
        print(f"DEBUG: Path does not exist: {repo_path}")
        return
    repo = git.Repo(repo_path)
    print(f"DEBUG: Found repository: {repo}")
    default_branch = repo.remotes.origin.refs.HEAD.reference.name.split('/')[-1]
    commits = list(repo.iter_commits(default_branch))
    contributors = set(c.author.name for c in commits)
    
    st.session_state.insights = {
        "total_commits": len(commits),
        "total_contributors": len(contributors),
        "active_branch": repo.active_branch.name,
        "last_commit": datetime.fromtimestamp(commits[0].committed_date).strftime('%Y-%m-%d')
    }

# 2. Repository Details (Directly in the page)
with st.container(border=True):
    st.subheader("📁 Repository Details")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Name:** {st.session_state.get('repo_name', 'N/A')}")
    col2.markdown(f"**Owner:** {st.session_state.get('repo_owner', 'N/A')}")
    col3.markdown(f"**Description:** {st.session_state.get('repo_description', 'N/A')}")

st.write("---")


if st.button("Fetch Insights", type="primary"):
    with st.spinner("Analyzing repository..."):
        fetch_insights()
        st.rerun()


# Display Insights if they have been fetched
if "insights" in st.session_state:
    data = st.session_state.insights
    st.subheader("📈 Repository Insights")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Commits", data["total_commits"])
    col2.metric("Contributors", data["total_contributors"])
    col3.metric("Last Commit", data["last_commit"])
    st.write(f"**Active Branch:** `{data['active_branch']}`")

else:
    st.info("Click 'Fetch Insights' to analyze the repository codebase.")

st.write("---")