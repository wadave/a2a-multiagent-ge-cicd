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

"""Basic load test for the Hosting Agent streaming endpoint."""

import json
import logging
import os
import sys
import time
from pathlib import Path

from locust import HttpUser, between, task

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from test_config import HOSTING_AGENT_ID, LOCATION, PROJECT_NUMBER

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load agent config from environment variables (with test_config fallback)
project_number = os.environ.get("PROJECT_NUMBER") or PROJECT_NUMBER
location = os.environ.get("GOOGLE_CLOUD_REGION") or LOCATION
engine_id = os.environ.get("AGENT_ENGINE_ID") or HOSTING_AGENT_ID

if not project_number or not engine_id:
    # Fallback: try loading from deployment_metadata.json
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, encoding="utf-8") as f:
            remote_agent_engine_id = json.load(f)["remote_agent_engine_id"]
        parts = remote_agent_engine_id.split("/")
        project_number = parts[1]
        location = parts[3]
        engine_id = parts[5]
    else:
        raise RuntimeError(
            "Configuration not found. Set PROJECT_NUMBER and AGENT_ENGINE_ID (or HOSTING_AGENT_ID) "
            "env vars, or provide deployment_metadata.json."
        )

# Convert to streaming URL
base_url = f"https://{location}-aiplatform.googleapis.com"
url_path = f"/v1/projects/{project_number}/locations/{location}/reasoningEngines/{engine_id}:streamQuery"

logger.info("Load Test Configuration:")
logger.info(f"  Project Number: {project_number}")
logger.info(f"  Location: {location}")
logger.info(f"  Agent Engine ID: {engine_id}")
logger.info(f"  Base URL: {base_url}")
logger.info(f"  URL path: {url_path}")


class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = base_url  # Set the base host URL for Locust

    @task
    def chat_stream(self) -> None:
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {os.environ['_AUTH_TOKEN']}"

        data = {
            "class_method": "async_stream_query",
            "input": {
                "user_id": "test",
                "message": "Hi!",
            },
        }

        start_time = time.time()
        with self.client.post(
            url_path,
            headers=headers,
            json=data,
            catch_response=True,
            name="/streamQuery async_stream_query",
            stream=True,
            params={"alt": "sse"},
        ) as response:
            if response.status_code == 200:
                events = []
                has_error = False
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        events.append(line_str)

                        if "429 Too Many Requests" in line_str:
                            self.environment.events.request.fire(
                                request_type="POST",
                                name=f"{url_path} rate_limited 429s",
                                response_time=0,
                                response_length=len(line),
                                response=response,
                                context={},
                            )

                        # Check for error responses in the JSON payload
                        try:
                            event_data = json.loads(line_str)
                            if isinstance(event_data, dict) and "code" in event_data:
                                if event_data["code"] >= 400:
                                    has_error = True
                                    error_msg = event_data.get(
                                        "message", "Unknown error"
                                    )
                                    response.failure(f"Error in response: {error_msg}")
                                    logger.error(
                                        "Received error response: code=%s, message=%s",
                                        event_data["code"],
                                        error_msg,
                                    )
                        except json.JSONDecodeError:
                            pass

                end_time = time.time()
                total_time = end_time - start_time

                if not has_error:
                    self.environment.events.request.fire(
                        request_type="POST",
                        name="/streamQuery end",
                        response_time=total_time * 1000,
                        response_length=len(events),
                        response=response,
                        context={},
                    )
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
