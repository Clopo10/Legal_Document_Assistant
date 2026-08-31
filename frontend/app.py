"""
Streamlit Frontend: Legal Document Assistant
--------------------------------------------
Provides a split-screen UI. 
Left: The raw contract text with dynamic CSS highlighting.
Right: The AI analysis controls and results.
"""

import streamlit as st
import requests
import os

# 1. Page Configuration (Must be wide for split-screen)
st.set_page_config(page_title="Legal AI Assistant", layout="wide")
st.title("Legal Document Assistant")

# 2. Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/analyze")
# Path to our local test contracts
DATA_DIR = "../data/sample_contracts"

def get_contract_files():
    """Fetches the list of downloaded CUAD test contracts."""
    if not os.path.exists(DATA_DIR):
        return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".txt")]

def load_contract_text(filename):
    """Loads the raw text of the selected contract."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def highlight_text(full_text, flagged_clauses):
    """
    The Highlighting Engine:
    Finds the exact 'original_text' returned by the LLM inside the full contract
    and wraps it in HTML <mark> tags for visual emphasis.
    """
    highlighted_text = full_text
    
    for clause in flagged_clauses:
        snippet = clause.get("original_text", "")
        risk = clause.get("risk_level", "HIGH")
        
        # Pick color based on risk severity
        color = "#ffcccc" if risk == "HIGH" else "#fff0b3" # Red or Yellow
        
        if snippet and snippet in highlighted_text:
            # HTML wrap the exact substring
            html_tag = f'<mark style="background-color: {color}; font-weight: bold; padding: 2px; border-radius: 3px;" title="{clause.get("reason")}">{snippet}</mark>'
            highlighted_text = highlighted_text.replace(snippet, html_tag)
            
    return highlighted_text

# 3. Build the UI Layout (Split Screen)
# col1 gets 60% of the screen (Document), col2 gets 40% (AI Chat)
col1, col2 = st.columns([6, 4])

# --- RIGHT PANEL: AI CONTROLS ---
with col2:
    st.subheader("AI Chat")
    
    # Dropdown to select a contract
    available_contracts = get_contract_files()
    selected_file = st.selectbox("Select a Contract to Review:", available_contracts)
    
    # Text input for the legal playbook rule
    playbook_rule = st.text_area(
        "Legal Playbook Rule:", 
        value="The governing law of the contract must be the State of Delaware."
    )
    
    analyze_button = st.button("Analyze Contract", type="primary", use_container_width=True)

# Load the text based on the dropdown selection
if available_contracts and selected_file:
    raw_text = load_contract_text(selected_file)
else:
    raw_text = "No contracts found. Please run the download script."

# Session state to hold our analysis results so they don't disappear on screen refresh
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# --- ACTION LOGIC: WHEN BUTTON IS CLICKED ---
if analyze_button:
    with col2:
        with st.spinner("Analyzing against legal playbook..."):
            try:
                # Send the request to our FastAPI backend
                payload = {
                    "filename": selected_file,
                    "contract_text": raw_text,
                    "playbook_rule": playbook_rule
                }
                response = requests.post(BACKEND_URL, json=payload)
                response.raise_for_status() # Raise error if backend fails
                
                # Save the JSON response to session state
                st.session_state.analysis_result = response.json()
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to Backend.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- LEFT PANEL: DOCUMENT VIEWER ---
with col1:
    st.subheader("Document Viewer")
    
    display_text = raw_text
    
    # If we have an analysis result, apply the highlights!
    if st.session_state.analysis_result:
        flagged = st.session_state.analysis_result.get("flagged_clauses", [])
        display_text = highlight_text(raw_text, flagged)
        
   # Convert newlines to HTML breaks so Streamlit doesn't create scrollable code blocks
    display_text_html = display_text.replace('\n', '<br>')

    st.markdown(
        f'<div style="height: 700px; overflow-y: scroll; padding: 20px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; color: #333; white-space: pre-wrap; font-family: sans-serif;">{display_text_html}</div>', 
        unsafe_allow_html=True
    )

# --- RIGHT PANEL: DISPLAY RESULTS ---
with col2:
    result = st.session_state.analysis_result
    if result:
        st.divider()
        
        # Status Banner
        if result.get("is_compliant"):
            st.success("Contract is fully compliant with the playbook.")
        else:
            st.error("Non-Compliant Clauses Detected")
            
        st.info(f"**Summary:** {result.get('summary')}")
        
        # Display the flagged clauses
        for i, clause in enumerate(result.get("flagged_clauses", [])):
            with st.expander(f"{clause.get('clause_title', 'Unknown Clause')}", expanded=True):
                st.markdown(f"**Risk Level:** `{clause.get('risk_level')}`")
                st.markdown(f"**Reason:** {clause.get('reason')}")
                st.markdown("**Proposed Redline:**")
                st.markdown(clause.get("proposed_redline"))
        
        # Display engineering metrics (Great for capstone defense)
        st.caption(
            f"Latency: {result.get('latency_seconds')}s | "
            f"Est. Cost: ${result.get('estimated_cost_usd'):.5f}"
        )