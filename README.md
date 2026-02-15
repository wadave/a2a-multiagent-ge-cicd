# A2A Multiagent Gemini Enterprise CI/CD

This repository provides an automated CI/CD pipeline to deploy an Agent-to-Agent (A2A) Google Cloud infrastructure with Gemini Enterprise (GE) Agentspace.

Instead of running manual deployment notebook cells, this solution is fully automated via Cloud Build using Python applications.

## Architecture

This project consists of 4 core Agent components deployed natively via Python modules, executing in Vertex AI Agent Engine. It uses 2 FastMCP servers hosted as Cloud Run apps:

1. **Weather MCP Server**: An external tool service for weather
2. **Cocktail MCP Server**: An external tool service for cocktails
3. **Weather Agent**: Connected to the Weather MCP
4. **Cocktail Agent**: Connected to the Cocktail MCP
5. **Hosting Agent**: Orchestrates and coordinates the Weather and Cocktail remote A2A Agents
6. **Frontend UI**: Simple web interface for the system

## CI/CD Pipeline Workflow

Google Cloud Build triggers from your git actions. Refer to `.cloudbuild/staging.yaml` and `.cloudbuild/deploy-to-prod.yaml` for complete environment configuration.

1. **Build & Deploy MCP Servers:** Deploys FastMCP endpoints on Cloud Run
2. **Deploy A2A Agents:** Deploys Weather and Cocktail capabilities into Agent Engine
3. **Deploy Hosting Agent:** Reaps the endpoints from the sub-agents and deploys as the Master Orchestrator
4. **Deploy Frontend:** Hosts the web portal connected to the Hosting Agent
5. **Register to Gemini Enterprise:** Automatically links the Hosting Agent Engine configuration directly into your Agentspace App.

### Setup Instructions

1. Link your git repository to **Google Cloud Build**
2. In Cloud Build -> Triggers -> Settings, ensure the variable `_PROD_PROJECT_ID` (or `_STAGING_PROJECT_ID`) is provided.
3. Replace the following substitution variables at the bottom of the Cloud Build YAML files, or provide them dynamically via Cloud Build parameters:
   - `_PROJECT_NUMBER`
   - `_AS_APP`: Agentspace App ID
   - `_AUTH_ID`: Secret identifier for the Google OAuth identity.
4. Push to the `staging` or `main` branches to begin execution.
