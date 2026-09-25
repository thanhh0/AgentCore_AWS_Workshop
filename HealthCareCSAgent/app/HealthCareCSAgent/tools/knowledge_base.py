from strands import tool
from typing import Optional


KNOWLEDGE_ARTICLES = {
    "telehealth-setup": {
        "id": "KB-001",
        "title": "Getting Started with Telehealth Consultations",
        "category": "onboarding",
        "content": (
            "To begin offering telehealth consultations:\n"
            "1. Log in to the Provider Portal at portal.healthsaas.example.com\n"
            "2. Navigate to Settings > Telehealth Configuration\n"
            "3. Enable video consultations and set your availability windows\n"
            "4. Configure e-prescription integration (requires AHPRA verification)\n"
            "5. Invite clinicians via Settings > Team Management\n"
            "Each clinician must complete identity verification before conducting consultations."
        ),
        "tags": ["telehealth", "setup", "onboarding", "video", "clinician"],
    },
    "drug-testing-compliance": {
        "id": "KB-002",
        "title": "Drug Testing Compliance & Chain of Custody",
        "category": "compliance",
        "content": (
            "All drug testing workflows must follow AS/NZS 4308:2008 standards.\n"
            "- Chain of custody forms are auto-generated for each test\n"
            "- Specimens must be sealed and barcoded at point of collection\n"
            "- Results are reported within 24-48 hours for standard panels\n"
            "- Positive results trigger an automatic Medical Review Officer (MRO) review\n"
            "- Employers receive only pass/fail unless the employee consents to detailed results\n"
            "For FIFO workforce testing, on-site collection kits can be ordered via the portal."
        ),
        "tags": ["drug_testing", "compliance", "chain_of_custody", "mining", "FIFO"],
    },
    "billing-invoices": {
        "id": "KB-003",
        "title": "Billing, Invoices & Payment Terms",
        "category": "billing",
        "content": (
            "Invoices are issued on the 1st of each month for the prior month's usage.\n"
            "- Payment terms: Net 30 days\n"
            "- Accepted methods: direct debit, credit card, EFT\n"
            "- Overdue accounts (60+ days) are suspended automatically\n"
            "- To dispute an invoice, contact billing@healthsaas.example.com within 14 days\n"
            "- Enterprise plans include volume discounts reviewed quarterly\n"
            "Account suspension can be lifted within 24 hours of payment clearance."
        ),
        "tags": ["billing", "invoices", "payment", "suspension"],
    },
    "patient-portal": {
        "id": "KB-004",
        "title": "Patient Portal Features & Access",
        "category": "product",
        "content": (
            "The Patient Portal allows end-patients to:\n"
            "- Book and manage telehealth appointments\n"
            "- View consultation summaries and prescriptions\n"
            "- Upload documents (referrals, test results)\n"
            "- Message their healthcare provider securely\n"
            "Patients receive an invite link from their provider. The portal supports "
            "SMS-based 2FA. Patient data is stored in Australia (ap-southeast-2) and "
            "complies with the Privacy Act 1988 and My Health Records Act 2012."
        ),
        "tags": ["patient_portal", "telehealth", "privacy", "appointments"],
    },
    "sports-injury-tracking": {
        "id": "KB-005",
        "title": "Sports Injury Tracking Module",
        "category": "product",
        "content": (
            "The Sports Health Pro plan includes:\n"
            "- Player injury registration and status tracking\n"
            "- Return-to-play workflow with medical sign-off\n"
            "- Telehealth consultations with team medical staff\n"
            "- Wellness check-in surveys (configurable frequency)\n"
            "- Integration with common sports science platforms (GPS, load monitoring)\n"
            "All player health data is access-controlled per role (coach, physio, doctor)."
        ),
        "tags": ["sports", "injury", "player_wellness", "sporting_club"],
    },
    "data-privacy": {
        "id": "KB-006",
        "title": "Data Privacy & Security Overview",
        "category": "compliance",
        "content": (
            "Our platform adheres to:\n"
            "- Australian Privacy Principles (APPs) under the Privacy Act 1988\n"
            "- My Health Records Act 2012 requirements\n"
            "- ISO 27001 certified infrastructure\n"
            "- Data residency: all data stored in AWS ap-southeast-2 (Sydney)\n"
            "- Encryption: AES-256 at rest, TLS 1.3 in transit\n"
            "- Annual penetration testing by independent assessors\n"
            "For data access requests or breach notifications, contact security@healthsaas.example.com."
        ),
        "tags": ["privacy", "security", "compliance", "data_residency"],
    },
    "cancellation-policy": {
        "id": "KB-007",
        "title": "Service Cancellation Policy",
        "category": "billing",
        "content": (
            "Service cancellation requires:\n"
            "- 30 days written notice for month-to-month plans\n"
            "- 90 days written notice for annual Enterprise agreements\n"
            "- Data export must be requested before cancellation (provided within 7 business days)\n"
            "- Outstanding invoices must be settled before cancellation is processed\n"
            "- Cancellation requests must be submitted by an authorised account contact\n"
            "NOTE: All cancellation requests must be handled by a human agent — "
            "this cannot be processed automatically."
        ),
        "tags": ["cancellation", "billing", "enterprise", "data_export"],
    },
}


@tool
def search_knowledge_base(query: str, category: Optional[str] = None) -> dict:
    """Search the company knowledge base for articles matching a query.

    Args:
        query: Search terms — topic, keyword, or question.
        category: Optional category filter (onboarding, compliance, billing, product).
    """
    query_lower = query.lower()
    results = []

    for article in KNOWLEDGE_ARTICLES.values():
        if category and article["category"] != category:
            continue
        searchable = f"{article['title']} {article['content']} {' '.join(article['tags'])}"
        if query_lower in searchable.lower():
            results.append({
                "id": article["id"],
                "title": article["title"],
                "category": article["category"],
            })

    if not results:
        return {"found": 0, "message": f"No articles matching '{query}'."}
    return {"found": len(results), "articles": results}


@tool
def get_knowledge_article(article_id: str) -> dict:
    """Retrieve the full content of a knowledge base article.

    Args:
        article_id: The article ID (e.g. KB-001).
    """
    for article in KNOWLEDGE_ARTICLES.values():
        if article["id"] == article_id:
            return article
    return {"error": f"Article {article_id} not found."}
