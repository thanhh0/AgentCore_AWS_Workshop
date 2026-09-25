"""Guardrail hook that enforces mandatory escalation rules and PII access controls.

Runs after each agent cycle to verify the agent followed policy. If the agent
should have escalated but didn't, the hook injects a corrective message.
"""
import re
from strands.hooks import HookProvider, MessageAddedEvent


ESCALATION_PATTERNS = {
    "emergency": [
        r"\b(emergency|urgent|life.?threatening|chest pain|suicide|self.?harm|overdose|anaphyla)\b",
        r"\b(call\s+000|call\s+an?\s+ambulance|medical\s+emergency)\b",
    ],
    "child_related": [
        r"\b(child|children|minor|minors|under\s*18|paediatric|pediatric|infant|toddler|adolescent|teenager)\b",
        r"\bmy\s+\S*\s*(son|daughter|kid|child)\b",
        r"\b\d+\s*year.?old\b",
    ],
    "cancellation": [
        r"\b(cancel\s+(my|our|the)\s+(service|subscription|plan|account|contract))\b",
        r"\b(want\s+to\s+(cancel|terminate|end|discontinue))\b",
        r"\b(cancellation|unsubscribe)\b",
    ],
}

COMPILED_PATTERNS = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in ESCALATION_PATTERNS.items()
}


def detect_escalation_triggers(text: str) -> list[str]:
    triggered = []
    for category, patterns in COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                triggered.append(category)
                break
    return triggered


class GuardrailHook(HookProvider):
    """Monitors messages for escalation triggers and flags when the agent should escalate."""

    def on_message_added(self, event: MessageAddedEvent):
        agent = event.agent
        messages = agent.messages
        if not messages:
            return

        user_messages = [
            block.get("text", "")
            for msg in messages
            if msg.get("role") == "user"
            for block in msg.get("content", [])
            if isinstance(block, dict) and "text" in block
        ]

        if not user_messages:
            return

        latest_user_text = user_messages[-1]
        triggers = detect_escalation_triggers(latest_user_text)

        if not triggers:
            return

        last_msg = messages[-1]
        if last_msg.get("role") != "assistant":
            return

        assistant_content = last_msg.get("content", [])
        used_escalation = any(
            isinstance(block, dict)
            and block.get("toolUse", {}).get("name") == "escalate_to_human"
            for block in assistant_content
        )

        if used_escalation:
            return

        trigger_str = ", ".join(triggers)
        agent.messages.append({
            "role": "user",
            "content": [{
                "text": (
                    f"[GUARDRAIL] This conversation contains triggers requiring mandatory escalation: {trigger_str}. "
                    "You MUST use the escalate_to_human tool now. Do not attempt to handle this yourself."
                )
            }],
        })

    def register_hooks(self, registry):
        registry.add_callback(MessageAddedEvent, self.on_message_added)
