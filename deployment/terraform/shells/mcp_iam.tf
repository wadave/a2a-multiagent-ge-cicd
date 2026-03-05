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

# Grant the default Agent Engine service account permission to invoke MCP services
resource "google_cloud_run_v2_service_iam_member" "agent_engine_mcp_invoker" {
  for_each = local.mcp_service_bindings

  project  = var.project_id
  location = var.region
  name     = each.value.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.agent_engine_sa}"

  depends_on = [google_cloud_run_v2_service.mcp_server]
}

# Grant the App service account permission to invoke MCP services
# (needed when agents are deployed with a custom service account)
resource "google_cloud_run_v2_service_iam_member" "app_sa_mcp_invoker" {
  for_each = local.mcp_service_bindings

  project  = var.project_id
  location = var.region
  name     = each.value.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${data.google_service_account.app_sa.email}"

  depends_on = [google_cloud_run_v2_service.mcp_server]
}
