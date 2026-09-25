# HealthCare CS Agent — Implementation Checklist

## Phase 1: MVP (Baseline)

- [x] Scaffold project with `agentcore create` (Strands + Bedrock + CodeZip)
- [x] Create feature branch `feature/healthcare-cs-agent`
- [x] Customise system prompt for healthcare SaaS customer service
- [x] **Customer search tool** — mock database with 5 customers across verticals
  - [x] `search_customers` — search by name, org, ID, type
  - [x] `get_customer_details` — full PII with authorisation confirmation gate
- [x] **Knowledge base tool** — 7 mock articles covering all verticals
  - [x] `search_knowledge_base` — keyword + category search
  - [x] `get_knowledge_article` — full article retrieval
- [x] **Human escalation tool** — mandatory for emergency, cancellation, child-related
  - [x] `escalate_to_human` — routes to human or creates ticket when staff unavailable
  - [x] `list_tickets` — view open tickets
- [x] **Customer preferences tool** — dual-write to local dict + AgentCore Memory
  - [x] `save_preference` / `get_preferences` with memory fallback
- [x] Wire all tools into main.py

## Phase 2: Memory & Guardrails (Pre-deploy)

- [x] **AgentCore Memory** — SEMANTIC + USER_PREFERENCE strategies
  - [x] `agentcore add memory --name CustMemory --strategies SEMANTIC,USER_PREFERENCE --expiry 30`
  - [x] Wire `AgentCoreMemorySessionManager` into main.py (graceful local dev fallback)
  - [x] Preferences tool writes events to memory for cross-session persistence
  - [x] Retrieval config: top_k=5, relevance_score=0.4 for facts + preferences
- [x] **Guardrail Hook** — programmatic escalation enforcement
  - [x] `hooks/guardrails.py` — regex detection for emergency, child, cancellation triggers
  - [x] Injects corrective prompt when agent fails to escalate
  - [x] Wired into agent via `hooks=[GuardrailHook()]`
- [x] **Gateway + Policy Engine** — provisioned for future external APIs
  - [x] `agentcore add gateway --name CSGateway`
  - [x] `agentcore add policy-engine --name CSPolicyEngine --attach-to-gateways CSGateway --attach-mode LOG_ONLY`
- [ ] Deploy with `agentcore deploy -y`
- [ ] Test memory persistence: invoke → wait → invoke from new session
- [ ] Test escalation guardrails: send emergency/cancellation/child messages

## Phase 3: Enhancements (Post-deploy)

- [ ] **Cedar policies** — after gateway is deployed, add Cedar rules via `agentcore add policy`
  - [ ] PII access policy for customer data tools
  - [ ] Rate limiting policy for search tools
- [ ] **Customisable conversation output** — configurable response format
  - [ ] Support output modes: verbose, concise, structured JSON
  - [ ] Customer-specific tone/language preferences from memory
- [ ] **Chat UI** — Streamlit or Gradio frontend
  - [ ] Basic chat interface calling the deployed agent
  - [ ] Show escalation status and ticket info in sidebar
- [ ] Switch policy engine from LOG_ONLY to ENFORCE after validation

## Phase 4: Stretch Goals

- [ ] **Multi-agent architecture** — specialist sub-agents (billing, clinical, compliance)
- [ ] **RAG with real knowledge base** — replace mock KB with AgentCore Knowledge Base
- [ ] **Evaluations** — automated quality scoring with `agentcore add evaluator`
- [ ] **Observability** — traces + logs dashboard
- [ ] **DynamoDB ticket store** — persistent ticket storage

## Architecture

```
User → AgentCore Runtime (Strands Agent)
         │
         ├── AgentCoreMemorySessionManager (SEMANTIC + USER_PREFERENCE)
         │     └── Cross-session facts & preferences via MEMORY_CUSTMEMORY_ID
         │
         ├── GuardrailHook (hooks/guardrails.py)
         │     └── Regex-based escalation trigger detection + corrective injection
         │
         ├── tools/customer_search.py    (mock DB, PII gate via confirm_authorised)
         ├── tools/knowledge_base.py     (mock KB, 7 articles)
         ├── tools/escalation.py         (human routing + ticket creation)
         ├── tools/preferences.py        (dual-write: local + AgentCore Memory)
         │
         ├── CSGateway + CSPolicyEngine  (provisioned, LOG_ONLY — for future APIs)
         │
         └── model/load.py              (Bedrock Claude Sonnet 4.5)
```

## Key Decisions

| Decision | Choice | Rationale |
|:---------|:-------|:----------|
| Framework | Strands | Best AgentCore integration, simplest path |
| Model | Claude Sonnet 4.5 (Bedrock) | Strong reasoning, no API key needed |
| Build | CodeZip | Faster deploys, no Docker dependency |
| Memory strategy | SEMANTIC + USER_PREFERENCE | Facts about customers + explicit preference storage |
| Guardrails approach | Strands hook + system prompt | Inline tools don't go through gateway; Cedar policies for future gateway tools |
| Policy engine mode | LOG_ONLY | Validate before enforcing; switch to ENFORCE after testing |
| Data | Mock/in-memory with memory fallback | Workshop-scoped; each tool structured for easy migration |
