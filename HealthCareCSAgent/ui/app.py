import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="HealthCare CS Agent", page_icon="🏥", layout="wide")

st.title("🏥 HealthCare CS Agent")
st.markdown("Customer service platform for Healthcare SaaS")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("💬 Chat")
    st.markdown(
        "Talk to the AI agent — ask questions, search customers, "
        "check the knowledge base, or submit support requests."
    )
    st.page_link("pages/1_Chat.py", label="Open Chat", icon="💬")

with col2:
    st.subheader("📋 Triage Dashboard")
    st.markdown(
        "Submit support tickets for automatic triage, view the ticket queue, "
        "and track priority/category/team assignments."
    )
    st.page_link("pages/2_Triage_Dashboard.py", label="Open Dashboard", icon="📋")
