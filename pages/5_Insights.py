import streamlit as st
import requests
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from datetime import date, timedelta
from collections import defaultdict
from ui_components import apply_custom_css, render_header, render_footer

if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

# Ensure LLM model initialization
def get_ai_reviewer():
    return ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",
        api_key="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", 
        temperature=0.2,
        top_p=0.7,
        max_completion_tokens=1024,
    )

st.set_page_config(page_title="Repo Insights", layout="wide")

# Apply custom CSS and render header
apply_custom_css()
render_header()

repo_owner = st.session_state.get("repo_owner")
repo_name = st.session_state.get("repo_name")

if not repo_owner or not repo_name or repo_owner == "Unknown":
    st.warning("Repository details are incomplete. Please start extraction from the Home page.")
    st.stop()

# Navigation row
_spacer, _btn_col1, _btn_col2 = st.columns([5.3, 1.1, 1.1])

with _btn_col1:
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/1_Dashboard_insights.py")
with _btn_col2:
    if st.button("💬 RepoTalk", use_container_width=True):
        st.switch_page("pages/7_Repo_Chat.py")

st.markdown(f"""
<div style="
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(100,149,237,0.25);
    border-radius: 16px;
    padding: 1rem 1.5rem;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 10px;
">
    <div style="font-size: 1.5rem;">📈</div>
    <div>
        <div style="font-size: 1.2rem; font-weight: 700; color: #fff;">Repository Insights</div>
        <div style="font-size: 0.9rem; color: cornflowerblue; font-weight: 600;">{repo_owner}/{repo_name}</div>
    </div>
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_pull_requests(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=5"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def fetch_pr_diff(owner, repo, pull_number):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    headers = {"Accept": "application/vnd.github.v3.diff"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    return ""

def generate_ai_review(diff: str) -> str:
    if not diff:
        return "Could not fetch diff for this Pull Request."
    
    # Truncate over-sized diffs to fit context limits roughly
    if len(diff) > 20000:
        diff = diff[:20000] + "\n...[TRUNCATED]"
        
    llm = get_ai_reviewer()
    system_prompt = (
        "You are an expert AI code reviewer. Your task is to analyze the following Git diff "
        "and suggest if any changes are required (e.g. identify syntax errors, logical bugs, "
        "security issues, or style improvements). "
        "If the diff looks completely fine and no changes are required, reply STRICTLY with 'no action needed'."
    )
    user_prompt = f"Diff:\n{diff}"
    
    try:
        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
        return response.content
    except Exception as e:
        return f"Error connecting to AI Provider: {e}"

from datetime import date, timedelta

# Helper to fetch commits
def fetch_commits_by_date(owner, repo, start, end):
    since_str = f"{start}T00:00:00Z"
    until_str = f"{end}T23:59:59Z"
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since_str}&until={until_str}&per_page=100"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def generate_release_notes(commits) -> str:
    if not commits:
        return "No commits provided."
        
    commit_texts = []
    for c in commits:
        # Extract the commit message and author name (handle missing author safely)
        msg = c.get('commit', {}).get('message', '').split('\n')[0]
        author = c.get('commit', {}).get('author', {}).get('name', 'Unknown')
        commit_texts.append(f"- {msg} (by {author})")
        
    commits_str = "\n".join(commit_texts)
    
    # Prune if there are way too many commits to avoid context length error
    if len(commits_str) > 20000:
        commits_str = commits_str[:20000] + "\n...[TRUNCATED]"
        
    llm = get_ai_reviewer()
    system_prompt = (
        "You are an expert technical writer and release manager. Your task is to review the following "
        "list of Git commits and generate a well-formatted Markdown Release Note. "
        "Categorize the commits logically (e.g., 'Features', 'Bug Fixes', 'Refactoring & Maintenance'). "
        "Summarize verbose commits and make it user-friendly. "
        "Start directly with the markdown formatted output."
    )
    user_prompt = f"Commits:\n{commits_str}"
    
    try:
        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
        return response.content
    except Exception as e:
        return f"Error connecting to AI Provider: {e}"

def generate_contributor_kudos(author: str, commits: list) -> str:
    if not commits:
        return "No commits provided."
        
    commits_str = "\n".join(commits)
    if len(commits_str) > 5000:
        commits_str = commits_str[:5000] + "\n...[TRUNCATED]"
        
    llm = get_ai_reviewer()
    system_prompt = (
        f"You are a supportive engineering manager. Your task is to write a short, personalized "
        f"'Kudos' and shoutout paragraph for the contributor named '{author}'. "
        f"Summarize their recent efforts based on the commit messages provided. "
        f"Keep the tone extremely uplifting, appreciative, and concise (2-3 sentences max). "
        f"Do not use greetings, output the paragraph directly."
    )
    user_prompt = f"Recent Commits by {author}:\n{commits_str}"
    
    try:
        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
        return response.content
    except Exception as e:
        return f"Error connecting to AI Provider: {e}"

tab1, tab2, tab3 = st.tabs(["Pull Requests Review", "Contributor Spotlight", "Release Notes Generator"])

with tab1:
    st.subheader("Latest Pull Requests")
    prs = fetch_pull_requests(repo_owner, repo_name)
    
    if not prs:
        st.info("No pull requests found or unable to fetch.")
    else:
        for pr in prs:
            with st.expander(f"#{pr['number']} - {pr['title']} ({pr['state']})", expanded=False):
                st.write(f"**Author:** {pr['user']['login']}")
                st.write(f"**Created At:** {pr['created_at']}")
                st.markdown(f"[View PR on GitHub]({pr['html_url']})")
                
                button_key = f"review_btn_{pr['number']}"
                
                if st.button("Review with AI", key=button_key):
                    with st.spinner("Analyzing PR Diff..."):
                        diff = fetch_pr_diff(repo_owner, repo_name, pr['number'])
                        if not diff:
                            st.error("No diff available or PR is empty.")
                        else:
                            review = generate_ai_review(diff)
                            st.markdown(f"""
                            <div class="info-card">
                                <h3>🤖 AI Review</h3>
                                <div style="color: #e0e1dd; font-size: 0.95rem;">{review}</div>
                            </div>
                            """, unsafe_allow_html=True)

with tab2:
    st.subheader("🏆 Contributor Spotlight")
    st.write("Recognize the most active contributors over a specified timeframe.")
    
    timeframe = st.selectbox("Timeframe", ["Last 7 Days", "Last 30 Days"], index=0)
    
    if st.button("Generate Spotlights", type="primary"):
        days = 7 if timeframe == "Last 7 Days" else 30
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()
        
        with st.spinner(f"Fetching commits for the {timeframe.lower()}..."):
            commits = fetch_commits_by_date(repo_owner, repo_name, start_date, end_date)
            
        if not commits:
            st.warning("No commits found in this timeframe.")
            st.session_state.spotlights = None
        else:
            author_commits = defaultdict(list)
            for c in commits:
                author_name = c.get('commit', {}).get('author', {}).get('name', 'Unknown')
                msg = c.get('commit', {}).get('message', '').split('\n')[0]
                author_commits[author_name].append(msg)
                
            sorted_authors = sorted(author_commits.items(), key=lambda item: len(item[1]), reverse=True)
            top_authors = sorted_authors[:3]
            
            spotlights = []
            for author_name, msgs in top_authors:
                with st.spinner(f"Generating Kudos for {author_name}..."):
                    kudos = generate_contributor_kudos(author_name, msgs)
                    spotlights.append({"author": author_name, "count": len(msgs), "kudos": kudos})
            
            st.session_state.spotlights = spotlights
            st.session_state.spotlight_meta = f"Analyzed {len(commits)} commits across {len(author_commits)} authors."
            
    if st.session_state.get("spotlights"):
        st.success(st.session_state.spotlight_meta)
        for s in st.session_state.spotlights:
            st.markdown(f"""
            <div class="info-card" style="margin-bottom: 1rem;">
                <h3>🌟 {s['author']} <span style="font-size: 0.9rem; color: #a0aab2; font-weight: 400;">({s['count']} commits)</span></h3>
                <p>{s['kudos']}</p>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.subheader("Automated Release Notes")
    st.write("Select a date range to generate a changelog from merged commits.")
    
    colA, colB = st.columns(2)
    with colA:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=14))
    with colB:
        end_date = st.date_input("End Date", value=date.today())
        
    if st.button("Fetch Commits & Generate Notes", type="primary"):
        with st.spinner("Fetching commits..."):
            commits = fetch_commits_by_date(repo_owner, repo_name, start_date, end_date)
            
        if not commits:
            st.warning("No commits found in the selected date range.")
            st.session_state.release_notes = None
        else:
            st.success(f"Successfully fetched {len(commits)} commits.")
            with st.spinner("Generating Release Notes with AI..."):
                st.session_state.release_notes = generate_release_notes(commits)
                
    if st.session_state.get("release_notes"):
        st.markdown("---")
        st.markdown(f"""
        <div class="info-card" style="margin-bottom: 1.5rem;">
            <h3>📦 Generated Release Notes</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.release_notes)
        
        st.download_button(
            label="📥 Download Release Notes",
            data=st.session_state.release_notes,
            file_name=f"release_notes_{start_date}_to_{end_date}.md",
            mime="text/markdown"
        )

st.write("---")
render_footer()
