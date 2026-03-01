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

# Data source to get project numbers
data "google_project" "projects" {
  for_each   = local.deploy_project_ids
  project_id = each.value
}

# 1. Assign roles for the CICD project
resource "google_project_iam_member" "cicd_project_roles" {
  for_each = toset(var.cicd_roles)

  project    = var.cicd_runner_project_id
  role       = each.value
  member     = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]

}

# 2. Assign roles for the other two projects (unique deployment projects)
resource "google_project_iam_member" "other_projects_roles" {
  for_each = {
    for pair in setproduct(toset(values(local.deploy_project_ids)), var.cicd_sa_deployment_required_roles) :
    "${pair[0]}-${pair[1]}" => {
      project_id = pair[0]
      role       = pair[1]
    }
  }

  project    = each.value.project_id
  role       = each.value.role
  member     = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}
# 3. Grant application SA the required permissions to run the application
resource "google_project_iam_member" "app_sa_roles" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), var.app_sa_roles) :
    join(",", pair) => {
      project = local.deploy_project_ids[pair[0]]
      role    = pair[1]
    }
  }

  project    = each.value.project
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.app_sa[split(",", each.key)[0]].email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}




# Special assignment: Allow the CICD SA to create tokens
resource "google_service_account_iam_member" "cicd_run_invoker_token_creator" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}
# Special assignment: Allow the CICD SA to impersonate himself for trigger creation
resource "google_service_account_iam_member" "cicd_run_invoker_account_user" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Allow the Cloud Build Service Agent to impersonate the CICD SA for V2 trigger execution
resource "google_service_account_iam_member" "cloudbuild_p4sa_impersonate_cicd" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.cicd_project.number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
  depends_on         = [resource.google_project_service.cicd_services]
}

# Allow the Legacy Cloud Build Service Account to impersonate the CICD SA for V1 trigger execution
resource "google_service_account_iam_member" "cloudbuild_legacy_impersonate_cicd" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.cicd_project.number}@cloudbuild.gserviceaccount.com"
  depends_on         = [resource.google_project_service.cicd_services]
}

# Allow CICD SA to impersonate app service accounts for deployment
resource "google_service_account_iam_member" "cicd_impersonate_app_sa" {
  for_each = local.deploy_project_ids

  service_account_id = google_service_account.app_sa[each.key].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Grant the CI/CD service account Model Armor Admin to manage floor settings
resource "google_project_iam_member" "github_runner_modelarmor_admin" {
  for_each = toset(values(local.deploy_project_ids))

  project = each.value
  role    = "roles/modelarmor.admin"
  member  = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
}

# Grant the CI/CD service account Service Usage Consumer
# Required for quota project determination via WIF when enabling floor settings
resource "google_project_iam_member" "github_runner_serviceusage_consumer" {
  for_each = toset(values(local.deploy_project_ids))

  project = each.value
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
}
