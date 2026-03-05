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

data "google_project" "project" {
  project_id = var.project_id
}

data "google_service_account" "app_sa" {
  account_id = "${var.project_name}-app"
  project    = var.project_id
}

locals {
  # MCP service types
  mcp_service_types = ["cocktail", "weather"]

  # One entry per MCP service: key is "<env>-<type>", value has service_name
  mcp_service_bindings = {
    for svc in local.mcp_service_types :
    "${var.env}-${svc}" => {
      service_name = "${svc}-mcp-ge-${var.env}"
    }
  }

  # Agent definitions
  agents = {
    cocktail = {
      display_name      = "Cocktail Agent ${title(var.env)}"
      entrypoint_module = "a2a_agents.cocktail_agent.cocktail_agent_executor"
      entrypoint_object = "CocktailAgentExecutor"
    }
    weather = {
      display_name      = "Weather Agent ${title(var.env)}"
      entrypoint_module = "a2a_agents.weather_agent.weather_agent_executor"
      entrypoint_object = "WeatherAgentExecutor"
    }
    hosting = {
      display_name      = "Hosting Agent ${title(var.env)}"
      entrypoint_module = "a2a_agents.hosting_agent.adk_agent"
      entrypoint_object = "agent"
    }
  }

  # Flat map keyed as "<env>-<agent>" for for_each
  agent_deployments = {
    for k, v in local.agents :
    "${var.env}-${k}" => v
  }

  # Default Agent Engine service account for this project
  agent_engine_sa = "service-${data.google_project.project.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

  # Logs bucket follows the naming convention set in storage.tf
  logs_bucket_name = "${var.project_id}-${var.project_name}-logs"
}
