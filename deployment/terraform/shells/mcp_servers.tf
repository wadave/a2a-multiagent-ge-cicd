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

# Hybrid Provisioning: Terraform creates the Cloud Run shell with a placeholder
# image. CI/CD then deploys the real image via `gcloud run deploy`, which
# updates the service in-place without Terraform interfering.
resource "google_cloud_run_v2_service" "mcp_server" {
  for_each = local.mcp_service_bindings

  name                = each.value.service_name
  location            = var.region
  project             = var.project_id
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
    }
    service_account = data.google_service_account.app_sa.email
  }

  lifecycle {
    ignore_changes = [
      template.containers
    ]
  }
}
