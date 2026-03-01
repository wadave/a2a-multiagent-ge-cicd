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

locals {
  cicd_services = [
    "cloudbuild.googleapis.com",
    "discoveryengine.googleapis.com",
    "aiplatform.googleapis.com",
    "serviceusage.googleapis.com",
    "bigquery.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com",
  ]

  deploy_project_services = [
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "discoveryengine.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "bigquery.googleapis.com",
    "serviceusage.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com",
  ]

  deploy_project_ids = {
    for k, v in {
      staging = var.staging_project_id
      prod    = var.prod_project_id
    } : k => v if v != ""
  }

  all_project_ids = [
    var.cicd_runner_project_id,
    var.prod_project_id,
    var.staging_project_id
  ]

  # Agent definitions for the multi-agent architecture
  agents = {
    cocktail = {
      display_name_suffix = "Cocktail Agent"
      entrypoint_module   = "a2a_agents.cocktail_agent.cocktail_agent_executor"
      entrypoint_object   = "CocktailAgentExecutor"
    }
    weather = {
      display_name_suffix = "Weather Agent"
      entrypoint_module   = "a2a_agents.weather_agent.weather_agent_executor"
      entrypoint_object   = "WeatherAgentExecutor"
    }
    hosting = {
      display_name_suffix = "Hosting Agent"
      entrypoint_module   = "a2a_agents.hosting_agent.adk_agent"
      entrypoint_object   = "agent"
    }
  }

  # Flatten agents x environments into a single map for for_each
  agent_deployments = {
    for pair in flatten([
      for env_key, project_id in local.deploy_project_ids : [
        for agent_key, agent in local.agents : {
          key               = "${env_key}-${agent_key}"
          env_key           = env_key
          project_id        = project_id
          display_name      = "${agent.display_name_suffix} ${title(env_key)}"
          entrypoint_module = agent.entrypoint_module
          entrypoint_object = agent.entrypoint_object
        }
      ]
    ]) : pair.key => pair
  }

}

