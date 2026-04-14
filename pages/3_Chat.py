import streamlit as st
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_nvidia_ai_endpoints import ChatNVIDIA

st.title("🌐 Repo Whisperer")

async def get_repo_data(prompt):
    print("Starting MCP client...")
    client = MultiServerMCPClient(
        {
            "gitnexus": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "gitnexus", "mcp"]
            }
        }
    )
    print("MCP client started...")

    tools = await client.get_tools()
    print("Tools fetched...")
 
    client = ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",
        api_key="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", 
        temperature=0.2,
        top_p=0.7,
        max_completion_tokens=1024,
    )   

    agent = create_agent(
        client,   # or claude
        tools
    )
    print("Agent created...")

    system_prompt = """
    You are a helpful assistant. Use temp_repo as the repository name.
    """

    result = await agent.ainvoke({
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    })
    print("Result fetched...")

    return result['messages'][-1].content

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
chat_container = st.container(height=350, border=True)
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])
if prompt := st.chat_input("Ask about your code..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)
    with st.spinner("Searching..."):
        retrieved = asyncio.run(get_repo_data(prompt))
        print(f"Retrieved: {retrieved}")
    with st.chat_message("assistant"): 
        st.markdown(retrieved)
    st.session_state.messages.append({"role": "assistant", "content": retrieved})
    st.rerun()
