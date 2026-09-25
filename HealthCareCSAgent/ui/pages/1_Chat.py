import streamlit as st
import boto3
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="HealthCare CS Agent", page_icon="🏥", layout="wide")

REGION = os.getenv("AWS_REGION", "us-west-2")
RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]


@st.cache_resource
def get_client():
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


with st.sidebar:
    st.title("HealthCare CS Agent")
    st.markdown("Customer service specialist for Healthcare SaaS")
    st.divider()

    if st.button("New Conversation"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("### Session Info")
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    st.code(st.session_state.session_id[:8] + "...", language=None)

    st.divider()
    st.markdown("### Capabilities")
    st.markdown("""
    - Search customer accounts
    - Query knowledge base
    - Save preferences (with memory)
    - Ticket triage & routing
    - Human escalation
    """)

    st.divider()
    st.markdown("### Escalation Triggers")
    st.warning("Emergency, cancellation, and child-related requests are automatically escalated to human agents.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            client = get_client()
            try:
                response = invoke_agent(client, prompt, st.session_state.session_id)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
