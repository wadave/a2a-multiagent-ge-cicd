# Software Design Document (SDD): A2A Multi-Agent on Agent Engine

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
- **Future Alarm & Feedback Architecture Suggestions**:
  - *Alerting System*: Setup Cloud Monitoring Alert Policies based on Error Rates (>5%) or high latency (P99 > 10s). Route these alerts to a Pub/Sub topic which triggers a Cloud Function to notify Google Chat or Slack.
  - *User Feedback Loop*: Implement thumbs up/down in the UI. Store this feedback in BigQuery. Periodically run analytical evaluations against traces to capture hallucination rates and improve prompt design iteratively.

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

---

## 10. Testing Strategy
- **Unit Testing**: Testing individual agent cards, functions, and logic boundaries natively using `pytest` without invoking network calls.
- **Integration Testing**: Testing local and remote agents using A2A mocking/stubbing or hitting staging endpoints securely.
- **End-to-End Testing**: Validating the chain from the UI to the actual MCP responses.
- **LLM-based Evaluation Scoring**:
  - **Mechanism**: Utilizes a scoring rubric interpreted by a Gemini model to evaluate agent responses for relevance, helpfulness, and tool routing accuracy.
  - **Flex Tier Integration**: Optimized for cost using Google's **Flex PayGo** (Flex Tier) with specific HTTP headers (`X-Vertex-AI-LLM-Request-Type: shared`, `X-Vertex-AI-LLM-Shared-Request-Type: flex`).
  - **Verified Configuration**: Successfully verified using the `gemini-3-flash-preview` model on the `global` endpoint.
- **Quality Metrics**: Maintain code linting standards utilizing tools mapped in `uv` and ensure high coverage prior to PR passing.

---

## 11. AI Lifecycle Management
This section documents the mechanisms for managing the agent's lifecycle, from configuration to evaluation and runtime operations.

- **Prompt and Agent Configuration Management**:
  - **Centralized Logic**: Model selections, instructions, and environment-specific variables are defined in [agent_configs.py](file:///usr/local/google/home/wangdave/remote_ws/projects/a2a-multiagent-ge-cicd/src/a2a_agents/common/agent_configs.py).
  - **State Management**: Utilizing `VertexAiSessionService` for fully managed, persistent conversational memory for orchestrated agents, replacing local in-memory storage.
  - **Secret Management**: Sensitive credentials (OAuth tokens, API keys) are strictly managed via Google Secret Manager, ensuring no leak into the source repository.
- **Experiment Tracking (Evaluation)**:
  - **Mechanism**: A dedicated evaluation suite in [tests/eval/](file:///usr/local/google/home/wangdave/remote_ws/projects/a2a-multiagent-ge-cicd/tests/eval/) supports rubric-based scoring.
  - **LLM-as-a-Judge**: Utilizes Gemini models on the Flex Tier (PayGo) to evaluate relevance, helpfulness, and routing accuracy.
- **Agent Operational Tooling**:
  - **Deployment Automation**: Python scripts in [deployment/](file:///usr/local/google/home/wangdave/remote_ws/projects/a2a-multiagent-ge-cicd/deployment/) orchestrate the creation and update of Reasoning Engines and Cloud Run services.
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

## 13. Appendices
- **Directory Structure**: Refer to `README.md` for standard repository mapping.
- **Change History**: 
  - [v1.0.0, Current Date, Initial Architecture Design]
  - [v1.0.1, 2026-02-27, Added AI Lifecycle Management section]
  - [v1.0.2, 2026-02-27, Added Compliance and Governance section]
  - [v1.0.3, 2026-03-03, Added Gemini retry options and Vertex AI Session Services]
  - [v1.0.4, 2026-03-05, Fixed VertexAiSessionService session ID mapping in AdkBaseMcpAgentExecutor and AdkOrchestratorAgentExecutor (user-provided session_id not supported); fixed Agent Engine deployment to use vertexai.agent_engines instead of google.genai.Client; added jq to Cloud Build Alpine image for Terraform shells step]
