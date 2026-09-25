import datetime
import uuid
from strands import tool
from typing import Optional


STAFF_AVAILABLE = True

TICKET_STORE: list[dict] = []


@tool
def escalate_to_human(
    reason: str,
    category: str,
    customer_id: Optional[str] = None,
    priority: Optional[str] = None,
    summary: str = "",
) -> dict:
    """Escalate a conversation to a human staff member. Use this when the request involves emergencies, service cancellations, or children.

    Args:
        reason: Why this needs human attention — be specific.
        category: One of: emergency, cancellation, child_related, other.
        customer_id: The customer ID if known.
        priority: Suggested priority: critical, high, medium, low. Defaults based on category.
        summary: Brief summary of the conversation so far for the human agent.
    """
    auto_priority = {
        "emergency": "critical",
        "child_related": "critical",
        "cancellation": "high",
        "other": "medium",
    }
    resolved_priority = priority or auto_priority.get(category, "medium")

    if STAFF_AVAILABLE:
        return {
            "status": "escalated",
            "message": f"Transferring to a human agent now. Priority: {resolved_priority}.",
            "category": category,
            "priority": resolved_priority,
            "reason": reason,
            "customer_id": customer_id,
        }

    ticket = {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "category": category,
        "priority": resolved_priority,
        "reason": reason,
        "summary": summary,
        "customer_id": customer_id,
        "status": "open",
        "assigned_to": None,
    }
    TICKET_STORE.append(ticket)

    return {
        "status": "ticket_created",
        "message": (
            "No human agents are currently available. A support ticket has been created "
            "and will be triaged by the next available staff member."
        ),
        "ticket": ticket,
    }


@tool
def list_tickets(customer_id: Optional[str] = None) -> dict:
    """List open support tickets, optionally filtered by customer ID.

    Args:
        customer_id: Filter tickets to a specific customer. Returns all if omitted.
    """
    tickets = TICKET_STORE
    if customer_id:
        tickets = [t for t in tickets if t.get("customer_id") == customer_id]
    return {"count": len(tickets), "tickets": tickets}
