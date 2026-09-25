import os
import logging
from strands import tool
from typing import Optional

log = logging.getLogger(__name__)

PREFERENCES_STORE: dict[str, dict] = {}

MEMORY_ID = os.getenv("MEMORY_CUSTMEMORY_ID")
_memory_client = None


def _get_memory_client():
    global _memory_client
    if _memory_client is None and MEMORY_ID:
        try:
            from bedrock_agentcore.memory import MemoryClient
            region = os.getenv("AWS_REGION", "us-west-2")
            _memory_client = MemoryClient(region_name=region)
        except Exception as e:
            log.warning(f"Could not initialise MemoryClient: {e}")
    return _memory_client


@tool
def save_preference(customer_id: str, key: str, value: str) -> dict:
    """Save a customer preference. Persists to AgentCore memory when deployed, falls back to local storage otherwise.

    Args:
        customer_id: The customer ID (e.g. C-1001).
        key: Preference key (e.g. contact_method, language, notification_frequency).
        value: Preference value.
    """
    if customer_id not in PREFERENCES_STORE:
        PREFERENCES_STORE[customer_id] = {}
    PREFERENCES_STORE[customer_id][key] = value

    client = _get_memory_client()
    if client and MEMORY_ID:
        try:
            client.create_event(
                memory_id=MEMORY_ID,
                actor_id=customer_id,
                session_id=f"pref-{customer_id}",
                messages=[(f"Customer preference: {key} = {value}", "ASSISTANT")],
            )
            return {
                "status": "saved",
                "storage": "agentcore_memory",
                "customer_id": customer_id,
                "preference": {key: value},
            }
        except Exception as e:
            log.warning(f"Memory write failed, using local store: {e}")

    return {
        "status": "saved",
        "storage": "local",
        "customer_id": customer_id,
        "preference": {key: value},
    }


@tool
def get_preferences(customer_id: str, key: Optional[str] = None) -> dict:
    """Retrieve saved preferences for a customer. Checks AgentCore memory first, then local storage.

    Args:
        customer_id: The customer ID.
        key: Optional specific preference key to retrieve. Returns all if omitted.
    """
    client = _get_memory_client()
    if client and MEMORY_ID:
        try:
            memories = client.retrieve_memories(
                memory_id=MEMORY_ID,
                namespace=f"/users/{customer_id}/preferences",
                query=key or "customer preferences",
                top_k=10,
            )
            if memories:
                retrieved = [
                    m.get("content", {}).get("text", "")
                    for m in memories
                    if m.get("content", {}).get("text")
                ]
                if retrieved:
                    return {
                        "customer_id": customer_id,
                        "source": "agentcore_memory",
                        "preferences": retrieved,
                    }
        except Exception as e:
            log.warning(f"Memory read failed, using local store: {e}")

    prefs = PREFERENCES_STORE.get(customer_id, {})
    if key:
        value = prefs.get(key)
        if value is None:
            return {"customer_id": customer_id, "found": False, "message": f"No preference '{key}' found."}
        return {"customer_id": customer_id, "found": True, "source": "local", "preference": {key: value}}
    return {"customer_id": customer_id, "source": "local", "preferences": prefs}
