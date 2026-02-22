#!/usr/bin/env bash
# Copyright 2025 Google LLC
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

set -e

echo "================================================================================"
echo "Integration Test: Gemini Enterprise Terraform Registration"
echo "================================================================================"

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${DIR}/../.." && pwd )"
TERRAFORM_DIR="${PROJECT_ROOT}/deployment/terraform"

echo "Running Terraform from directory: ${TERRAFORM_DIR}"
echo ""

# Extract PROJECT_ID from test_config.py using python, to mimic the previous python test
cd "${PROJECT_ROOT}"
source .venv/bin/activate
export PROJECT_ID=$(python3 -c "import sys; sys.path.append('tests'); from test_config import PROJECT_ID; print(PROJECT_ID)")
echo "Extracted PROJECT_ID is: '$PROJECT_ID'"
cd "${TERRAFORM_DIR}"

export TF_VAR_prod_project_id="${PROJECT_ID}"
export TF_VAR_staging_project_id="${PROJECT_ID}"
export TF_VAR_cicd_runner_project_id="${PROJECT_ID}"
export TF_VAR_repository_owner="test-owner"
export TF_VAR_repository_name="test-repo"

echo "Executing: terraform init"
terraform init
echo "----------------------------------------"

echo "Executing: terraform apply -auto-approve -target=module.gemini_enterprise_oauth -target=module.gemini_enterprise_agent_engine_register"
if terraform apply -auto-approve -target=module.gemini_enterprise_oauth -target=module.gemini_enterprise_agent_engine_register; then
  echo ""
  echo "[PASS] Successfully executed Terraform registration."
  exit 0
else
  echo ""
  echo "[FAIL] Could not execute Terraform registration."
  exit 1
fi
