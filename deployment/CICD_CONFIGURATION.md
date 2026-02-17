# CI/CD Configuration Guide

This document describes how the CI/CD pipeline is configured to avoid hard-coded values and use dynamic environment variables.

## Overview

All configuration values are managed through:
1. **Terraform variables** (deployment/terraform/variables.tf)
2. **Terraform substitutions** (deployment/terraform/build_triggers.tf)
3. **Cloud Build YAML files** (.cloudbuild/*.yaml)
4. **Runtime environment variables** (passed to deployment scripts)

## Key Principles

1. **No Hard-Coded Values**: All project IDs, regions, service accounts, etc. are passed as variables
2. **Latest Source Code**: All deployments use the latest code from `src/` directory
3. **Trailing Slash for MCP**: MCP server URLs automatically get `/mcp/` appended with trailing slash
4. **Dynamic Agent IDs**: Frontend automatically gets the hosting agent ID after deployment

## Configuration Flow

```
terraform.tfvars
    ↓
Terraform Variables (variables.tf)
    ↓
Build Trigger Substitutions (build_triggers.tf)
    ↓
Cloud Build YAML (_SUBSTITUTION_VARS)
    ↓
Environment Variables (export VAR=value)
    ↓
Deployment Scripts (deploy_agents.py)
    ↓
Deployed Resources
```

## Terraform Configuration

### Required Variables

Set these in `deployment/terraform/terraform.tfvars`:

```hcl
# Project IDs
staging_project_id     = "your-staging-project"
prod_project_id        = "your-prod-project"
cicd_runner_project_id = "your-cicd-project"

# Project Numbers (NOT IDs)
staging_project_number = "123456789012"
prod_project_number    = "234567890123"

# Region
region = "us-central1"

# GitHub
repository_owner = "your-github-org"
repository_name  = "your-repo"
```

### Variable Definitions

**deployment/terraform/variables.tf** defines all variables:
- `staging_project_id` / `prod_project_id` - GCP project IDs
- `staging_project_number` / `prod_project_number` - GCP project numbers
- `region` - Deployment region
- `repository_owner` / `repository_name` - GitHub configuration
- Service account roles and permissions
- Optional: Agentspace configuration

### Build Trigger Substitutions

**deployment/terraform/build_triggers.tf** passes variables to Cloud Build:

**Staging Trigger:**
```hcl
substitutions = {
  _STAGING_PROJECT_ID          = var.staging_project_id
  _PROJECT_NUMBER              = var.staging_project_number
  _APP_SERVICE_ACCOUNT_STAGING = google_service_account.app_sa["staging"].email
  _REGION                      = var.region
}
```

**Production Trigger:**
```hcl
substitutions = {
  _PROD_PROJECT_ID            = var.prod_project_id
  _PROJECT_NUMBER             = var.prod_project_number
  _APP_SERVICE_ACCOUNT_PROD   = google_service_account.app_sa["prod"].email
  _REGION                     = var.region
  _AS_APP                     = var.as_app_prod      # Optional
  _AUTH_ID                    = var.auth_id_prod     # Optional
}
```

## Cloud Build Pipeline

### Staging Pipeline (.cloudbuild/staging.yaml)

**Key Features:**
1. **No Hard-Coded Values**: All values come from Terraform substitutions
2. **MCP URL Trailing Slash**: Automatically appends `/mcp/` to MCP server URLs
3. **Latest Source Code**: Builds from `./src/` directory
4. **Dynamic Environment Variables**: Sets env vars from substitutions

**MCP URL Handling:**
```bash
# Automatically appends /mcp/ with trailing slash
echo "$(gcloud run services describe cocktail-mcp-ge-staging --region ${_REGION} --format 'value(status.url)')/mcp/" > /workspace/cocktail_url.txt
```

**Agent Deployment:**
```bash
export CT_MCP_SERVER_URL=$(cat /workspace/cocktail_url.txt)
export WEA_MCP_SERVER_URL=$(cat /workspace/weather_url.txt)
export PROJECT_ID="${_STAGING_PROJECT_ID}"
export GOOGLE_CLOUD_REGION="${_REGION}"
export APP_SERVICE_ACCOUNT="${_APP_SERVICE_ACCOUNT_STAGING}"
export DISPLAY_NAME_SUFFIX="Staging"

uv run python deployment/deploy_agents.py
```

**Frontend Deployment:**
```bash
# Dynamic agent ID from deployment output
HOSTING_AGENT_RESOURCE=$(cat /workspace/hosting_agent_id.txt)
AGENT_ENGINE_ID=$(echo "$HOSTING_AGENT_RESOURCE" | awk -F'/' '{print $NF}')

gcloud run deploy a2a-frontend-ge2 \
  --set-env-vars "PROJECT_ID=${_STAGING_PROJECT_ID},PROJECT_NUMBER=${_PROJECT_NUMBER},AGENT_ENGINE_ID=${AGENT_ENGINE_ID},GOOGLE_CLOUD_LOCATION=${_REGION}"
```

### Production Pipeline (.cloudbuild/deploy-to-prod.yaml)

Same structure as staging, but:
- Uses `_PROD_PROJECT_ID` instead of `_STAGING_PROJECT_ID`
- Uses `_APP_SERVICE_ACCOUNT_PROD`
- Sets `DISPLAY_NAME_SUFFIX="Prod"`
- Optional: Registers agent to Agentspace if `_AS_APP` and `_AUTH_ID` are set

## Deployment Script

**deployment/deploy_agents.py** uses environment variables:

```python
project_id = os.environ.get("PROJECT_ID")
location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
service_account = os.environ.get("APP_SERVICE_ACCOUNT")
bucket_name = os.environ.get("BUCKET_NAME", f"{project_id}-bucket")
display_name_suffix = os.environ.get("DISPLAY_NAME_SUFFIX", "Staging")

ct_mcp_url = os.environ.get("CT_MCP_SERVER_URL")
wea_mcp_url = os.environ.get("WEA_MCP_SERVER_URL")
```

**Important**: The script changes to the `src/` directory to ensure it uses the latest source code:

```python
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
os.chdir(src_dir)
```

## MCP Trailing Slash Problem

**Problem:** FastMCP servers require `/mcp/` path with trailing slash, but without it:
- `/mcp` → 307 Temporary Redirect → `/mcp/`
- This redirect breaks MCP session creation

**Solution:** Both Cloud Build pipelines automatically append `/mcp/` with trailing slash:

```bash
# Line 67-68 in staging.yaml and deploy-to-prod.yaml
echo "$(gcloud run services describe cocktail-mcp-ge-staging --region ${_REGION} --format 'value(status.url)')/mcp/" > /workspace/cocktail_url.txt
echo "$(gcloud run services describe weather-mcp-ge-staging --region ${_REGION} --format 'value(status.url)')/mcp/" > /workspace/weather_url.txt
```

This ensures:
1. ✓ URLs always have trailing slash
2. ✓ No 307 redirects
3. ✓ MCP sessions work correctly
4. ✓ Agents can access MCP tools

## Environment Variables Reference

### Cloud Build Substitutions (from Terraform)

| Variable | Source | Description |
|----------|--------|-------------|
| `_STAGING_PROJECT_ID` | `var.staging_project_id` | Staging GCP project ID |
| `_PROD_PROJECT_ID` | `var.prod_project_id` | Production GCP project ID |
| `_PROJECT_NUMBER` | `var.staging_project_number` or `var.prod_project_number` | GCP project number |
| `_REGION` | `var.region` | Deployment region |
| `_APP_SERVICE_ACCOUNT_STAGING` | `google_service_account.app_sa["staging"].email` | Staging service account |
| `_APP_SERVICE_ACCOUNT_PROD` | `google_service_account.app_sa["prod"].email` | Production service account |
| `_AS_APP` | `var.as_app_prod` | Optional: Agentspace App ID |
| `_AUTH_ID` | `var.auth_id_prod` | Optional: OAuth Client ID |

### Runtime Environment Variables (in deploy step)

| Variable | Description |
|----------|-------------|
| `CT_MCP_SERVER_URL` | Cocktail MCP server URL (with `/mcp/`) |
| `WEA_MCP_SERVER_URL` | Weather MCP server URL (with `/mcp/`) |
| `PROJECT_ID` | GCP project ID for deployment |
| `GOOGLE_CLOUD_REGION` | GCP region |
| `APP_SERVICE_ACCOUNT` | Service account email |
| `DISPLAY_NAME_SUFFIX` | Environment suffix (Staging/Prod) |
| `BUCKET_NAME` | GCS bucket for agent staging |
| `REQUIREMENTS_FILE` | Path to requirements.txt |

## Setup Instructions

### 1. Configure Terraform Variables

```bash
cd deployment/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 2. Get Project Numbers

```bash
# Get project numbers (NOT IDs)
gcloud projects describe YOUR_STAGING_PROJECT_ID --format="value(projectNumber)"
gcloud projects describe YOUR_PROD_PROJECT_ID --format="value(projectNumber)"
```

### 3. Apply Terraform

```bash
terraform init
terraform plan
terraform apply
```

### 4. Verify Build Triggers

```bash
gcloud builds triggers list --project=YOUR_CICD_PROJECT_ID
```

Check that substitutions are set correctly in each trigger.

## Troubleshooting

### MCP Connection Failures

**Symptom:** 307 Redirect errors in agent logs

**Solution:** Verify MCP URLs have trailing slash:
```bash
# In Cloud Build logs, check:
echo "Cocktail MCP URL: $(cat /workspace/cocktail_url.txt)"
# Should show: https://...run.app/mcp/  (with trailing slash)
```

### Missing Environment Variables

**Symptom:** Deployment script fails with missing variables

**Solution:** Check build trigger substitutions:
```bash
gcloud builds triggers describe TRIGGER_NAME --project=CICD_PROJECT_ID
```

### Wrong Agent IDs in Frontend

**Symptom:** Frontend can't connect to agent

**Solution:** Verify hosting_agent_id.txt is being written and read:
```bash
# In deployment logs, check for:
# "Wrote hosting agent ID to /workspace/hosting_agent_id.txt"
```

## Best Practices

1. **Never Hard-Code Values**: Always use variables and substitutions
2. **Test in Staging First**: Verify all substitutions work before prod
3. **Use Latest Source**: Ensure pipelines build from `src/` directory
4. **Trailing Slash for MCP**: Always append `/mcp/` with trailing slash
5. **Dynamic Agent IDs**: Let deployment script write agent IDs, don't hard-code
6. **Environment-Specific**: Use different values for staging/prod via variables
