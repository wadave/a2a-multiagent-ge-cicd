# A2A Multi-Agent on Agent Engine

> **DISCLAIMER**: THIS DEMO IS INTENDED FOR DEMONSTRATION PURPOSES ONLY. IT IS NOT INTENDED FOR USE IN A PRODUCTION ENVIRONMENT.
>
> **Important**: A2A is a work in progress (WIP) thus, in the near future there might be changes that are different from what demonstrated here.

> **Important**: Please run it in **Cloud Shell** to ensure you have the proper permissions.

This document describes a multi-agent set up using Agent2Agent (A2A), ADK, Agent Engine, MCP servers, and the ADK extension for A2A. It provides an overview of how the A2A protocol works between agents, and how the extension is activated on the server and included in the response.

## Overview

This application demonstrates the integration of Google's Open Source frameworks Agent2Agent (A2A) and Agent Development Kit (ADK) for multi-agent orchestration with Model Context Protocol (MCP) clients. The application features a host agent coordinating tasks between specialized remote A2A agents that interact with various MCP servers to fulfill user requests.

### Architecture

The application utilizes a multi-agent architecture where a host agent delegates tasks to remote A2A agents (Cocktail and Weather) based on the user's query. These agents then interact with corresponding remote MCP servers.

**Host Agent is built using Agent Engine server and ADK agents.**

![architecture](asset/a2a_adk_diagram.png)

### Application Screenshot

![screenshot](asset/screenshot.png)

## Core Components

### Agents

The application employs three distinct agents:

- **Host Agent:** An ADK `LlmAgent` that receives user queries, determines the required task(s), and delegates to the appropriate specialized agent(s) via `RemoteA2aAgent` sub-agents.
- **Cocktail Agent:** Handles requests related to cocktail recipes and ingredients by interacting with the Cocktail MCP server.
- **Weather Agent:** Manages requests related to weather forecasts by interacting with the Weather MCP server.

### MCP Servers and Tools

The agents interact with the following MCP servers:

1. **Cocktail MCP Server** (Cloud Run)
    - Provides 5 tools:
        - `search cocktail by name`
        - `list all cocktail by first letter`
        - `search ingredient by name`
        - `list random cocktails`
        - `lookup full cocktail details by id`
2. **Weather MCP Server** (Cloud Run)
    - Provides 3 tools:
        - `get weather forecast by city name`
        - `get weather forecast by coordinates`
        - `get weather alert by state code`

## Project Structure

```
.
├── .cloudbuild/                  # Cloud Build CI/CD pipelines
│   ├── pr_checks.yaml
│   ├── staging.yaml
│   └── deploy-to-prod.yaml
├── asset/                        # Architecture diagrams, screenshots
├── deployment/
│   ├── deploy_agents.py          # Python script to deploy all agents
│   └── terraform/                # Terraform IaC for Agent Engine, IAM, etc.
├── scripts/                      # Utility scripts
├── src/
│   ├── a2a_agents/               # Agent source code (workspace package)
│   │   ├── common/               # Shared executors, auth utilities
│   │   ├── cocktail_agent/       # Cocktail agent card, executor, ADK agent
│   │   ├── hosting_agent/        # Host agent (LlmAgent + RemoteA2aAgent)
│   │   └── weather_agent/        # Weather agent card, executor, ADK agent
│   ├── frontend/                 # Gradio frontend (connects via A2A)
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── pyproject.toml
│   └── mcp_servers/              # MCP server implementations
│       ├── cocktail_mcp_server/
│       └── weather_mcp_server/
├── tests/
│   ├── conftest.py               # Adds src/ to sys.path
│   ├── unit/                     # Unit tests (agent cards, servers, logic)
│   ├── integration/              # Integration tests (local + remote agents)
│   ├── eval/                     # Evaluation suite (evalsets, config)
│   └── load_test/                # Locust load tests
├── pyproject.toml
├── uv.lock
├── Makefile
└── README.md
```

## Example Usage

Here are some example questions you can ask the chatbot:

- `Please get cocktail margarita id and then full detail of cocktail margarita`
- `Please list a random cocktail`
- `Please get weather forecast for New York`
- `What is the weather in Houston, TX?`

## Setup and Deployment

### Prerequisites

1. [Python 3.12+](https://www.python.org/downloads/)
2. [gcloud SDK](https://cloud.google.com/sdk/docs/install)
3. [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
4. Google Cloud project with Vertex AI API enabled

### Local Testing

#### 1. Install dependencies

```bash
uv sync
```

#### 2. Configure environment

Create `src/a2a_agents/.env` with:

```bash
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
PROJECT_ID="your-project-id"
PROJECT_NUMBER="your-project-number"
CT_AGENT_URL="https://..."   # Deployed cocktail agent A2A URL
WEA_AGENT_URL="https://..."  # Deployed weather agent A2A URL
CT_MCP_SERVER_URL="https://..."
WEA_MCP_SERVER_URL="https://..."
```

#### 3. Run hosting agent locally

```bash
python tests/integration/test_hosting_agent_local.py
```

#### 4. Run the frontend locally

```bash
cd src/frontend
uv run python main.py
# Open http://localhost:8080
```

### Deployment

#### Infrastructure (Terraform)

The `deployment/terraform/` directory contains Terraform configuration for:

- Agent Engine resources (Cocktail, Weather, Hosting agents)
- Service accounts and IAM
- Cloud Build triggers (CI/CD)
- Storage buckets

```bash
cd deployment/terraform
terraform init
terraform apply
```

#### CI/CD Pipeline

Pushing to the `staging` branch triggers the Cloud Build pipeline (`.cloudbuild/staging.yaml`) which:

1. Deploys MCP servers to Cloud Run
2. Deploys all agents to Agent Engine
3. Deploys the Gradio frontend to Cloud Run

### Running Tests

```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests (requires deployed agents)
uv run pytest tests/integration/ -m integration

# Evaluation
uv run python tests/eval/run_evaluation.py

# Load tests (requires locust)
cd tests/load_test
locust -f load_test_comprehensive.py
```

## Disclaimer

**Important**: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks. Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.

## License

This project is licensed under the [MIT License](LICENSE).
