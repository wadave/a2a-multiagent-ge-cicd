# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# IAM permissions for Agent Engines to invoke MCP Cloud Run services

locals {
  # Define MCP services that need IAM permissions
  mcp_services = {
    cocktail = "cocktail-mcp-ge-staging"
    weather  = "weather-mcp-ge-staging"
  }

  # Agent Engine service account (default Vertex AI service account)
  # Format: service-{PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com
  agent_engine_sa = {
    for env_key, project_id in local.deploy_project_ids :
    env_key => "service-${data.google_project.projects[env_key].number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
  }
}

# Grant Agent Engine SA permission to invoke MCP Cloud Run services
resource "google_cloud_run_v2_service_iam_member" "agent_engine_mcp_invoker" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), keys(local.mcp_services)) :
    "${pair[0]}-${pair[1]}" => {
      env_key      = pair[0]
      service_name = local.mcp_services[pair[1]]
      project_id   = local.deploy_project_ids[pair[0]]
    }
  }

  project  = each.value.project_id
  location = var.region
  name     = each.value.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.agent_engine_sa[each.value.env_key]}"

  depends_on = [google_project_service.deploy_project_services]
}

# Also grant App Service Account permission to invoke MCP services
# (needed if agents use custom service accounts)
resource "google_cloud_run_v2_service_iam_member" "app_sa_mcp_invoker" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), keys(local.mcp_services)) :
    "${pair[0]}-${pair[1]}" => {
      env_key      = pair[0]
      service_name = local.mcp_services[pair[1]]
      project_id   = local.deploy_project_ids[pair[0]]
    }
  }

  project  = each.value.project_id
  location = var.region
  name     = each.value.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app_sa[each.value.env_key].email}"

  depends_on = [
    google_project_service.deploy_project_services,
    google_service_account.app_sa
  ]
}
