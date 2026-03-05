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

# Hybrid Provisioning: Terraform creates Agent Engine shells with a dummy
# inline source archive. CI/CD then deploys the real source code via
# deploy_agents.py (using the SDK update path), which Terraform ignores
# via the lifecycle block below.
resource "google_vertex_ai_reasoning_engine" "app" {
  for_each = local.agent_deployments

  display_name = each.value.display_name
  description  = "Agent deployed via Terraform"
  region       = var.region
  project      = var.project_id

  spec {
    agent_framework = "google-adk"
    service_account = data.google_service_account.app_sa.email

    deployment_spec {
      min_instances         = 1
      max_instances         = 10
      container_concurrency = 9

      resource_limits = {
        cpu    = "4"
        memory = "8Gi"
      }

      env {
        name  = "LOGS_BUCKET_NAME"
        value = local.logs_bucket_name
      }
    }

    source_code_spec {
      inline_source {
        # Dummy base64-encoded tarball for initial shell creation.
        # CI/CD overwrites this with real source code.
        source_archive = trimspace(file("${path.module}/dummy_source/source-b64.txt"))
      }

      python_spec {
        # The true entrypoints are set by CI/CD via deploy_agents.py.
        # This dummy entrypoint prevents Vertex AI from crashing on startup
        # while reading the placeholder source_archive.
        entrypoint_module = "main"
        entrypoint_object = "dummy"
        version           = "3.12"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      spec[0].source_code_spec,
      spec[0].deployment_spec,
      display_name,
    ]
  }
}
