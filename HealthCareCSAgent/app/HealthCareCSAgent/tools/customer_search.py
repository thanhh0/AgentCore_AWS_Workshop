from strands import tool
from typing import Optional


MOCK_CUSTOMERS = {
    "C-1001": {
        "id": "C-1001",
        "name": "Dr. Sarah Mitchell",
        "email": "s.mitchell@northsidemedical.com.au",
        "phone": "+61 3 9555 1234",
        "org": "Northside Medical Group",
        "org_type": "telehealth_provider",
        "plan": "Enterprise Telehealth",
        "status": "active",
        "services": ["video_consult", "e_prescriptions", "patient_portal"],
        "notes": "Key account — 12 clinicians onboarded. Prefers email contact.",
    },
    "C-1002": {
        "id": "C-1002",
        "name": "James Caldwell",
        "email": "jcaldwell@westcoastfc.com.au",
        "phone": "+61 8 9444 5678",
        "org": "West Coast Football Club",
        "org_type": "sporting_club",
        "plan": "Sports Health Pro",
        "status": "active",
        "services": ["injury_tracking", "telehealth_consult", "player_wellness"],
        "notes": "Season in progress. High priority during match weeks.",
    },
    "C-1003": {
        "id": "C-1003",
        "name": "Karen Liu",
        "email": "karen.liu@pilbaramining.com.au",
        "phone": "+61 8 9222 3456",
        "org": "Pilbara Mining Corp",
        "org_type": "mining",
        "plan": "Workplace Health Suite",
        "status": "active",
        "services": ["drug_testing", "fitness_for_duty", "remote_telehealth"],
        "notes": "FIFO workforce. Compliance-critical — drug testing SLAs strictly enforced.",
    },
    "C-1004": {
        "id": "C-1004",
        "name": "Tom Nguyen",
        "email": "tom@safeworktesting.com.au",
        "phone": "+61 2 9888 7654",
        "org": "SafeWork Testing Services",
        "org_type": "drug_testing_agency",
        "plan": "Testing Agency Standard",
        "status": "active",
        "services": ["drug_testing", "chain_of_custody", "result_reporting"],
        "notes": "B2B reseller. Serves 40+ employer clients.",
    },
    "C-1005": {
        "id": "C-1005",
        "name": "Rachel Adams",
        "email": "radams@familycarehealth.com.au",
        "phone": "+61 7 3111 2233",
        "org": "FamilyCare Health",
        "org_type": "telehealth_provider",
        "plan": "Telehealth Starter",
        "status": "suspended",
        "services": ["video_consult", "patient_portal"],
        "notes": "Account suspended — outstanding invoice 60+ days. Escalate billing queries.",
    },
}


@tool
def search_customers(query: str, field: Optional[str] = None) -> dict:
    """Search the customer database by name, organisation, ID, or any field.

    Args:
        query: Search term — customer name, org name, customer ID, or keyword.
        field: Optional field to restrict search to (name, org, org_type, plan, status). Searches all fields if omitted.
    """
    query_lower = query.lower()
    results = []

    for customer in MOCK_CUSTOMERS.values():
        if field and field in customer:
            if query_lower in str(customer[field]).lower():
                results.append(_summary(customer))
        else:
            searchable = f"{customer['name']} {customer['org']} {customer['id']} {customer['org_type']} {customer['plan']} {customer['status']}"
            if query_lower in searchable.lower():
                results.append(_summary(customer))

    if not results:
        return {"found": 0, "message": f"No customers matching '{query}'."}
    return {"found": len(results), "customers": results}


@tool
def get_customer_details(customer_id: str, confirm_authorised: bool) -> dict:
    """Retrieve full customer details including PII. Requires explicit authorisation confirmation.

    Args:
        customer_id: The customer ID (e.g. C-1001).
        confirm_authorised: Must be True — confirms the caller has verified they are authorised to view this customer's data.
    """
    if not confirm_authorised:
        return {"error": "Access denied. You must confirm authorisation before viewing customer PII."}

    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found."}
    return customer


def _summary(customer: dict) -> dict:
    return {
        "id": customer["id"],
        "name": customer["name"],
        "org": customer["org"],
        "org_type": customer["org_type"],
        "plan": customer["plan"],
        "status": customer["status"],
    }
