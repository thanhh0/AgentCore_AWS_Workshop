import boto3
import datetime
import uuid
import os

REGION = os.getenv("AWS_REGION", "us-west-2")
TABLE_NAME = os.getenv("TICKET_TABLE", "HealthCareCS-Tickets")

_table = None


def _get_table():
    global _table
    if _table is not None:
        return _table
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    _table = dynamodb.Table(TABLE_NAME)
    try:
        _table.load()
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "ticket_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "ticket_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        _table.wait_until_exists()
    return _table


TEAMS = {
    "billing": "Billing & Accounts",
    "clinical": "Clinical Support",
    "technical": "Technical Support",
    "compliance": "Compliance & Legal",
    "account": "Account Management",
    "general": "General Support",
}


def create_ticket(
    subject: str,
    body: str,
    category: str,
    priority: str,
    team: str,
    customer_id: str | None = None,
    customer_name: str | None = None,
    customer_org: str | None = None,
    triage_reasoning: str = "",
    escalate: bool = False,
) -> dict:
    ticket = {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "subject": subject,
        "body": body,
        "category": category,
        "priority": priority,
        "team": TEAMS.get(team, team),
        "team_key": team,
        "customer_id": customer_id or "unknown",
        "customer_name": customer_name or "unknown",
        "customer_org": customer_org or "unknown",
        "triage_reasoning": triage_reasoning,
        "escalate": escalate,
        "status": "open",
        "assigned_to": "unassigned",
    }
    _get_table().put_item(Item=ticket)
    return ticket


def list_tickets(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    team: str | None = None,
    limit: int = 50,
) -> list[dict]:
    table = _get_table()
    response = table.scan(Limit=limit)
    tickets = response.get("Items", [])

    if status:
        tickets = [t for t in tickets if t.get("status") == status]
    if category:
        tickets = [t for t in tickets if t.get("category") == category]
    if priority:
        tickets = [t for t in tickets if t.get("priority") == priority]
    if team:
        tickets = [t for t in tickets if t.get("team_key") == team]

    tickets.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return tickets


def get_ticket(ticket_id: str) -> dict | None:
    response = _get_table().get_item(Key={"ticket_id": ticket_id})
    return response.get("Item")


def update_ticket(ticket_id: str, **updates) -> dict | None:
    ticket = get_ticket(ticket_id)
    if not ticket:
        return None
    ticket.update(updates)
    _get_table().put_item(Item=ticket)
    return ticket
