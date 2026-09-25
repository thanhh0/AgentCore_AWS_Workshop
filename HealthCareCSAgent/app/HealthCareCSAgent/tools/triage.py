from strands import tool
from typing import Optional
from tools.ticket_store import create_ticket, list_tickets as _list_tickets, get_ticket, update_ticket


@tool
def triage_and_create_ticket(
    subject: str,
    body: str,
    category: str,
    priority: str,
    team: str,
    reasoning: str,
    customer_id: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_org: Optional[str] = None,
    escalate: bool = False,
) -> dict:
    """Create a triaged support ticket after classifying the incoming request.

    You MUST classify every incoming ticket using these rules:

    CATEGORIES (pick one):
    - billing: invoices, payments, pricing, plan changes, refunds, suspension
    - clinical: medical emergencies, patient care, telehealth session issues, prescriptions
    - technical: platform bugs, login issues, integration errors, API problems, performance
    - compliance: drug testing, chain of custody, privacy, data requests, audits, FIFO
    - account: onboarding, cancellations, account changes, user management, permissions

    PRIORITY (pick one):
    - critical: medical emergencies, safety concerns, data breaches, complete service outages
    - high: service cancellations, compliance deadlines, suspended accounts, child-related
    - medium: feature issues, billing disputes, configuration help
    - low: general questions, feature requests, feedback

    TEAM (pick one):
    - billing: for billing/payment/pricing issues
    - clinical: for medical/patient/telehealth issues
    - technical: for platform/integration/bug issues
    - compliance: for regulatory/privacy/drug-testing issues
    - account: for account lifecycle/onboarding/cancellation

    ESCALATION: Set escalate=True for emergencies, child-related, or cancellations.

    Args:
        subject: Short ticket subject line.
        body: Full ticket description.
        category: One of: billing, clinical, technical, compliance, account.
        priority: One of: critical, high, medium, low.
        team: One of: billing, clinical, technical, compliance, account.
        reasoning: Explain why you chose this category, priority, and team.
        customer_id: Customer ID if identified from the request.
        customer_name: Customer name if identified.
        customer_org: Customer organisation if identified.
        escalate: True if this needs immediate human attention.
    """
    ticket = create_ticket(
        subject=subject,
        body=body,
        category=category,
        priority=priority,
        team=team,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_org=customer_org,
        triage_reasoning=reasoning,
        escalate=escalate,
    )
    return {
        "status": "triaged",
        "ticket": ticket,
        "message": f"Ticket {ticket['ticket_id']} created — {priority} priority, routed to {ticket['team']}."
        + (" ESCALATED for immediate attention." if escalate else ""),
    }


@tool
def get_ticket_queue(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    team: Optional[str] = None,
) -> dict:
    """Retrieve the current ticket queue with optional filters.

    Args:
        status: Filter by status: open, in_progress, resolved, closed.
        category: Filter by category: billing, clinical, technical, compliance, account.
        priority: Filter by priority: critical, high, medium, low.
        team: Filter by team: billing, clinical, technical, compliance, account.
    """
    tickets = _list_tickets(status=status, category=category, priority=priority, team=team)
    return {"count": len(tickets), "tickets": tickets}


@tool
def update_ticket_status(
    ticket_id: str,
    status: str,
    assigned_to: Optional[str] = None,
    resolution_note: Optional[str] = None,
) -> dict:
    """Update a ticket's status or assignment.

    Args:
        ticket_id: The ticket ID (e.g. TKT-AB12CD34).
        status: New status: open, in_progress, resolved, closed.
        assigned_to: Name of the person/team taking ownership.
        resolution_note: Note explaining the resolution (required when resolving/closing).
    """
    updates = {"status": status}
    if assigned_to:
        updates["assigned_to"] = assigned_to
    if resolution_note:
        updates["resolution_note"] = resolution_note

    ticket = update_ticket(ticket_id, **updates)
    if not ticket:
        return {"error": f"Ticket {ticket_id} not found."}
    return {"status": "updated", "ticket": ticket}
