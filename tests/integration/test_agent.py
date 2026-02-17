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

import os

import pytest
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from a2a_agents.hosting_agent.adk_agent import create_hosting_agent


@pytest.fixture(autouse=True)
def _set_agent_env_vars():
    """Set required environment variables for the hosting agent."""
    os.environ.setdefault(
        "CT_AGENT_URL",
        "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/8358349955399680000/a2a",
    )
    os.environ.setdefault(
        "WEA_AGENT_URL",
        "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/5302657608228798464/a2a",
    )


@pytest.mark.integration
def test_agent_stream() -> None:
    """
    Integration test for the agent stream functionality.
    Tests that the agent returns valid streaming responses.
    """
    root_agent = create_hosting_agent()

    session_service = InMemorySessionService()

    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Hello! How are you?")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0, "Expected at least one message"

    has_text_content = False
    for event in events:
        if (
            event.content
            and event.content.parts
            and any(part.text for part in event.content.parts)
        ):
            has_text_content = True
            break
    assert has_text_content, "Expected at least one message with text content"
