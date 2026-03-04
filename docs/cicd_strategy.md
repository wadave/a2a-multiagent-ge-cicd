# CI/CD Deployment Strategy

This document outlines the pipeline architecture and rationale for deploying the Multi-Agent (A2A) Google Enterprise application. The deployment leverages Google Cloud Build, Docker, the Google Cloud CLI (`gcloud`), the Vertex AI Python SDK, and Terraform to securely deploy and register the agent logic.

## 🏗️ Pipeline Architecture & Flow

The pipeline executes a structured sequence in `.cloudbuild/staging.yaml`, blending different tools for their respective strengths in infrastructure control and application delivery:

1. **Parallel MCP Server Deployment (`gcloud`)**
   - Builds Docker images for the FastMCP servers (Cocktail and Weather).
   - Deploys them in parallel to Cloud Run as private internal microservices (`--no-allow-unauthenticated`).
   - Retrieves the deployed Cloud Run URLs dynamically for subsequent steps.

2. **Agent Engine Deployment (Vertex AI Python SDK)**
   - Resolves and installs fast package dependencies securely using Astral's `uv`.
   - Executes `deploy_agents.py` to launch the deployment script using the `vertexai` library.
   - Programmatically packages and registers the Reasoning Engines (A2A Agents) using the Python classes and tool signatures.
   - Extracts and persists the newly created Agent Engine Instance ID.

3. **Frontend Service Deployment (`gcloud`)**
   - Builds the user-facing web interface.
   - Deploys the service to Cloud Run with public access (`--allow-unauthenticated`).
   - Injects the dynamic Agent Engine Instance ID via environment variables so the UI can communicate with the agent backend.

4. **Agent Registration & Security Integrations (Terraform)**
   - Provisions necessary fine-grained IAM roles.
   - Formally configures the OAuth setup (retrieving secure Client Secrets from Google Secret Manager).
   - Links and "Registers" the specific Vertex AI Hosting Agent instance with the broader Gemini Enterprise interface, creating the bridge required for user interaction.

## ⚖️ The "App vs. Infra Divide"

A core architectural principle of this deployment strategy is the "App vs. Infra Divide". Instead of using a single tool (like Terraform) to manage absolutely everything, responsibilities are split based on the lifecycle of the components:

- **Infrastructure (Infra)**: Foundational, slow-moving resources like GCP Projects, Service Accounts, IAM bindings, Secret Manager secrets, and API enablements. These are managed by **Terraform**. They represent the "platform" and rarely change.
- **Application (App)**: Fast-moving components like Docker image hashes, specific Python code versions, and Agent Engine definitions. These change with almost every commit and are managed by **`gcloud`** and the **Python SDK**.

**Why use this approach?**

1.  **Velocity**: If Terraform managed the Cloud Run services directly, every code commit would require a Terraform plan/apply cycle just to update a Docker image SHA. This heavily couples application deployments to infrastructure state, introducing bottlenecks and potential state lock issues in CI/CD.
2.  **Safety**: By separating concerns, application developers can push new code (via `gcloud` or the Python SDK) without needing permissions to mutate core infrastructure (IAM roles, network configurations).
3.  **Simplicity**: It prevents the Terraform state file from churning constantly. Terraform is invoked only when structural changes are needed (e.g., registering a new OAuth client), while the CI/CD pipeline rapidly iterates the application logic.

## 🛠️ Tooling Breakdown & Rationale

Instead of monolithic deployment scripts or attempting to deploy all logic strictly via Terraform, the pipeline smartly implements the "App vs. Infra divide"—a hallmark best practice for modern CI/CD architecture.

### 1. `gcloud` CLI

- **Target Component:** Stateless execution layers (The MCP Action Servers and the React Frontend).
- **Rationale:** Using `gcloud run deploy` is better suited for continuous application deployment compared to native Terraform. Pushing continuous deployment via Terraform inextricably couples your long-term infrastructure state file directly to rapidly changing Docker image SHAs, which can stall operations if state locking occurs or updates become out of sync.

### 2. Vertex AI Python SDK (`vertexai`)

- **Target Component:** Agent Engine / Reasoning Engine payloads.
- **Rationale:** While Terraform _can_ provision the `google_vertex_ai_reasoning_engine` resource natively, it is mechanically cumbersome for developer workflows. Developers would have to manually bundle independent `.tar.gz` payloads, push them to Cloud Storage, and structure dependencies rigidly in HCL strings. The Python SDK handles code introspection, dependency bundling, and Cloud Storage staging natively executing dynamically in Python.

### 3. Terraform (HashiCorp)

- **Target Component:** Identity Management, Application Security, and Gemini Enterprise Control Plane mapping.
- **Rationale:** Setting up OAuth tokens, resolving Secret Manager variables, defining the core platform project scope, and registering an API endpoint into the broader Gemini Enterprise space are inherently stateful platform resources. Running explicit shell scripts or `gcloud` commands for structural access provisioning is brittle and difficult to audit. Terraform ensures safe, declarative tracking to guarantee the application components have the exact rights they need (`-target` is used explicitly here to navigate safe partial dependency resolution at deployment time).
