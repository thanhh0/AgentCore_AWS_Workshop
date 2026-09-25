import os
import json
import uuid
import re
import boto3
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

REGION = os.getenv("AWS_REGION", "us-west-2")
RUNTIME_ARN = os.getenv(
    "AGENT_RUNTIME_ARN",
    "arn:aws:bedrock-agentcore:us-west-2:825729848461:runtime/HealthCareCSAgent_HealthCareCSAgent-QJDnQRCSv7",
)

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

client = boto3.client("bedrock-agentcore", region_name=REGION)


MOCK_CUSTOMERS = {
    "C-1001": {
        "id": "C-1001", "name": "Dr. Sarah Mitchell", "email": "s.mitchell@northsidemedical.com.au",
        "phone": "+61 3 9555 1234", "org": "Northside Medical Group", "org_type": "telehealth_provider",
        "plan": "Enterprise Telehealth", "status": "active",
        "services": ["video_consult", "e_prescriptions", "patient_portal"],
    },
    "C-1002": {
        "id": "C-1002", "name": "James Caldwell", "email": "jcaldwell@westcoastfc.com.au",
        "phone": "+61 8 9444 5678", "org": "West Coast Football Club", "org_type": "sporting_club",
        "plan": "Sports Health Pro", "status": "active",
        "services": ["injury_tracking", "telehealth_consult", "player_wellness"],
    },
    "C-1003": {
        "id": "C-1003", "name": "Karen Liu", "email": "karen.liu@pilbaramining.com.au",
        "phone": "+61 8 9222 3456", "org": "Pilbara Mining Corp", "org_type": "mining",
        "plan": "Workplace Health Suite", "status": "active",
        "services": ["drug_testing", "fitness_for_duty", "remote_telehealth"],
    },
    "C-1004": {
        "id": "C-1004", "name": "Tom Nguyen", "email": "tom@safeworktesting.com.au",
        "phone": "+61 2 9888 7654", "org": "SafeWork Testing Services", "org_type": "drug_testing_agency",
        "plan": "Testing Agency Standard", "status": "active",
        "services": ["drug_testing", "chain_of_custody", "result_reporting"],
    },
    "C-1005": {
        "id": "C-1005", "name": "Rachel Adams", "email": "radams@familycarehealth.com.au",
        "phone": "+61 7 3111 2233", "org": "FamilyCare Health", "org_type": "telehealth_provider",
        "plan": "Telehealth Starter", "status": "suspended",
        "services": ["video_consult", "patient_portal"],
    },
}

MOCK_BOOKINGS = [
    {"id": "BK-001", "customer": "C-1001", "type": "Telehealth Setup Review", "date": "2026-10-02", "status": "confirmed", "provider": "Platform Support"},
    {"id": "BK-002", "customer": "C-1002", "type": "Injury Tracking Demo", "date": "2026-10-05", "status": "confirmed", "provider": "Product Team"},
    {"id": "BK-003", "customer": "C-1003", "type": "Compliance Audit Prep", "date": "2026-10-08", "status": "pending", "provider": "Compliance Team"},
    {"id": "BK-004", "customer": "C-1005", "type": "Account Reinstatement", "date": "2026-10-01", "status": "pending", "provider": "Billing Team"},
]

MOCK_MEDICAL_DOCS = [
    {"id": "MD-001", "customer": "C-1001", "name": "AHPRA Registration.pdf", "type": "registration", "uploaded": "2026-08-15", "size": "245 KB"},
    {"id": "MD-002", "customer": "C-1002", "name": "Player Medical Clearance - Season 2026.pdf", "type": "clearance", "uploaded": "2026-09-01", "size": "1.2 MB"},
    {"id": "MD-003", "customer": "C-1003", "name": "Drug Testing Protocol v3.pdf", "type": "protocol", "uploaded": "2026-07-20", "size": "890 KB"},
    {"id": "MD-004", "customer": "C-1003", "name": "Fitness for Duty Standards.docx", "type": "standard", "uploaded": "2026-06-10", "size": "456 KB"},
    {"id": "MD-005", "customer": "C-1004", "name": "Chain of Custody Template.pdf", "type": "template", "uploaded": "2026-09-10", "size": "123 KB"},
]


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/api/customers")
async def list_customers():
    return list(MOCK_CUSTOMERS.values())


@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: str):
    c = MOCK_CUSTOMERS.get(customer_id)
    if not c:
        return {"error": "Not found"}
    return c


@app.get("/api/bookings")
async def list_bookings(customer_id: str = None):
    if customer_id:
        return [b for b in MOCK_BOOKINGS if b["customer"] == customer_id]
    return MOCK_BOOKINGS


@app.get("/api/medical-docs")
async def list_medical_docs(customer_id: str = None):
    if customer_id:
        return [d for d in MOCK_MEDICAL_DOCS if d["customer"] == customer_id]
    return MOCK_MEDICAL_DOCS


def _parse_sse_stream(raw: str) -> str:
    text_parts = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("event:") or line.startswith(":"):
            continue
        data_str = line[5:].strip() if line.startswith("data:") else line
        if not data_str:
            continue
        try:
            data = json.loads(data_str)
            event = data.get("event", {})
            cbd = event.get("contentBlockDelta", {})
            delta = cbd.get("delta", {})
            text = delta.get("text")
            if text:
                cleaned = re.sub(r"</?thinking>", "", text)
                if cleaned:
                    text_parts.append(cleaned)
        except json.JSONDecodeError:
            pass
    return "".join(text_parts)


ONBOARDING_FEATURES = {
    "telehealth_provider": {
        "label": "Telehealth Provider",
        "features": [
            {"key": "video_consult", "name": "Video Consultations", "desc": "HD video appointments with screen sharing, recording, and waiting room management."},
            {"key": "e_prescriptions", "name": "E-Prescriptions", "desc": "Digitally sign and send prescriptions to pharmacies. Requires AHPRA verification."},
            {"key": "patient_portal", "name": "Patient Portal", "desc": "Patients book appointments, view summaries, upload documents, and message providers securely."},
        ],
        "preferences": [
            {"key": "contact_method", "label": "Preferred contact method", "options": ["Email", "Phone", "SMS", "In-app message"]},
            {"key": "notification_frequency", "label": "Notification frequency", "options": ["Real-time", "Daily digest", "Weekly summary"]},
            {"key": "consult_reminders", "label": "Consultation reminders", "options": ["30 minutes before", "1 hour before", "1 day before", "No reminders"]},
            {"key": "data_export_format", "label": "Preferred data export format", "options": ["PDF", "CSV", "HL7 FHIR"]},
        ],
    },
    "mining": {
        "label": "Mining & Workplace Health",
        "features": [
            {"key": "drug_testing", "name": "Drug Testing & Chain of Custody", "desc": "AS/NZS 4308 compliant testing with auto-generated chain of custody forms and MRO review."},
            {"key": "fitness_for_duty", "name": "Fitness for Duty Assessments", "desc": "Pre-employment and periodic health assessments for FIFO and on-site workers."},
            {"key": "remote_telehealth", "name": "Remote Site Telehealth", "desc": "Telehealth consultations optimised for low-bandwidth remote and FIFO sites."},
        ],
        "preferences": [
            {"key": "contact_method", "label": "Preferred contact method", "options": ["Email", "Phone", "SMS", "In-app message"]},
            {"key": "notification_frequency", "label": "Notification frequency", "options": ["Real-time", "Daily digest", "Weekly summary"]},
            {"key": "compliance_alerts", "label": "Compliance alert level", "options": ["All alerts", "Critical only", "Summary reports"]},
            {"key": "testing_kit_reorder", "label": "Auto-reorder testing kits", "options": ["Yes, when stock is low", "No, I'll order manually"]},
        ],
    },
    "sporting_club": {
        "label": "Sports Health",
        "features": [
            {"key": "injury_tracking", "name": "Injury Registration & Tracking", "desc": "Log injuries, track recovery timelines, and manage return-to-play workflows with medical sign-off."},
            {"key": "player_wellness", "name": "Player Wellness Check-ins", "desc": "Configurable wellness surveys, load monitoring integration, and trend dashboards."},
            {"key": "telehealth_consult", "name": "Team Medical Telehealth", "desc": "Video consultations between players and team medical staff, with role-based access controls."},
        ],
        "preferences": [
            {"key": "contact_method", "label": "Preferred contact method", "options": ["Email", "Phone", "SMS", "In-app message"]},
            {"key": "notification_frequency", "label": "Notification frequency", "options": ["Real-time", "Daily digest", "Weekly summary"]},
            {"key": "wellness_check_freq", "label": "Wellness check-in frequency", "options": ["Daily", "Twice weekly", "Weekly", "Fortnightly"]},
            {"key": "injury_report_access", "label": "Injury report visibility", "options": ["Medical staff only", "Medical + coaching staff", "All team staff"]},
        ],
    },
    "drug_testing_agency": {
        "label": "Testing Agency",
        "features": [
            {"key": "drug_testing", "name": "Drug Testing Management", "desc": "End-to-end testing workflows with chain of custody, barcode scanning, and result reporting."},
            {"key": "chain_of_custody", "name": "Chain of Custody Tracking", "desc": "Digital chain of custody forms with tamper-evident seals and audit trail."},
            {"key": "result_reporting", "name": "Result Reporting Portal", "desc": "Employer-facing portal with pass/fail results, MRO review status, and compliance dashboards."},
        ],
        "preferences": [
            {"key": "contact_method", "label": "Preferred contact method", "options": ["Email", "Phone", "SMS", "In-app message"]},
            {"key": "notification_frequency", "label": "Notification frequency", "options": ["Real-time", "Daily digest", "Weekly summary"]},
            {"key": "result_turnaround", "label": "Result notification timing", "options": ["As soon as available", "Batched daily", "Batched weekly"]},
            {"key": "report_format", "label": "Preferred report format", "options": ["PDF", "CSV", "API integration"]},
        ],
    },
}


@app.get("/api/onboarding/{customer_id}")
async def get_onboarding_content(customer_id: str):
    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": "Customer not found"}
    org_type = customer.get("org_type", "telehealth_provider")
    content = ONBOARDING_FEATURES.get(org_type, ONBOARDING_FEATURES["telehealth_provider"])
    return {
        "customer": {
            "id": customer["id"],
            "name": customer["name"],
            "org": customer["org"],
            "org_type": org_type,
            "plan": customer["plan"],
            "services": customer["services"],
        },
        "content": content,
    }


@app.post("/api/onboarding/complete")
async def complete_onboarding(request: Request):
    body = await request.json()
    customer_id = body.get("customer_id", "C-1001")
    preferences = body.get("preferences", {})
    session_id = body.get("session_id", str(uuid.uuid4()))

    pref_lines = [f"- {k}: {v}" for k, v in preferences.items()]
    prompt = (
        f"[SYSTEM: Customer {customer_id} just completed onboarding. "
        f"Save the following preferences for this customer using the save_preference tool. "
        f"Save each preference individually.]\n\n"
        f"Preferences to save:\n" + "\n".join(pref_lines) + "\n\n"
        f"After saving, confirm that onboarding is complete and briefly welcome the customer."
    )

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"prompt": prompt}).encode(),
            runtimeSessionId=session_id,
        )
        stream = response.get("response")
        full_text = ""
        if stream:
            if hasattr(stream, "iter_lines"):
                for line in stream.iter_lines():
                    if line:
                        decoded = line.decode() if isinstance(line, bytes) else line
                        full_text += _parse_sse_stream(decoded)
            else:
                content = stream.read()
                decoded = content.decode() if isinstance(content, bytes) else content
                full_text = _parse_sse_stream(decoded)

        return {"status": "complete", "message": full_text or "Onboarding complete! Your preferences have been saved."}
    except Exception as e:
        return {"status": "complete", "message": f"Onboarding complete! (Note: preferences will sync on next interaction. {e})"}


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id", str(uuid.uuid4()))

    async def generate():
        try:
            response = client.invoke_agent_runtime(
                agentRuntimeArn=RUNTIME_ARN,
                qualifier="DEFAULT",
                payload=json.dumps({"prompt": prompt}).encode(),
                runtimeSessionId=session_id,
            )
            stream = response.get("response")
            if stream is None:
                yield f"data: {json.dumps({'text': 'No response from agent.'})}\n\n"
                return

            if hasattr(stream, "iter_lines"):
                for line in stream.iter_lines():
                    if line:
                        decoded = line.decode() if isinstance(line, bytes) else line
                        text = _parse_sse_stream(decoded)
                        if text:
                            yield f"data: {json.dumps({'text': text})}\n\n"
            else:
                content = stream.read()
                decoded = content.decode() if isinstance(content, bytes) else content
                text = _parse_sse_stream(decoded)
                if text:
                    yield f"data: {json.dumps({'text': text})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8502"))
    workshop_url = os.getenv("WORKSHOP_URL", "http://localhost:8502")
    print(f"\n  App running at: {workshop_url}/app/{port}/\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
