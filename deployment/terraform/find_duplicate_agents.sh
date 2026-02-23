#!/bin/bash
TOKEN_NAME="projects/496235138247/locations/global/authorizations/staging-ui_oauth_token"
URL="https://discoveryengine.googleapis.com/v1alpha/projects/496235138247/locations/global/collections/default_collection/engines/enterprise-search-17489269_1748926990192/assistants/default_assistant/agents"
NEXT_PAGE_TOKEN=""

while :; do
  PAGED_URL="${URL}"
  if [ -n "$NEXT_PAGE_TOKEN" ]; then
    PAGED_URL="${URL}?pageToken=${NEXT_PAGE_TOKEN}"
  fi
  
  RESPONSE=$(curl -s -X GET \
      -H "Authorization: Bearer $(gcloud auth print-access-token)" \
      -H "x-goog-user-project: $(gcloud config get-value project)" \
      -H "content-type: application/json" \
      "${PAGED_URL}")
  
  # Search the current page for the token
  hit=$(echo "$RESPONSE" | grep "staging-ui_oauth_token")
  if [ -n "$hit" ]; then
     echo "===== FOUND MATCH ====="
     echo "$RESPONSE" | jq ".agents[] | select(.authorizationConfig.toolAuthorizations[]? | contains(\"staging-ui_oauth_token\")) | .name" 2>/dev/null
     echo "$RESPONSE" | jq ".agents[] | select(.authorizationConfig.agentAuthorization | contains(\"staging-ui_oauth_token\")) | .name" 2>/dev/null
     echo "$RESPONSE" | jq ".agents[] | select(.adkAgentDefinition.authorizations[]? | contains(\"staging-ui_oauth_token\")) | .name" 2>/dev/null
  fi
  
  NEXT_PAGE_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('nextPageToken', ''))" 2>/dev/null)
  
  if [ -z "$NEXT_PAGE_TOKEN" ]; then
    break
  fi
done
echo "Search Complete"
