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

variable "project_id" {
  description = "The GCP project ID to deploy shells into."
  type        = string
}

variable "env" {
  description = "Deployment environment label, e.g. 'staging' or 'prod'. Used in resource names and display names."
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.env)
    error_message = "env must be 'staging' or 'prod'."
  }
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
}

variable "project_name" {
  description = "Short project name used in resource naming conventions."
  type        = string
  default     = "a2a-multiagent-ge-cicd"
}

variable "ge_app_id" {
  description = "Gemini Enterprise app ID. If empty, agent registration is skipped."
  type        = string
  default     = ""
}

variable "agents_region" {
  description = "Region for Gemini Enterprise (typically 'global')."
  type        = string
  default     = "global"
}
