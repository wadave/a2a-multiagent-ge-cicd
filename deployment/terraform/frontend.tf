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

# Frontend Cloud Run Service

variable "frontend_image_staging" {
  type        = string
  description = "Docker image for staging frontend (e.g., us-central1-docker.pkg.dev/PROJECT/REPO/frontend:TAG)"
  default     = ""
}

variable "frontend_image_prod" {
  type        = string
  description = "Docker image for production frontend"
  default     = ""
}

variable "hosting_agent_id_staging" {
  type        = string
  description = "Hosting Agent ID for staging"
  default     = ""
}

variable "hosting_agent_id_prod" {
  type        = string
  description = "Hosting Agent ID for production"
  default     = ""
}

# Deploy frontend to staging
resource "google_cloud_run_v2_service" "frontend_staging" {
  count    = var.frontend_image_staging != "" ? 1 : 0
  project  = var.staging_project_id
  location = var.region
  name     = "a2a-frontend-ge2"

  template {
    service_account = google_service_account.app_sa["staging"].email

    containers {
      image = var.frontend_image_staging

      env {
        name  = "PROJECT_ID"
        value = var.staging_project_id
      }

      env {
        name  = "PROJECT_NUMBER"
        value = var.staging_project_number
      }

      env {
        name  = "AGENT_ENGINE_ID"
        value = var.hosting_agent_id_staging
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.deploy_project_services,
    google_service_account.app_sa
  ]
}

# Allow unauthenticated access to frontend (staging)
resource "google_cloud_run_v2_service_iam_member" "frontend_staging_noauth" {
  count    = var.frontend_image_staging != "" ? 1 : 0
  project  = var.staging_project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend_staging[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Deploy frontend to production
resource "google_cloud_run_v2_service" "frontend_prod" {
  count    = var.frontend_image_prod != "" ? 1 : 0
  project  = var.prod_project_id
  location = var.region
  name     = "a2a-frontend-ge2-prod"

  template {
    service_account = google_service_account.app_sa["prod"].email

    containers {
      image = var.frontend_image_prod

      env {
        name  = "PROJECT_ID"
        value = var.prod_project_id
      }

      env {
        name  = "PROJECT_NUMBER"
        value = var.prod_project_number
      }

      env {
        name  = "AGENT_ENGINE_ID"
        value = var.hosting_agent_id_prod
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.deploy_project_services,
    google_service_account.app_sa
  ]
}

# Allow unauthenticated access to frontend (prod)
resource "google_cloud_run_v2_service_iam_member" "frontend_prod_noauth" {
  count    = var.frontend_image_prod != "" ? 1 : 0
  project  = var.prod_project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend_prod[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "frontend_url_staging" {
  description = "URL of the staging frontend"
  value       = var.frontend_image_staging != "" ? google_cloud_run_v2_service.frontend_staging[0].uri : "Not deployed"
}

output "frontend_url_prod" {
  description = "URL of the production frontend"
  value       = var.frontend_image_prod != "" ? google_cloud_run_v2_service.frontend_prod[0].uri : "Not deployed"
}
