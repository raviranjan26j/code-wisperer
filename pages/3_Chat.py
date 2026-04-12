import streamlit as st
import os
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")
from langchain_groq import ChatGroq
from neo4j import GraphDatabase

st.title("🌐 Repo Whisperer")

# Configuration (In production, use secrets)
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://55ec7d9e.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PWD = os.getenv("NEO4J_PWD")
api_key = os.getenv("GROQ_API_KEY")
model = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key, temperature=0)

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))

def retrieve_code(prompt):
    driver = get_driver()
    with driver.session() as session:
        # Note: Updated to use full-text index query
        query = 'CALL db.index.fulltext.queryNodes("code_index", $prompt) YIELD node, score RETURN node.name AS name, node.code AS code LIMIT 5'
        results = session.run(query, prompt=prompt).data()
    return results

st.markdown("""
    <style>
    /* Target the container holding the nav bar */
    div.fixed-nav {
        position: fixed;
        top: 0px;
        left: 0;
        width: 100%;
        background-color: white; /* Match your app theme */
        padding: 10px 20px;
        z-index: 1000; /* Ensure it stays above other content */
        border-bottom: 1px solid #ddd;
    }
    /* Add padding to the top of the main content so it isn't hidden by the bar */
    .stApp {
        padding-top: 80px;
    }
    </style>
    """, unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="fixed-nav">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="tertiary"):
            st.switch_page("app1.py")
    with col2:
        if st.button("📊 Dashboard", type="tertiary"):
            st.switch_page("pages/2_Dashboard.py")
    with col3:
        if st.button("🤖 Repo Chat", type="primary"):
            pass
    with col4:
        if st.button("⚙️ Settings", type="tertiary"):
            st.switch_page("pages/4_Settings.py")
    st.markdown('</div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
# 1. Create a container with fixed height to hold the messages
# This pushes everything below it to the bottom of this container
chat_container = st.container(height=350, border=True)
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])
# 2. This input will now appear at the bottom of the container above
if prompt := st.chat_input("Ask about your code..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)
        
    with st.spinner("Searching..."):
        retrieved = retrieve_code(prompt)
        context = "\n\n".join([f"Name: {r['name']}\nCode: {r['code']}" for r in retrieved]) if retrieved else "No code found."
        response = model.invoke(f"Context: {context}\nQuestion: {prompt}")
        
    with st.chat_message("assistant"): 
        st.markdown(response.content)
    st.session_state.messages.append({"role": "assistant", "content": response.content})
    
    # Rerun to update the chat_container
    st.rerun()