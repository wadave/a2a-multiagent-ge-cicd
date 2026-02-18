CT_MCP_SERVER_URL=$(gcloud run services describe cocktail-mcp-ge-staging --region us-central1 --project dw-genai-dev --format="value(status.url)")/mcp/
WEA_MCP_SERVER_URL=$(gcloud run services describe weather-mcp-ge-staging --region us-central1 --project dw-genai-dev --format="value(status.url)")/mcp/

export CT_MCP_SERVER_URL=$CT_MCP_SERVER_URL
export WEA_MCP_SERVER_URL=$WEA_MCP_SERVER_URL
export PROJECT_ID="dw-genai-dev"
export GOOGLE_CLOUD_REGION="us-central1"
export APP_SERVICE_ACCOUNT="app-sa-staging@dw-genai-dev.iam.gserviceaccount.com"
export DISPLAY_NAME_SUFFIX="Staging"
export BUCKET_NAME="dw-genai-dev-bucket"

uv export --project ./src/a2a_agents --no-hashes --no-sources --no-header --no-dev --no-emit-project --no-annotate > src/requirements.txt
uv run deployment/deploy_agents.py
