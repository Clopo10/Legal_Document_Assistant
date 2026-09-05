"""
Streamlit Frontend: Legal Document Assistant
"""

import os
import requests
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Legal AI Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Remove Streamlit's default massive top padding safely
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 0rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

# 3. Environment & Directory Setup
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/analyze")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "sample_contracts"))

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("Settings")
    
    st.subheader("AI Engine")
    selected_model = st.selectbox(
        "Model Tier",
        options=["gemini-3.6-flash", "gemini-3.8-flash"]
    )
    
    st.divider()
    
    # Create an empty placeholder. We will inject the metrics here at the very end of the script!
    usage_placeholder = st.empty()
    
    st.divider()
    st.caption("Legal Assistant Capstone v2.0")


def get_contract_files():
    if not os.path.exists(DATA_DIR):
        return []
    return sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".txt")])


def load_contract_text(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def highlight_text(full_text, flagged_clauses):
    highlighted = full_text
    for clause in flagged_clauses:
        snippet = clause.get("original_text", "")
        risk = clause.get("risk_level", "HIGH")
        
        bg_color = "#fee2e2" if risk == "HIGH" else "#fef9c3"
        text_color = "#991b1b" if risk == "HIGH" else "#854d0e"
        border = "1px solid #f87171" if risk == "HIGH" else "1px solid #facc15"
        
        if snippet and snippet in highlighted:
            reason_escaped = clause.get("reason", "").replace('"', '&quot;')
            html_tag = (
                f'<mark style="background-color: {bg_color}; color: {text_color}; '
                f'border: {border}; font-weight: bold; padding: 2px 4px; '
                f'border-radius: 4px;" title="{reason_escaped}">{snippet}</mark>'
            )
            highlighted = highlighted.replace(snippet, html_tag)
    return highlighted



# ==============================================================================
# MAIN WORKSPACE
# ==============================================================================
st.title("Interactive Legal Document Assistant")

tab_demo, tab_upload, tab_history = st.tabs([
    "Demo Gallery", 
    "Custom Workspace", 
    "Compliance History"
])

# ------------------------------------------------------------------------------
# TAB 1: DEMO GALLERY
# ------------------------------------------------------------------------------
with tab_demo:
    available_contracts = get_contract_files()
    col1, col2 = st.columns([6, 4])
    
    with col2:
        st.subheader("Rule Configuration")
        
        # Native Streamlit container to prevent page scrolling
        with st.container(height=600):
            selected_file = st.selectbox(
                "Select a Contract:",
                options=available_contracts if available_contracts else ["No contracts found"],
                key="demo_select"
            )
            
            playbook_rule = st.text_area(
                "Legal Playbook Rule:",
                value="The governing law of the contract must be the State of Delaware.",
                key="demo_rule",
                height=100
            )
            
            analyze_button = st.button(
                "Analyze Contract", 
                type="primary", 
                use_container_width=True, 
                key="demo_btn"
            )
            
            raw_text = ""
            if available_contracts and selected_file in available_contracts:
                raw_text = load_contract_text(selected_file)
            
            if analyze_button:
                if not raw_text:
                    st.warning("Please select a valid contract file first.")
                else:
                    with st.spinner("Analyzing against legal playbook..."):
                        try:
                            payload = {
                                "filename": selected_file,
                                "contract_text": raw_text,
                                "playbook_rule": playbook_rule,
                                "model": selected_model
                            }
                            response = requests.post(BACKEND_URL, json=payload, timeout=60)
                            response.raise_for_status()
                            
                            data = response.json()
                            st.session_state.analysis_result = data
                            
                            st.session_state.total_tokens += data.get("input_tokens", 0) or 0
                            st.session_state.total_cost += data.get("estimated_cost_usd", 0.0) or 0.0
                            
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")
            
            result = st.session_state.analysis_result
            if result:
                st.divider()
                if result.get("is_compliant"):
                    st.success("Contract is fully compliant with the playbook.")
                else:
                    st.error("Non-Compliant Clauses Detected")
                    
                st.info(f"Summary: {result.get('summary')}")
                
                flagged = result.get("flagged_clauses", [])
                if flagged:
                    st.markdown(f"**Identified Violations ({len(flagged)}):**")
                    for clause in flagged:
                        title = clause.get("clause_title", "Flagged Clause")
                        with st.expander(title, expanded=True):
                            st.markdown(f"**Risk Level:** `{clause.get('risk_level', 'HIGH')}`")
                            st.markdown(f"**Reason:** {clause.get('reason', 'N/A')}")
                            st.markdown("**Proposed Redline:**")
                            st.markdown(clause.get("proposed_redline", "N/A"))
    
    with col1:
        st.subheader("Document Viewer")
        
        with st.container(height=600):
            if raw_text:
                display_text = raw_text
                if st.session_state.analysis_result:
                    display_text = highlight_text(
                        raw_text, 
                        st.session_state.analysis_result.get("flagged_clauses", [])
                    )
                
                display_text_html = display_text.replace("\n", "<br>")
                
                # Hardcoded white background and black text for dark mode compatibility
                st.markdown(
                    f"""
                    <div style="
                        background-color: #ffffff; 
                        color: #000000; 
                        padding: 20px; 
                        border-radius: 5px; 
                        border: 1px solid #ccc; 
                        font-family: sans-serif; 
                        font-size: 14px; 
                        line-height: 1.6;
                    ">
                        {display_text_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.info("Select a contract from the panel on the right to preview it.")

# ------------------------------------------------------------------------------
# TAB 2: CUSTOM WORKSPACE
# ------------------------------------------------------------------------------
with tab_upload:
    st.subheader("Upload a New Contract")
    st.write("Upload a .txt or .pdf contract. The backend will parse, chunk, and vectorize the document on the fly.")
    
    uploaded_file = st.file_uploader("Choose a file to analyze", type=["txt", "pdf"])
    if uploaded_file:
        st.info(f"File uploaded: {uploaded_file.name}. Vectorization endpoint coming next.")

# ------------------------------------------------------------------------------
# TAB 3: COMPLIANCE HISTORY
# ------------------------------------------------------------------------------
with tab_history:
    st.subheader("Compliance History Logs")
    st.write("Audit trail of historical contract analyses stored in the SQLite backend.")
    st.info("Database persistence integration coming next.")


# ==============================================================================
# INJECT SIDEBAR METRICS
# ==============================================================================
with usage_placeholder.container():
    st.subheader("Session Usage")
    st.metric(label="Tokens Processed", value=f"{st.session_state.total_tokens:,}")
    st.metric(label="Est. Enterprise Cost", value=f"${st.session_state.total_cost:.5f}")