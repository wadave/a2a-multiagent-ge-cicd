# Software Design Document (SDD): Integrating Gemini Enterprise with MCP Servers and A2A Agents

## Table of Contents

### Part I: Current Architecture
1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architectural Design](#3-architectural-design)
4. [Detailed Design](#4-detailed-design)
5. [Database Design](#5-database-design)
6. [External Interfaces](#6-external-interfaces)
7. [Security Considerations](#7-security-considerations)
8. [Observability, Performance, Scalability & Resilience](#8-observability-performance-scalability--resilience)
9. [Deployment Architecture & SDLC](#9-deployment-architecture--sdlc)
10. [Testing Strategy](#10-testing-strategy)
11. [AI Lifecycle Management](#11-ai-lifecycle-management)
12. [Compliance and Governance](#12-compliance-and-governance)
13. [API Integration Guide (External UI)](#13-api-integration-guide-external-ui)
    - [13.1 Authentication (OAuth 2.0)](#131-authentication-oauth-20)
    - [13.2 API Endpoint Definition](#132-api-endpoint-definition)
    - [13.3 The Request Payload](#133-the-request-payload)
    - [13.4 Understanding the Response Stream](#134-understanding-the-response-stream)
    - [13.5 Error Responses](#135-error-responses)
    - [13.6 Rate Limits and Quotas](#136-rate-limits-and-quotas)
    - [13.7 Sample Integration: cURL](#137-sample-integration-curl)
14. [Cost Management](#14-cost-management)

### Part II: Future Roadmap & Architectural Extensions
15. [Data Migration and Schema Evolution](#15-data-migration-and-schema-evolution)
16. [Enterprise Reliability & Distributed Topology](#16-enterprise-reliability--distributed-topology)
    - [16.1 Multi-Region Resilience (GKE Active-Active Failovers)](#161-multi-region-resilience-gke-active-active-failovers)
    - [16.2 Gemini Enterprise Integration Resiliency](#162-gemini-enterprise-integration-resiliency)
17. [Future Architectural Extensions: Plugins, Events, & Webhooks](#17-future-architectural-extensions-plugins-events--webhooks)
    - [17.1 Plugin Patterns (MCP as Distributed Plugins)](#171-plugin-patterns-mcp-as-distributed-plugins)
    - [17.2 Event-Driven Architecture (Google Cloud Pub/Sub)](#172-event-driven-architecture-google-cloud-pubsub)
    - [17.3 Webhooks and Callback Support](#173-webhooks-and-callback-support)
    - [17.4 Observability Enhancements](#174-observability-enhancements)

### Appendices
18. [Appendices](#18-appendices)

---

# Part I: Current Architecture

## 1. Introduction
- **Purpose**: To define the architecture, design, security, and deployment strategy for the A2A Multi-Agent system on Google Cloud Agent Engine.
- **Scope**: The system encompasses a multi-agent orchestration setup utilizing the Agent2Agent (A2A) protocol, Agent Development Kit (ADK), Agent Engine, and Model Context Protocol (MCP) servers. It covers the delegation of tasks from a host agent to specialized domain agents (Cocktail and Weather) and the integration with external APIs via MCP.
- **Definitions and Acronyms**:
  - **A2A**: Agent-to-Agent protocol.
  - **ADK**: Agent Development Kit.
  - **MCP**: Model Context Protocol.
  - **SDLC**: Software Development Life Cycle.
- **References**:
  - [A2A Protocol Docs](https://a2aprotocol.ai/docs/)
  - [Gemini Enterprise A2A Registration](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent)
  - [Agent Engine A2A Usage](https://docs.cloud.google.com/agent-builder/agent-engine/use/a2a)

---

## 2. System Overview
- **System Description**: A robust, multi-agent orchestration hub where a Host Agent receives user requests and intelligently routes sub-tasks to specialized remote domain agents (e.g., Cocktail Agent, Weather Agent). These agents fetch real-world data from external APIs via containerized MCP Servers.
- **Design Goals**:
  - **Modularity**: Separation of concerns between orchestration, domain logic, and data retrieval.
  - **Observability**: Deep telemetry across the multi-hop agent execution path.
  - **Security & Resilience**: Zero-trust approach with dedicated Service Accounts, Secret Manager integration, Model Armor for LLM security, and HTTP Circuit Breakers preventing cascading failure.
  - **Automation**: Fully automated CI/CD pipelines via Terraform and Cloud Build.
- **Architecture Summary**: Serverless multi-agent orchestration (Google Cloud Agent Engine) paired with serverless data retrieval (Google Cloud Run).
- **System Context Diagram**:
  ```mermaid
  graph TD
      User[User / Analyst] --> UI[Gemini Enterprise / Custom UI]
      UI --> Auth[Authentication Layer]
      Auth --> MA[Model Armor / Threat Detection]
      MA --> Host[Host Agent / Route]
      Host -->|A2A Protocol| CocktailAgent[Cocktail Domain Agent]
      Host -->|A2A Protocol| WeatherAgent[Weather Domain Agent]
      CocktailAgent -->|MCP Protocol| CocktailMCP[Cocktail MCP Server]
      WeatherAgent -->|MCP Protocol| WeatherMCP[Weather MCP Server]
      CocktailMCP --> External1[TheCocktailDB API]
      WeatherMCP --> External2[National Weather Service API]
  ```

---

## 3. Architectural Design
- **System Architecture Diagram**:
  ```mermaid
  graph TD
      subgraph GCP Agent Engine Runtime
          HostAgent[Host Agent]
          CocktailAgent[Cocktail Agent]
          WeatherAgent[Weather Agent]
      end
      subgraph GCP Cloud Run
          CocktailMCP[Cocktail MCP Server]
          WeatherMCP[Weather MCP Server]
      end
      HostAgent -.->|Delegation| CocktailAgent
      HostAgent -.->|Delegation| WeatherAgent
      CocktailAgent ===>|StreamableHTTP| CocktailMCP
      WeatherAgent ===>|StreamableHTTP| WeatherMCP
  ```
- **Why A2A on Agent Engine vs. A2A on Cloud Run?**
  - **Native Platform Integration**: Agent Engine directly provides the `reasoningEngines` API, allowing native A2A interaction using the Vertex AI SDK without managing HTTP endpoints, routing, or complex OIDC tokens manually.
  - **Built-in Observability**: Agent Engine automatically instruments LLM execution, providing out-of-the-box Cloud Trace, Cloud Logging, and Cloud Monitoring for complex agentic workflows. Deploying raw A2A to Cloud Run requires manual instrumentation for deep execution traces.
  - **Managed Environment**: Agent Engine is specifically tailored for LangChain and agentic workloads, optimizing prompt caching, context management, and dependency pre-warming.
- **Technology Stack**: Python 3.13+, ADK, Google Cloud Agent Engine, Google Cloud Run, FastAPI/Gradio, MCP SDK, Terraform, Google Cloud Build.

---

## 4. Detailed Design
### Orchestration Tier (Host Agent)
- **Responsibilities**: Receives user intent, determines routing logic, and delegates tasks to domain agents via A2A.
- **Interfaces/APIs**: Authorized REST/gRPC from Frontend; A2A out to sub-agents.
- **State Management**: Ephemeral conversational state managed by ADK and Vertex AI sessions.

### Specialized Agent Tier
- **Responsibilities**: The Cocktail and Weather Agents execute domain-specific logic and know how to invoke their corresponding MCP tools.
- **Interfaces/APIs**: A2A in from Host Agent; MCP via StreamableHTTP out to Cloud Run.

### Data Integration Tier (MCP Servers)
- **Responsibilities**: Securely encapsulate external API interactions and expose them as standardized tools via the Model Context Protocol.
- **Interfaces/APIs**: MCP via HTTP in; standard REST/HTTP out to external services.

---

## 5. Database Design
- *Note: This application primarily relies on external APIs rather than a local relational database.*
- **State/Logging Storage**: Telemetry datastores (Google Cloud Logging, Cloud Trace) and GCS buckets for artifacts.
- **Configuration Storage**: Google Secret Manager for sensitive keys (e.g., OAuth tokens, Github PAT) and Terraform state in Google Cloud Storage.

---

## 6. External Interfaces
- **User Interface**: Gemini Enterprise and a custom Gradio testing frontend.
- **External APIs**:
  - *TheCocktailDB API*: Fetch recipes, lists, and ingredient data.
  - *National Weather Service (NWS) API*: Fetch localized weather forecasts.
- **Network Protocols**: A2A (internal RPC/REST), MCP over StreamableHTTP, standard REST/JSON.

---

## 7. Security Considerations
- **Authentication**: User authentication at the UI boundary. Service-to-service authentication is implicitly handled by Google Cloud IAM (e.g., Agent Engine invoking Cloud Run).
- **Authorization**: Strict Principle of Least Privilege. Separate Service Accounts for CI/CD runners (`a2a-multiagent-ge-cicd-cb`) and application runtime (`a2a-multiagent-ge-cicd-app`).
- **Data Protection**: Secrets (OAuth tokens, API keys) are strictly managed via Google Secret Manager. No hardcoded credentials. Terraform state is encrypted in GCS.
- **LLM Security**: Google Cloud Model Armor is enabled via Terraform (configured via Floor Settings) to automatically inspect and block malicious prompts and prevent sensitive data exfiltration in model responses.
- **Threat Model**:
  - *Unauthorized Access*: Mitigated by strict Cloud IAM permissions.
  - *Data Exfiltration via Agents*: Mitigated by scoping MCP server actions tightly (read-only downstream APIs) and by Model Armor inspection.

---

## 8. Observability, Performance, Scalability & Resilience
- **Scalability**: Both Agent Engine and Cloud Run automatically scale horizontally based on incoming traffic.
- **Resilience**:
  - **HTTP Circuit Breaker**: Implemented (using `aiobreaker`) on the shared asynchronous HTTP client. This ensures that if downstream MCP servers or external APIs experience outages, the system "fails fast" (returning HTTP 503) rather than hanging and consuming resources.
  - **Gemini Resource Retries**: The `LlmAgent` automatically retries Gemini model invocations (up to 3 attempts) for transient failures, enhancing robustness for LLM interactions.
- **Deep Observability (Telemetry)**:
  - **Cloud Logging**: Captures step-by-step agent thought processes, action selections, and runtime errors.
  - **Cloud Trace**: Crucial for A2A multi-hop requests. Enables visualization of latency across Frontend -> Host Agent -> Sub-agent -> MCP Server -> External API.
  - **Cloud Monitoring**: Tracks golden signals (Latency, Traffic, Errors, Saturation).
---

## 9. Deployment Architecture & SDLC
- **SDLC Approach**: Infrastructure-as-Code (IaC) with Terraform integrating deeply with CI/CD.
- **Environments**:
  - *CI/CD Project*: Runs Cloud Build.
  - *Staging Project*: Receives merges to `staging`.
  - *Production Project*: Receives manual deployments.
- **CI/CD Pipeline Configuration**:
  1. `pr_checks.yaml`: Triggered on PRs. Runs linting and `pytest`.
  2. `staging.yaml`: Triggered on merge to `staging`. Deploys MCP servers, extracts URLs, deploys Agent Engines via Python SDK.
  3. `deploy-to-prod.yaml`: Manual trigger requiring approval.
- **Infrastructure**: Configured natively via the `deployment/terraform/*` scripts.
- **Rollback Procedures**:
  - **Agent Engine**: If a newly deployed agent fails health checks, re-run `deploy_agents.py` with the previous known-good container image and configuration. Agent Engine supports `update()` which overwrites the existing resource in-place.
  - **MCP Servers (Cloud Run)**: Cloud Run maintains revision history. Roll back to the previous revision via `gcloud run services update-traffic <service> --to-revisions=<previous-revision>=100`.
  - **Infrastructure (Terraform)**: Revert the Terraform change in source control and re-apply. Terraform state in GCS provides an audit trail of prior configurations.
  - **Partial Failure**: If agents are partially updated (e.g., Host Agent updated but a Domain Agent deployment fails), the Host Agent should gracefully handle downstream errors via the circuit breaker (returning HTTP 503) until the Domain Agent is restored.

---

## 10. Testing Strategy
This section outlines the foundational verifications required for functional correctness, as well as the advanced enterprise-grade resilience & security testing methodologies necessary for production deployment.

### 10.1 Functional & Integration Testing
- **Unit Testing**: Testing individual agent cards, functions, and logic boundaries natively using `pytest` without invoking network calls. Executed in CI via `pr_checks.yaml` on every pull request.
- **Integration Testing**: Testing local and remote agents using A2A mocking/stubbing or hitting staging endpoints securely. Runs post-deploy in the `staging.yaml` pipeline against the staging project.
- **End-to-End Testing**: Validating the chain from the UI to the actual MCP responses. Executed manually or via scheduled pipeline against the staging environment.
- **Quality Metrics**: Maintain code linting standards utilizing `ruff` (configured in `pyproject.toml`) and enforce passing tests prior to PR merge via `pr_checks.yaml`.

### 10.2 Resilience & Security Testing
To ensure the system can withstand degraded conditions and adversarial attacks, the following advanced methodologies are required:

- **Failure Injection (Chaos Engineering)**: Simulating real-world outages to ensure graceful degradation.
  - *Network Faults*: Artificially introducing latency or dropping packets to downstream external APIs (e.g., TheCocktailDB) to validate that the HTTP Circuit Breakers trip correctly and return a `503 Service Unavailable` instead of hanging or cascading failures upstream to the Host Agent.
  - *Dependency Outages*: Shutting down a regional Cloud Run MCP server to ensure the Agent Engine Host correctly handles the failure, ideally routing to a fallback region (if a multi-cluster topology is implemented).
- **Red Teaming (Penetration Testing)**:
  - *Adversarial Prompting*: Dedicated exercises attempting to jailbreak the Host Agent, bypass system instructions, or coerce the agent into unauthorized tool invocations.
  - *Model Armor Validation*: Verifying that Google Cloud Model Armor successfully intercepts and sanitizes PII/sensitive data before it leaves the orchestrator.
- **Disaster Recovery (DR) Validation**:
  - *Infrastructure Restoration Drill*: Periodically deleting a staging environment to measure the Recovery Time Objective (RTO) required for Terraform to completely rebuild the infrastructure shell.
  - *Failover Exercises*: If the multi-region topology (Section 16.1) is adopted, intentionally failing the primary GKE cluster to validate that the Global External Application Load Balancer successfully reroutes traffic to the secondary cluster.
- **Backup & Restore Testing (State Data)**:
  - *Limitation Context*: Current conversational memory relies on `VertexAiSessionService`, which acts as a highly-available state cache but lacks enterprise Point-in-Time Recovery (PITR) or automated snapshotting.
  - *Future State Validation*: Upon migrating session state to a formal database (see Section 15: Schema Evolution), rigorous drills involving restoring corrupted tables from automated backups, validating snapshot integrity, and testing cross-region asynchronous replication lags must be executed.

### 10.3 LLM-based Evaluation Scoring
- **Mechanism**: Utilizes a scoring rubric interpreted by a Gemini model to evaluate agent responses for relevance, helpfulness, and tool routing accuracy. The rubric and test cases are maintained in [`tests/eval/`](../tests/eval/).
- **Flex Tier Integration**: Optimized for cost using Google's **Flex PayGo** (Flex Tier) with specific HTTP headers (`X-Vertex-AI-LLM-Request-Type: shared`, `X-Vertex-AI-LLM-Shared-Request-Type: flex`).
- **Verified Configuration**: Successfully verified using the `gemini-3-flash-preview` model on the `global` endpoint.

---

## 11. AI Lifecycle Management
This section documents the mechanisms for managing the agent's lifecycle, from configuration to evaluation and runtime operations.

- **Prompt and Agent Configuration Management**:
  - **Centralized Logic**: Model selections, instructions, and environment-specific variables are defined in [`agent_configs.py`](../src/a2a_agents/common/agent_configs.py).
  - **State Management**: Utilizing `VertexAiSessionService` for fully managed, persistent conversational memory for orchestrated agents, replacing local in-memory storage.
  - **Secret Management**: Sensitive credentials (OAuth tokens, API keys) are strictly managed via Google Secret Manager, ensuring no leak into the source repository.
- **Experiment Tracking (Evaluation)**:
  - **Mechanism**: A dedicated evaluation suite in [`tests/eval/`](../tests/eval/) supports rubric-based scoring.
  - **LLM-as-a-Judge**: Utilizes Gemini models on the Flex Tier (PayGo) to evaluate relevance, helpfulness, and routing accuracy.
- **Agent Operational Tooling**:
  - **Deployment Automation**: Python scripts in [`deployment/`](../deployment/) orchestrate the creation and update of Reasoning Engines and Cloud Run services.
  - **Telemetry Integration**: Native integration with Cloud Trace, Logging, and Monitoring provides real-time visibility into agentic multi-hop execution.

---

## 12. Compliance and Governance
This section details the framework for ensuring data integrity, regional compliance, and adherence to enterprise security policies.

- **Audit Logging and Retention**:
  - **Dedicated Log Storage**: GenAI inference details are routed to a custom Cloud Logging bucket (`genai-telemetry`) with an explicit **10-year retention policy**, meeting standard regulatory audit requirements.
  - **BigQuery Integration**: Logs are linked to BigQuery datasets, enabling advanced compliance reporting and periodic auditing of multi-agent interactions.
- **Data Residency and Sovereignty**:
  - **Regional Pinning**: All core infrastructure, including Agent Engine runtimes, Cloud Run services, and Logging buckets, are pinned to the `us-central1` region by default to ensure data residency compliance.
- **Policy Enforcement**:
  - **Principle of Least Privilege (PoLP)**: IAM roles are granularly assigned to the CICD and Application service accounts, strictly limiting access to required Google Cloud services (AI Platform, Secret Manager, Logging).
  - **Secure Identity**: Integration with Gemini Enterprise via OAuth2 ensures that all agent interactions are performed within a verified organizational identity context.

---

## 13. API Integration Guide (External UI)

This section details how to integrate custom Frontends, External UIs, or corporate applications (e.g., Slack bots, React Dashboards, Java/C# microservices) directly with the Agent Engine Host Agent, without relying on the Python `google-cloud-aiplatform` SDK.

### 13.1 Authentication (OAuth 2.0)
To interact with the Agent Engine API, your external UI must present a valid Google Cloud OAuth 2.0 Bearer Token.

#### Identity Requirements
The identity generating the token (e.g., a Service Account or a human Google Account) must have the following IAM role in the Google Cloud Project where the agent is hosted:
*   **Vertex AI User** (`roles/aiplatform.user`)

#### Generating a Token
**From a local CLI for testing:**
```bash
gcloud auth print-access-token
```

**From a backend service (e.g., Node.js):**
Use the Google Auth Library to automatically mint tokens. Let the library handle token rotation.
```javascript
const {GoogleAuth} = require('google-auth-library');
const auth = new GoogleAuth({
  scopes: 'https://www.googleapis.com/auth/cloud-platform'
});
const client = await auth.getClient();
const token = await client.getAccessToken();
```

### 13.2 API Endpoint Definition

The REST endpoint format for streaming interactions with a Reasoning Engine is:

**HTTP Method:** `POST`
**URL Structure:**
```text
https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}:streamQuery
```

**URL Parameters:**
*   `{LOCATION}`: The region where the agent is deployed (e.g., `us-central1`).
*   `{PROJECT_NUMBER}`: The numeric ID of the Google Cloud project (not the string project ID).
*   `{AGENT_ENGINE_ID}`: The numeric 18-digit identifier of your deployed Reasoning Engine (e.g., `123456789012345678`).

### 13.3 The Request Payload

The API expects a JSON payload defining the user input, the session context, and optional agent constraints.

**Headers Required:**
```http
Authorization: Bearer YOUR_OAUTH_TOKEN
Content-Type: application/json
```

**JSON Body Example:**
```json
{
  "input": {
    "message": "What is the weather like in Seattle and can you suggest a cocktail to drink?"
  },
  "sessionId": "usr-1234",
  "userId": "usr-1234"
}
```

*   `input.message`: The text string containing the user's prompt to the agent.
*   `sessionId`: A client-provided string used to isolate conversational memory. Must be consistent for follow-up turns by the same user to maintain conversation history. **Note:** Internally, `VertexAiSessionService` does not accept user-provided session IDs directly. The executor maintains a mapping from this client-provided `sessionId` (used as a context key) to the Vertex-assigned session ID. This is transparent to the external caller.
*   `userId`: An identifier for the caller.

### 13.4 Understanding the Response Stream

Because the agent often streams back thoughts, internal tool calls, and final responses incrementally, the `:streamQuery` API returns **Server-Sent Events (SSE)**.

Your client must keep the HTTP connection open and parse these events as they arrive.

#### Example Sequence of Server-Sent Events

**1. The Agent Begins Thinking:**
```json
data: {"content": {"role": "assistant", "parts": [{"text": "I need to check the weather first."}]}}
```

**2. The Agent Makes a Tool Call (Internal execution, ignored by UI):**
```json
data: {"content": {"parts": [{"functionCall": {"name": "WeatherAgent", "args": {"location": "Seattle"}}}]}}
```

**3. The Agent Streams the Final Answer:**
```json
data: {"content": {"role": "assistant", "parts": [{"text": "The weather in Seattle is rainy."}]}}
```
```json
data: {"content": {"role": "assistant", "parts": [{"text": " I suggest a Dark and Stormy."}]}}
```

#### Parsing Logic for the UI
When building your UI client (React, Vue, etc.), your parsing loop should concatenate `parts[].text` objects from the stream to piece together the final markdown response for the user, while safely ignoring `functionCall` objects unless your UI specifically intends to display "Debugging/Thinking" steps to end users.

### 13.5 Error Responses

The API may return the following error status codes. Clients should implement exponential backoff with jitter for retryable errors.

| Status Code | Meaning | Retryable | Notes |
|---|---|---|---|
| `400` | Bad Request — malformed JSON or missing required fields (`input.message`). | No | Fix the request payload. |
| `401` | Unauthorized — missing or expired OAuth token. | No | Refresh the Bearer token and retry. |
| `403` | Forbidden — the identity lacks `roles/aiplatform.user` on the project. | No | Grant the required IAM role. |
| `404` | Not Found — invalid `AGENT_ENGINE_ID` or `PROJECT_NUMBER`. | No | Verify the resource path. |
| `429` | Rate Limited — Gemini or Agent Engine quota exceeded. | Yes | Retry with exponential backoff. See Section 13.6. |
| `500` | Internal Server Error — unexpected agent runtime failure. | Yes | Retry with backoff; check Cloud Logging for details. |
| `503` | Service Unavailable — circuit breaker open or downstream MCP outage. | Yes | Retry after a delay; the circuit breaker will auto-recover. |

Error responses return a JSON body:
```json
{
  "error": {
    "code": 429,
    "message": "Quota exceeded for aiplatform.googleapis.com/generate_content_requests_per_minute_per_project_per_base_model.",
    "status": "RESOURCE_EXHAUSTED"
  }
}
```

### 13.6 Rate Limits and Quotas

External integrators should be aware of the following quota boundaries:

*   **Gemini Model Quotas**: Requests-per-minute (RPM) and tokens-per-minute (TPM) limits apply per project per model. Check your project's quotas in the [Google Cloud Console](https://console.cloud.google.com/iam-admin/quotas).
*   **Agent Engine Quotas**: `reasoningEngines.streamQuery` has per-project rate limits. Monitor usage via Cloud Monitoring.
*   **Recommended Client Behavior**: Implement exponential backoff starting at 1 second with a maximum of 60 seconds. Include jitter to avoid thundering-herd effects when multiple clients retry simultaneously.

### 13.7 Sample Integration: cURL
You can test the raw HTTP integration from any terminal:

```bash
# Set your variables
LOCATION="us-central1"
PROJECT_NUMBER="9876543210"
AGENT_ENGINE_ID="123456789012345678"
TOKEN=$(gcloud auth print-access-token)

# Execute the streamQuery
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_NUMBER}/locations/${LOCATION}/reasoningEngines/${AGENT_ENGINE_ID}:streamQuery" \
  -d '{
    "input": {
      "message": "Suggest a cocktail."
    },
    "sessionId": "test-session-1"
  }'
```

---

## 14. Cost Management

- **Cloud Run MCP Servers**: Configured with `min-instances=0` to scale to zero during idle periods. Set appropriate `max-instances` limits to cap spend during traffic spikes.
- **Agent Engine**: Costs are driven by Gemini model invocations (input/output tokens). Use the Flex Tier (PayGo) for non-latency-sensitive workloads such as evaluations and batch tasks to reduce per-token costs.
- **Gemini Model Selection**: Use `gemini-2.5-flash` for domain agents where speed and cost efficiency are prioritized. Reserve higher-capability models for the Host Agent's routing logic where accuracy is critical.
- **Monitoring**: Set up Cloud Billing budgets and alerts to detect unexpected cost increases. Track per-agent token consumption via Cloud Monitoring custom metrics.

---

# Part II: Future Roadmap & Architectural Extensions

> The following sections describe **proposed future capabilities** that are not yet implemented. They are included to document architectural direction, inform capacity planning, and guide future engineering investment.

---

## 15. Data Migration and Schema Evolution

> **Status:** Future Proposal — not currently implemented. The system uses `VertexAiSessionService` for session state.

Migrating from **Vertex AI Session Service** to an alternative datastore (Cloud SQL/PostgreSQL, Firestore, or Redis) presents two distinct challenges: **Data Migration** (moving existing data) and **Schema Evolution** (restructuring data to fit the target schema).

The recommended approach follows a "Contract-First" and "Backward Compatible" strategy.

### The Strategy: The Strangler Fig Pattern (Dual-Writing)

Switching datastores in a single cutover risks dropping active user sessions. The migration must be phased to maintain availability.

#### Phase 1: Define the New Contract (Schema Evolution)
Vertex AI Session data is typically unstructured or loosely structured JSON attached to a session ID. A formal database such as PostgreSQL requires strongly typed schemas.

*   **Old Vertex AI Format:**
    `Session ID: "user-123" -> Data: {"history": [...], "context": "cocktail_mode"}`
*   **New Database Schema (Alembic/PostgreSQL):**
    A relational schema enforces constraints on the migrated data.

```python
class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(String, primary_key=True)  # E.g. "user-123"
    agent_context = Column(String, nullable=False)  # E.g. "cocktail_mode"
    conversation_history = Column(JSONB)  # Structured JSON array
    last_updated = Column(TIMESTAMP, server_default=func.now())
```

#### Phase 2: Dual-Writing (Backward Compatibility)
In this phase, the ADK Agents (or Host Agent orchestrator) write to both systems but only read from the old system.

1. Deploy the new database (e.g., Cloud SQL).
2. Update the `HostingAgent` code:

```python
def update_session(session_id, new_data):
    # 1. Write to Vertex AI Session Service (The current Source of Truth)
    vertex_ai.publish_message(session_id, new_data)

    # 2. Asynchronously write to Postgres (The new system)
    try:
        db.execute("INSERT INTO agent_sessions ... ON CONFLICT DO UPDATE")
    except Exception:
        # We explicitly catch exceptions here because Postgres is NOT the
        # source of truth yet. If this fails, the app must not crash.
        log.warning("Failed to dual-write to Postgres")
```

#### Phase 3: The Backfill (Data Migration Script)
Dual-writing only captures new activity. Inactive and historical sessions must also be migrated from Vertex AI to Postgres.

A one-off backfill script performs this bulk data migration.

```python
def backfill_sessions():
    # 1. Pull all historical sessions from Vertex AI
    vertex_sessions = vertex_ai.get_all_sessions()

    for session in vertex_sessions:
        # 2. Transform the loose Vertex AI JSON into the strict Postgres schema
        transformed_data = transform_vertex_to_postgres(session)

        # 3. Insert into Postgres (skip if the dual-writer already created it)
        db.execute("INSERT INTO agent_sessions ... ON CONFLICT DO NOTHING")
```

#### Phase 4: Switch the Read Path (Cutover)
Once the backfill is complete and the dual-writer has been running reliably for a few days, a code update is deployed.

1. The `HostingAgent` reads from Postgres as the primary source.
2. If a read from Postgres fails (e.g., an edge-case race condition), the system falls back to reading from Vertex AI, ensuring backward compatibility.

```python
def get_session(session_id):
    # Try the new database first
    data = db.query(AgentSession).filter_by(id=session_id).first()
    if data:
        return data

    # Fallback to the old system just in case
    log.warning(f"Session {session_id} not in Postgres, checking Vertex")
    return vertex_ai.get_session(session_id)
```

#### Phase 5: The Cleanup (Deprecation)
Once 100% of reads are confirmed as successfully served from Postgres, a final deployment:

1. Removes the Vertex AI read fallback.
2. Removes the Vertex AI dual-write logic from the agent.
3. Deprecates and deletes the Vertex AI Session service resources.

### Summary

1. **Contract-First:** The strict Postgres schema is defined before moving any data.
2. **Backward Compatibility:** Dual-writing to both systems ensures older clients expecting Vertex AI data are not disrupted during the transition.
3. **Forward Compatibility:** The backfill script transforms old unstructured data to fit the new schema.

---

## 16. Enterprise Reliability & Distributed Topology

> **Status:** Future Proposal — the current system runs on serverless Agent Engine and Cloud Run in a single region (`us-central1`). This section describes a hypothetical GKE-based multi-region topology for organizations requiring higher availability guarantees.

Redundancy, failover, health checks, and global availability are critical considerations for production multi-agent deployment. If moving off serverless orchestration in favor of native Kubernetes, a true multi-region failover topology is necessary for true resiliency.

### 16.1 Multi-Region Resilience (GKE Active-Active Failovers)

To achieve multi-region failover with GKE, a Multi-Cluster Architecture must be implemented. A single Kubernetes cluster cannot span multiple regions. Here is how Google Cloud natively handles this fallback:

*   **Deploy Multiple Clusters:** Create two separate GKE clusters in two different regions (e.g., one in `us-central1` and one in `us-east4`).
*   **Deploy Identical Workloads:** Deploy the containerized ADK agent pods to both clusters simultaneously.
*   **The Global Routing Layer (Global Load Balancing):** Place a **Google Cloud Global External Application Load Balancer** in front of both clusters. This load balancer exposes a single, global Anycast IP address.

#### How the Failover Works
The Global Load Balancer constantly performs health checks on the agent pods deployed in both regional GKE clusters.

*   **Active-Active Routing (Latency Based):** By default, when a user in New York connects to the Global IP, the load balancer automatically routes their traffic to the `us-east4` cluster because it is physically closer, offering the lowest latency. A user in Chicago gets routed to `us-central1`.
*   **The Failover Event:** If the `us-central1` region experiences a massive outage, or agent pods within that region repeatedly fail their deep health checks, the Global Load Balancer detects this almost instantly.
*   **Traffic Restitution:** The Load Balancer automatically stops sending traffic to `us-central1` and reroutes all **new** inbound requests (even from Chicago) to the healthy backup cluster in `us-east4`. **Note:** Any in-flight SSE streams connected to the failed region will terminate — clients must implement reconnection logic to re-establish streams against the surviving region.

#### Cross-Region Session State
For session continuity across regions, a cross-region datastore is required to replicate conversation history. Options include:
*   **Firestore (Native Mode):** Multi-region replication with strong consistency. Well-suited for session state and conversation history.
*   **Cloud Spanner:** Globally consistent, strongly typed relational store. Higher cost, appropriate for enterprise-scale deployments.
*   **Memorystore for Redis (Cross-Region Replication):** Low-latency session cache with async replication for failover.

Without cross-region session replication, a user whose traffic fails over to the backup region will lose their in-progress conversation context and must start a new session.

#### GKE Native Configuration
To automate this configuration within an SDLC pipeline, Google Cloud provides two networking standards explicitly designed to program a global load balancer across split GKE clusters:
1.  **Multi-Cluster Ingress (MCI):** The classic, robust mechanism to define one centralized ingress resource that spans multiple clusters.
2.  **Multi-Cluster Gateway API:** The modernized Kubernetes-native standard for defining advanced multi-cluster routing protocols.

### 16.2 Gemini Enterprise Integration Resiliency

Organizations utilizing Gemini Enterprise as the frontline portal often ask if agents deployed on GKE can be registered with Gemini Enterprise. The current project uses an **ADK root agent on Agent Engine**, which is registered via the `adk_agent_definition` path requiring a `provisioned_reasoning_engine` resource name. However, **Agent Engine is regional** — it runs in a single region and cannot span multiple regions, making it a single point of failure in a multi-region topology. This defeats the purpose of the GKE active-active failover described in Section 16.1.

The recommended approach for enterprise resilience is to **convert the ADK root agent to a native A2A agent** and deploy it directly to GKE, where it benefits from multi-region failover via Global Load Balancing.

#### Why the ADK Root Agent on Agent Engine Cannot Handle Failover

The ADK agent registration path in Gemini Enterprise uses the `adk_agent_definition` with a `provisioned_reasoning_engine` field pointing to a specific regional Reasoning Engine resource:

```json
{
  "adk_agent_definition": {
    "provisioned_reasoning_engine": {
      "reasoning_engine": "projects/{project}/locations/us-central1/reasoningEngines/{id}"
    }
  }
}
```

This creates two fundamental limitations:
1.  **Regional lock-in**: The Reasoning Engine resource exists in exactly one region. If that region goes down, the registered agent is unreachable.
2.  **No URL-based routing**: Gemini Enterprise communicates with the agent via internal Vertex AI platform infrastructure — there is no HTTP URL to point at a Global Load Balancer.

#### Converting the ADK Root Agent to an A2A Agent

By converting the root agent to a native A2A agent, it can be deployed to GKE and registered directly with Gemini Enterprise via the [A2A agent registration path](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent), which accepts an **HTTP endpoint URL** rather than a Reasoning Engine resource name. This enables multi-region deployment behind a Global Load Balancer.

##### What the Conversion Involves

The current ADK root agent (`LlmAgent` with `RemoteA2aAgent` sub-agents) would be refactored to:

1.  **Wrap the ADK agent in an A2A server**: Use the `a2a-sdk` to expose the agent as a standalone A2A-compliant HTTP service, with an agent card at `/.well-known/agent.json` and message handling via JSON-RPC (`message/send`, `message/stream`).
2.  **Implement an `AgentExecutor`**: Similar to the existing `AdkOrchestratorAgentExecutor`, bridge between incoming A2A protocol messages and the internal ADK `Runner`.
3.  **Self-manage session state**: Replace `VertexAiSessionService` with a persistent, cross-region store (e.g., Firestore, Cloud Spanner, or Memorystore) since Agent Engine's managed session service is no longer available.
4.  **Containerize and deploy to GKE**: Package the A2A agent as a Docker container with health check endpoints, deploy to multi-region GKE clusters with appropriate HPA scaling.

##### Architecture

```
Gemini Enterprise
    │
    │  (HTTPS — A2A JSON-RPC, with OIDC auth token)
    │
    ▼
Global External Application Load Balancer
    │  (health-checked, latency-based routing)
    │
    ├──────────────────────────┐
    ▼                          ▼
GKE Cluster (us-central1)    GKE Cluster (us-east4)
┌─────────────────────┐      ┌─────────────────────┐
│ A2A Root Agent      │      │ A2A Root Agent      │
│  - /.well-known/    │      │  - /.well-known/    │
│    agent.json       │      │    agent.json       │
│  - ADK Runner       │      │  - ADK Runner       │
│  - RemoteA2aAgent   │      │  - RemoteA2aAgent   │
│    sub-agents       │      │    sub-agents       │
└────────┬────────────┘      └────────┬────────────┘
         │                            │
         │  (A2A JSON-RPC over HTTPS) │
         ▼                            ▼
    GKE Sub-Agents              GKE Sub-Agents
    (Cocktail, Weather)         (Cocktail, Weather)
```

##### Key Differences from the Current Architecture

| Aspect | Current (ADK on Agent Engine) | Target (A2A on GKE) |
|---|---|---|
| Registration path | `adk_agent_definition` + `provisioned_reasoning_engine` | A2A agent registration with HTTP endpoint URL |
| Root agent location | Agent Engine (single region) | GKE (multi-region behind Global LB) |
| GE → Agent transport | Internal Vertex AI platform | HTTPS (direct HTTP call to Global LB) |
| Multi-region failover | **Not supported** — Agent Engine is regional | **Supported** — Global LB routes to healthy cluster |
| Session management | `VertexAiSessionService` (managed) | Self-managed cross-region store (Firestore, Spanner) |
| Auth | Platform-managed IAM | OIDC token validation at the GKE ingress |
| Infrastructure control | Limited (managed platform) | Full (Kubernetes-native scaling, health checks, HPA) |

#### Multi-Region Failover with Gemini Enterprise

When the A2A root agent is deployed to multi-region GKE clusters behind a Global External Application Load Balancer:

1.  **Registration**: Gemini Enterprise registers the A2A agent with the Global LB URL (e.g., `https://my-root-agent.corp.internal`).
2.  **Active-Active Routing**: The Global LB routes Gemini Enterprise requests to the nearest healthy GKE cluster based on latency.
3.  **Failover Event**: If a region fails, the LB automatically reroutes all subsequent requests to the surviving cluster. No re-registration with Gemini Enterprise is required — the URL remains the same.
4.  **Session Continuity**: Cross-region session state replication (via Firestore or Spanner) ensures users retain their conversation context after failover (see Section 16.1).

#### Protocol Summary

| Hop | From | To | Protocol | Transport |
|---|---|---|---|---|
| 1 | Gemini Enterprise | A2A Root Agent (via Global LB) | A2A (JSON-RPC) | HTTPS |
| 2 | A2A Root Agent | GKE Sub-Agent | A2A (JSON-RPC) | HTTPS |
| 3 | GKE Sub-Agent | MCP Server / External API | MCP (StreamableHTTP) or REST | HTTPS |

---

## 17. Future Architectural Extensions: Plugins, Events, & Webhooks

> **Status:** Future Proposal — these patterns are not currently implemented but represent natural extensions of the existing architecture.

The current architecture is prioritized for synchronous orchestration, but it is deeply extensible. If the system needs to scale to handle long-running background tasks or dynamic feature loading, the following enterprise patterns will integrate seamlessly:

### 17.1 Plugin Patterns (MCP as Distributed Plugins)
Traditional applications use "Plugin Architectures" by loading local SDKs, dynamic libraries (`.whl`, `.so`), or relying on framework-specific hooks (e.g., WordPress plugins).

This architecture natively implements a **Distributed Plugin Pattern** via the Model Context Protocol (MCP).
*   **How it works:** The Host Agent does not need to deploy code updates to gain new capabilities. Instead, independent engineering teams can deploy their own Cloud Run services (MCP Servers).
*   **Integration (Future):** The Host Agent would dynamically read the `.well-known/mcp` configuration over HTTP, instantly "plugging in" the external tools without restarting or rebuilding the core Agent Engine environment. This is a decoupled, language-agnostic plugin realization. *Note: Currently, MCP server URLs are configured at deploy time via environment variables. Dynamic discovery is a planned enhancement.*

### 17.2 Event-Driven Architecture (Google Cloud Pub/Sub)
Currently, A2A delegation is synchronous (the Host Agent holds the HTTP connection open while waiting for the Domain Agent). For long-running research tasks (e.g., generating a 50-page financial report), this synchronous pattern will timeout.

To address this, an **Event-Driven Architecture (EDA)** is proposed.
*   **The Shift:** Instead of a direct HTTP `streamQuery`, the Host Agent acts as a Message Publisher.
*   **Implementation:** When the user asks for a massive report, the Host Agent immediately publishes an event to a Google Cloud Pub/Sub topic (e.g., `topic: generate-report`) with a payload defining the user intent. It then immediately returns an HTTP `202 Accepted` to the Frontend UI, freeing up compute.
*   **Agent Subscribers:** Domain Agents (configured as Cloud Run specialized workers) act as "Push Subscribers" to the Pub/Sub topic. They pick up the event, run for as long as needed, and execute their localized tools.

### 17.3 Webhooks and Callback Support
If the system moves to the Event-Driven model described above, the Frontend UI no longer gets an immediate HTTP response.

To close the loop, the architecture must support **Webhooks/Callbacks**.
*   **The Contract:** The external caller (Frontend, Slack, or a 3rd-party microservice) must provide a target Webhook URL in their initial payload.
    ```json
    {
      "input": { "message": "Research cocktail history for 5 hours." },
      "callback_url": "https://my-ui.internal/api/webhook/reports",
      "sessionId": "usr-123"
    }
    ```
*   **The Execution:** When the Domain Agent (running asynchronously off a Pub/Sub queue) finally generates the report, it is programmed to send a final HTTP POST request back to the `callback_url`. The external UI receives that payload and updates the user's dashboard notifying them the document is ready.

### 17.4 Observability Enhancements
*   **Alerting System:** Set up Cloud Monitoring Alert Policies based on Error Rates (>5%) or high latency (P99 > 10s). Route alerts to a Pub/Sub topic which triggers a Cloud Function to notify Google Chat or Slack.
*   **User Feedback Loop:** Implement thumbs up/down in the UI. Store feedback in BigQuery. Periodically run analytical evaluations against traces to capture hallucination rates and improve prompt design iteratively.

---

## 18. Appendices
- **Directory Structure**: Refer to `README.md` for standard repository mapping.
- **Change History**:
  - [v1.0.0, 2025-07-15, Initial Architecture Design]
  - [v1.0.1, 2025-08-27, Added AI Lifecycle Management section]
  - [v1.0.2, 2025-09-16, Added Compliance and Governance section]
  - [v1.0.3, 2026-03-03, Added Gemini retry options and Vertex AI Session Services]
  - [v1.0.4, 2026-03-05, Fixed VertexAiSessionService session ID mapping in AdkBaseMcpAgentExecutor and AdkOrchestratorAgentExecutor (user-provided session_id not supported); fixed Agent Engine deployment to use vertexai.agent_engines instead of google.genai.Client; added jq to Cloud Build Alpine image for Terraform shells step]
  - [v1.0.5, 2026-03-08, Added Schema Evolution section detailing Alembic/PostgreSQL migration and Vertex Session DB transitions]
  - [v1.0.6, 2026-03-08, Added API Integration Guide (External UI) covering raw REST and OAuth 2.0 connectivity]
  - [v1.0.7, 2026-03-08, Added Future Architectural Extensions covering Plugin Patterns, Event-Driven Pub/Sub, and Webhooks]
  - [v1.0.8, 2026-03-08, Added Enterprise Reliability & Distributed Topology section summarizing GKE multi-region failovers and Gemini Enterprise integration]
  - [v1.0.9, 2026-03-08, Reorganized into Part I (Current Architecture) and Part II (Future Roadmap); renumbered sections; added status callouts to future sections; normalized tone; moved observability enhancements to roadmap]
  - [v1.1.0, 2026-03-08, Rewrote Section 16.2 — Agent Engine is regional and cannot support multi-region failover; recommended converting ADK root agent to A2A agent for direct GKE deployment and Gemini Enterprise registration via A2A path; added multi-region architecture diagram and protocol summary]
