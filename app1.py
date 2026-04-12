import streamlit as st
import os
import shutil
from git import Repo
from neo4j import GraphDatabase
from tree_sitter import Language, Parser
import tree_sitter_typescript, tree_sitter_javascript, tree_sitter_java, tree_sitter_html, tree_sitter_css, tree_sitter_python

# --- CONFIGURATION ---
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://55ec7d9e.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PWD = os.getenv("NEO4J_PWD")

# --- Session Management ---
if "processing_complete" not in st.session_state: st.session_state.processing_complete = False
if "repo_url" not in st.session_state: st.session_state.repo_url = ""

def get_parser(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {'.ts': tree_sitter_typescript.language_typescript(), '.tsx': tree_sitter_typescript.language_tsx(),
               '.js': tree_sitter_javascript.language(), '.jsx': tree_sitter_javascript.language(),
               '.java': tree_sitter_java.language(), '.html': tree_sitter_html.language(),
               '.css': tree_sitter_css.language(), '.py': tree_sitter_python.language()}
    return Parser(Language(mapping[ext])) if ext in mapping else None

def ingest_node(node, source_code, file_path, session, parent_uid=None):
    target_nodes = ['function_declaration', 'method_declaration', 'function_definition', 
                    'class_declaration', 'class_definition', 'arrow_function']
    
    current_node_uid = None
    
    if node.type in target_nodes:
        # 1. Create a stable, unique identifier for this node
        current_node_uid = f"{file_path}:{node.start_byte}"
        
        code_snippet = source_code[node.start_byte:node.end_byte].decode('utf8')
        name_node = node.child_by_field_name('name')
        name = source_code[name_node.start_byte:name_node.end_byte].decode('utf8') if name_node else "anonymous"
        
        # 2. Use the unique 'uid' property in MERGE
        session.run(
            """
            MERGE (c:CodeEntity {uid: $uid})
            SET c.name = $name, c.type = $type, c.file = $file, c.code = $code
            """, 
            uid=current_node_uid, name=name, type=node.type, file=file_path, code=code_snippet
        ).consume()
        
        # 3. Create the relationship using the UIDs
        if parent_uid is not None:
            session.run(
                """
                MATCH (p:CodeEntity {uid: $p_uid}), (c:CodeEntity {uid: $c_uid})
                MERGE (p)-[:CONTAINS]->(c)
                """, 
                p_uid=parent_uid, c_uid=current_node_uid
            ).consume()

    # Pass the current node UID as the parent for the recursive call
    next_parent = current_node_uid if current_node_uid is not None else parent_uid
    
    for child in node.children: 
        ingest_node(child, source_code, file_path, session, next_parent)

def run_pipeline(repo_url):
    temp_dir = "./temp_repo"
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    Repo.clone_from(repo_url, temp_dir)
    supported_files = [os.path.join(root, f) for root, _, files in os.walk(temp_dir) for f in files if get_parser(os.path.join(root, f))]
    
    total = len(supported_files)
    progress_bar = st.progress(0)
    status_text = st.empty()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
    with driver.session() as session:
        for i, full_path in enumerate(supported_files):
            parser = get_parser(full_path)
            with open(full_path, "rb") as f:
                code = f.read()
                tree = parser.parse(code)
                ingest_node(tree.root_node, code, full_path, session)
            progress_bar.progress((i + 1) / total)
            status_text.text(f"Processed {i+1}/{total}: {os.path.basename(full_path)}")
    driver.close()
    #if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
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
        with st.spinner("Extracting..."):
            run_pipeline(repo_url)
            st.session_state.processing_complete = True
            st.success("Extraction complete! Redirecting...")
            st.switch_page("pages/2_Dashboard.py")