import streamlit as st
import os
from gitingest import ingest
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate

from ui_components import apply_custom_css, render_header, render_lottie_transparent, render_footer


# 1. Guard: Ensure user has processed the repo
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")


# Custom CSS for Background, Animations, and Typography
apply_custom_css()

render_header()
_spacer_col, _btn_col, _title_col, _spacer_col = st.columns([0.1, 2, 5, 2])
with _btn_col:
    st.markdown("<div style='padding-left: 20px;'>", unsafe_allow_html=True)
    if st.button("◀  Go to Dashboard", key="back_to_dashboard"):
        st.switch_page("pages/1_Dashboard_insights.py")
    st.markdown("</div>", unsafe_allow_html=True)
with _title_col:
    st.markdown("<h2 style='text-align: center; color: cornflowerblue;'>RepoTalk Chat</h2>", unsafe_allow_html=True)

if "repochat_messages" not in st.session_state:
    st.session_state.repochat_messages = []

# Initialize Vectorstore with Gitingest
if "vectorstore" not in st.session_state:
    loading_container = st.empty()
    with loading_container.container():
        st.markdown("<h4 style='text-align: center; color: #a0aab2; margin-bottom: -15px;'>Ingesting and analyzing repository structure...</h4>", unsafe_allow_html=True)
        render_lottie_transparent("assets/AI.json", height=200)
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        repo_path = os.path.join(project_root, "temp_repo")
        
        # Use gitingest on local directory
        exclude_patterns = {".claude", ".gitnexus", "AGENTS.md", "CLAUDE.md"}
        summary, tree, content = ingest(repo_path, exclude_patterns=exclude_patterns)

        print("Summary:", summary)
        print("Tree:", tree)
        print("Content:", content)
        
        # Batch string into chunks suitable for indexing
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
        combined_text = f"Repository Summary:\n{summary}\n\nRepository Structure:\n{tree}\n\nCodebase Files:\n{content}"
        chunks = text_splitter.split_text(combined_text)
        
        # Embed using local HF model
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        st.session_state.vectorstore = FAISS.from_texts(chunks, embeddings)
    except Exception as e:
        st.error(f"Error initializing RAG context: {e}")
            
    loading_container.empty()

col_spacer1, col_chat, col_spacer2 = st.columns([0.1, 9.8, 0.1])
with col_chat:
    # Display previously recorded messages

    chat_container = st.container(height=350, border=True)
    with chat_container:
        for msg in st.session_state.repochat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input & Invocation
    if prompt := st.chat_input("Ask me anything about the codebase structure or files..."):
        # Render user prompt
        st.session_state.repochat_messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # Retrieval generation


        with chat_container:


            thinking_placeholder = st.empty()


            with thinking_placeholder.container():


                with st.chat_message("assistant"):
                    anim_col, _ = st.columns([1, 9])
                    with anim_col:
                        render_lottie_transparent("assets/chat_thinking.json", height=50)
        try:
            llm = ChatNVIDIA(
                model="meta/llama-3.1-70b-instruct",
                api_key="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", 
                temperature=0.2,
                max_tokens=1024,
            )

            # Setup retriever to get top 5 chunks
            retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 5})

            system_prompt = (
                "You are 'RepoTalk', an AI assistant powered by Gitingest context to help developers "
                "analyze and understand their codebase based on the retrieved snippets below.\n"
                "Provide detailed, structured and accurate responses.\n\n"
                "Context Snippets:\n{context}"
            )

            prompt_tmpl = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain = (
                {"context": retriever | format_docs, "input": RunnablePassthrough()}
                | prompt_tmpl
                | llm
            )

            response = rag_chain.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)

        except Exception as e:
            answer = f"An error occurred while fetching the answer: {str(e)}"

        thinking_placeholder.empty()

        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(answer)

        st.session_state.repochat_messages.append({"role": "assistant", "content": answer})
        st.rerun()

render_footer()
