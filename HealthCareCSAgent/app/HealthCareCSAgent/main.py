import os
import re
from typing import Any
from collections import OrderedDict
from strands import Agent
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

from tools.customer_search import search_customers, get_customer_details
from tools.knowledge_base import search_knowledge_base, get_knowledge_article
from tools.escalation import escalate_to_human, list_tickets
from tools.preferences import save_preference, get_preferences
from hooks.guardrails import GuardrailHook

app = BedrockAgentCoreApp()
log = app.logger

MEMORY_ID = os.getenv("MEMORY_CUSTMEMORY_ID")
REGION = os.getenv("AWS_REGION", "us-west-2")

session_manager = None
if MEMORY_ID:
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    log.info(f"AgentCore Memory enabled: {MEMORY_ID}")
else:
    log.info("AgentCore Memory not available (local dev or not yet deployed)")


DEFAULT_SYSTEM_PROMPT = """You are a customer service specialist for a Healthcare SaaS company that builds operational platforms for telehealth providers, sporting clubs, mining organisations, and workplace drug testing agencies.

IMPORTANT: Never output <thinking> tags or internal reasoning. Only output your final response to the customer.

Your role:
- Answer questions about the company's products and services using the knowledge base
- Help customers find their account information (with proper authorisation)
- Save and retrieve customer preferences (these persist across sessions via memory)
- Escalate to a human agent when required

Conversation style:
- Professional, empathetic, and concise
- Use plain language — avoid unnecessary jargon
- Confirm understanding before taking actions
- Summarise what you did at the end of each interaction

MANDATORY ESCALATION RULES — you MUST use escalate_to_human immediately when:
1. EMERGENCY: Any medical emergency, safety concern, or urgent clinical issue
2. CANCELLATION: Any request to cancel a service or subscription
3. CHILDREN: Any request involving minors (patients or subjects under 18)
Do NOT attempt to handle these yourself. Escalate FIRST, then inform the customer.

CUSTOMER DATA RULES:
- When searching for customers, show only summary info (name, org, plan, status)
- Before revealing full details (email, phone, notes), you MUST ask the user to confirm they are authorised to view this data
- Never volunteer PII unprompted
- Set confirm_authorised=True ONLY after the user explicitly confirms

KNOWLEDGE BASE:
- ALWAYS search the knowledge base before answering product/policy questions
- Try multiple search terms if the first search returns no results (e.g. for mining, also try "drug testing", "FIFO", "workplace")
- When results are found, retrieve the full article and present the information to the customer
- If no relevant article exists after multiple searches, say so honestly — never fabricate policies
- Only escalate to a human if the customer explicitly requests it or the mandatory escalation rules apply

MEMORY:
- When you learn a customer preference (contact method, language, format, etc.), save it
- At the start of a conversation, check if you have stored preferences for the customer
"""


tools = [
    search_customers,
    get_customer_details,
    search_knowledge_base,
    get_knowledge_article,
    escalate_to_human,
    list_tickets,
    save_preference,
    get_preferences,
]


def _build_session_manager(actor_id: str, session_id: str):
    if not MEMORY_ID:
        return None
    memory_config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={
            f"/users/{actor_id}/facts": RetrievalConfig(top_k=5, relevance_score=0.4),
            f"/users/{actor_id}/preferences": RetrievalConfig(top_k=5, relevance_score=0.4),
        },
    )
    return AgentCoreMemorySessionManager(memory_config, REGION)


def _make_conversation_manager():
    return NullConversationManager()


def agent_factory():
    cache = OrderedDict()

    def get_or_create_agent(session_id, actor_id="default-user"):
        cache_key = f"{actor_id}:{session_id}"
        if cache_key in cache:
            cache.move_to_end(cache_key)
            return cache[cache_key]
        if len(cache) >= 128:
            cache.popitem(last=False)

        sm = _build_session_manager(actor_id, session_id)

        cache[cache_key] = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools,
            conversation_manager=_make_conversation_manager(),
            session_manager=sm,
            hooks=[GuardrailHook()],
        )
        return cache[cache_key]

    return get_or_create_agent


get_or_create_agent = agent_factory()


def strip_trailing_tool_use(messages: Any) -> list[dict]:
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")

    messages = list(messages)
    while messages:
        last = messages[-1]
        if not isinstance(last, dict):
            raise ValueError("each message must be an object")
        original_content = last.get("content", [])
        if not isinstance(original_content, list) or not all(isinstance(block, dict) for block in original_content):
            raise ValueError("each message content value must be a list of content blocks")

        content = [block for block in original_content if "toolUse" not in block]
        if len(content) == len(original_content):
            break
        if content:
            messages[-1] = {**last, "content": content}
            break
        messages.pop()

    return messages


def _extract_prompt(payload: dict):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    if "messages" in payload:
        return strip_trailing_tool_use(payload["messages"])
    if "tool_results" in payload:
        tool_results = payload["tool_results"]
        if not isinstance(tool_results, list) or not all(
            isinstance(tool_result, dict) and isinstance(tool_result.get("toolUseId"), str)
            for tool_result in tool_results
        ):
            raise ValueError("tool_results must contain objects with a toolUseId string")
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in tool_results]}]
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("prompt must be a string")
    return prompt


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking HealthCare CS Agent...")

    session_id = getattr(context, 'session_id', 'default-session')
    actor_id = payload.get("userId", "default-user") if isinstance(payload, dict) else "default-user"
    agent = get_or_create_agent(session_id, actor_id)

    prompt = _extract_prompt(payload)

    async for event in agent.stream_async(
        prompt,
    ):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        # Strip <thinking> tags from Nova model output
        cbd = event["event"].get("contentBlockDelta", {})
        delta = cbd.get("delta", {})
        if "text" in delta:
            cleaned = re.sub(r"</?thinking>", "", delta["text"])
            if not cleaned:
                continue
            delta["text"] = cleaned
        yield event


if __name__ == "__main__":
    app.run()
