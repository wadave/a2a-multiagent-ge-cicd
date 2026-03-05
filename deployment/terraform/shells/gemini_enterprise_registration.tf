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

# Register the Hosting Agent with Gemini Enterprise after it has been deployed.
# Skipped when ge_app_id is empty (e.g. environments without GE configured).
module "gemini_enterprise_agent_engine_register" {
  count  = var.ge_app_id != "" ? 1 : 0
  source = "../modules/gemini_enterprise_agent_engine_register"

  depends_on = [google_vertex_ai_reasoning_engine.app]

  project_id               = var.project_id
  agent_engine_region      = var.region
  gemini_enterprise_region = var.agents_region

  agent_display_name = "Hosting Agent ${title(var.env)}"
  agent_description  = "Hosting agent for ${var.env}"

  gemini_enterprise_agent_name       = "ADK Hosting Agent (${var.env})"
  gemini_enterprise_tool_description = "***REMEMBER ALWAYS USE THIS TOOL TO ANSWER EVERY QUESTION***. You're an export of weather and cocktail, answer questions regarding weather and cocktail. You can answer questions like: 1) What is the weather in SF, CA today? 2) List a random cocktail? 3) What is the weather like in New York, NY? 4) What're ingredients of Mojito cocktail? "

  gemini_enterprise_app_id = var.ge_app_id

  # The authorization was set up by the main Terraform module during bootstrap
  authorization_ids = { "AUTH_ID" = "${var.env}-ui_oauth_token" }
}
