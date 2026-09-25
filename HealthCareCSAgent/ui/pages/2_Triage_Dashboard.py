import streamlit as st
import boto3
import json
import uuid
import os
import re
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ticket Triage Dashboard", page_icon="📋", layout="wide")

REGION = os.getenv("AWS_REGION", "us-west-2")
RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
TABLE_NAME = os.getenv("TICKET_TABLE", "HealthCareCS-Tickets")

PRIORITY_COLORS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

CATEGORY_ICONS = {
    "billing": "💳",
    "clinical": "🏥",
    "technical": "🔧",
    "compliance": "📜",
    "account": "👤",
}


@st.cache_resource
def get_dynamo_table():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


@st.cache_resource
def get_agent_client():
    return boto3.client("bedrock-agentcore", region_name=REGION)


def invoke_agent(client, prompt: str, session_id: str) -> str:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": prompt}).encode(),
        runtimeSessionId=session_id,
    )
    stream = response.get("response")
    if stream is None:
        return "No response from agent."

    content = stream.read()
    raw = content.decode() if isinstance(content, bytes) else content

    text_parts = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("event:") or line.startswith(":"):
            continue
        data_str = line.removeprefix("data:").strip()
        if not data_str:
            continue
        try:
            data = json.loads(data_str)
            text = data.get("event", {}).get("contentBlockDelta", {}).get("delta", {}).get("text")
            if text:
                text_parts.append(text)
        except json.JSONDecodeError:
            pass

    return "".join(text_parts) if text_parts else raw


def load_tickets():
    table = get_dynamo_table()
    try:
        response = table.scan(Limit=100)
        tickets = response.get("Items", [])
        tickets.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tickets
    except Exception:
        return []


st.title("📋 Ticket Triage Dashboard")

tab_submit, tab_queue = st.tabs(["Submit Ticket", "Ticket Queue"])

# --- Submit Ticket Tab ---
with tab_submit:
    st.subheader("Submit a new support request")
    st.markdown("The agent will automatically classify, prioritise, and route your ticket.")

    with st.form("ticket_form"):
        col1, col2 = st.columns(2)
        with col1:
            sender_name = st.text_input("Your name", placeholder="e.g. Karen Liu")
            sender_email = st.text_input("Email", placeholder="e.g. karen.liu@pilbaramining.com.au")
        with col2:
            sender_org = st.text_input("Organisation", placeholder="e.g. Pilbara Mining Corp")
            customer_id = st.text_input("Customer ID (if known)", placeholder="e.g. C-1003")

        subject = st.text_input("Subject", placeholder="e.g. Drug testing results delayed for FIFO crew")
        body = st.text_area(
            "Description",
            height=150,
            placeholder="Describe your issue in detail...",
        )

        submitted = st.form_submit_button("Submit & Triage", type="primary", use_container_width=True)

    if submitted:
        if not subject or not body:
            st.error("Subject and description are required.")
        else:
            triage_prompt = (
                f"Triage this incoming support ticket. Classify it and create a ticket.\n\n"
                f"FROM: {sender_name or 'Unknown'} ({sender_email or 'no email'})\n"
                f"ORG: {sender_org or 'Unknown'}\n"
                f"CUSTOMER ID: {customer_id or 'not provided'}\n"
                f"SUBJECT: {subject}\n\n"
                f"BODY:\n{body}\n\n"
                f"Instructions: Search for this customer if an ID or org is provided. "
                f"Check the knowledge base for relevant context. "
                f"Then classify and create the ticket using triage_and_create_ticket. "
                f"Report the triage result."
            )

            with st.spinner("Agent is triaging your ticket..."):
                client = get_agent_client()
                session_id = str(uuid.uuid4())
                try:
                    response = invoke_agent(client, triage_prompt, session_id)
                    cleaned = re.sub(r"</?thinking>", "", response).strip()

                    ticket_match = re.search(r"TKT-[A-Z0-9]{8}", cleaned)
                    if ticket_match:
                        st.success(f"Ticket created: **{ticket_match.group()}**")
                    else:
                        st.success("Ticket triaged successfully!")

                    st.markdown("### Agent Response")
                    st.markdown(cleaned)
                except Exception as e:
                    st.error(f"Triage failed: {e}")

# --- Ticket Queue Tab ---
with tab_queue:
    st.subheader("Current ticket queue")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_status = st.selectbox("Status", ["all", "open", "in_progress", "resolved", "closed"])
    with col_f2:
        filter_priority = st.selectbox("Priority", ["all", "critical", "high", "medium", "low"])
    with col_f3:
        filter_category = st.selectbox("Category", ["all", "billing", "clinical", "technical", "compliance", "account"])
    with col_f4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    tickets = load_tickets()

    if filter_status != "all":
        tickets = [t for t in tickets if t.get("status") == filter_status]
    if filter_priority != "all":
        tickets = [t for t in tickets if t.get("priority") == filter_priority]
    if filter_category != "all":
        tickets = [t for t in tickets if t.get("category") == filter_category]

    # Stats row
    if tickets:
        s1, s2, s3, s4 = st.columns(4)
        open_count = sum(1 for t in tickets if t.get("status") == "open")
        critical_count = sum(1 for t in tickets if t.get("priority") == "critical")
        escalated_count = sum(1 for t in tickets if t.get("escalate"))
        s1.metric("Total Shown", len(tickets))
        s2.metric("Open", open_count)
        s3.metric("Critical", critical_count)
        s4.metric("Escalated", escalated_count)

    st.divider()

    if not tickets:
        st.info("No tickets found. Submit one above or adjust filters.")
    else:
        for ticket in tickets:
            priority = ticket.get("priority", "medium")
            category = ticket.get("category", "general")
            p_icon = PRIORITY_COLORS.get(priority, "⚪")
            c_icon = CATEGORY_ICONS.get(category, "📝")
            status = ticket.get("status", "open")
            escalated = " **ESCALATED**" if ticket.get("escalate") else ""

            with st.expander(
                f"{p_icon} {ticket.get('ticket_id', '?')} — {ticket.get('subject', 'No subject')} "
                f"[{status}]{escalated}"
            ):
                col_a, col_b, col_c = st.columns(3)
                col_a.markdown(f"**Category:** {c_icon} {category}")
                col_b.markdown(f"**Priority:** {p_icon} {priority}")
                col_c.markdown(f"**Team:** {ticket.get('team', 'unassigned')}")

                col_d, col_e, col_f = st.columns(3)
                col_d.markdown(f"**Customer:** {ticket.get('customer_name', 'unknown')}")
                col_e.markdown(f"**Org:** {ticket.get('customer_org', 'unknown')}")
                col_f.markdown(f"**Assigned to:** {ticket.get('assigned_to', 'unassigned')}")

                st.markdown(f"**Created:** {ticket.get('created_at', '?')}")

                if ticket.get("body"):
                    st.markdown("**Description:**")
                    st.text(ticket["body"])

                if ticket.get("triage_reasoning"):
                    st.markdown(f"**Triage reasoning:** {ticket['triage_reasoning']}")

                if ticket.get("resolution_note"):
                    st.markdown(f"**Resolution:** {ticket['resolution_note']}")
