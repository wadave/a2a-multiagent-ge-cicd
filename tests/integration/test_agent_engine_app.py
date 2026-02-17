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

import logging
import os

import pytest
from google.adk.events.event import Event
from vertexai import agent_engines

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


@pytest.fixture
def agent_app():
    """Fixture to create and set up an AdkApp wrapping the hosting agent."""
    root_agent = create_hosting_agent()
    app = agent_engines.AdkApp(agent=root_agent)
    app.set_up()
    return app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_stream_query(agent_app) -> None:
    """
    Integration test for the agent stream query functionality.
    Tests that the agent returns valid streaming responses.
    """
    message = "Hi!"
    events = []
    async for event in agent_app.async_stream_query(message=message, user_id="test"):
        events.append(event)
    assert len(events) > 0, "Expected at least one chunk in response"

    has_text_content = False
    for event in events:
        validated_event = Event.model_validate(event)
        content = validated_event.content
        if (
            content is not None
            and content.parts
            and any(part.text for part in content.parts)
        ):
            has_text_content = True
            break

    assert has_text_content, "Expected at least one event with text content"


@pytest.mark.integration
def test_agent_feedback(agent_app) -> None:
    """
    Integration test for the agent feedback functionality.
    Tests that feedback can be registered successfully.
    """
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "user_id": "test-user-456",
        "session_id": "test-session-456",
    }

    # Should not raise any exceptions
    agent_app.register_feedback(feedback_data)

    # Test invalid feedback
    with pytest.raises(ValueError):
        invalid_feedback = {
            "score": "invalid",  # Score must be numeric
            "text": "Bad feedback",
            "user_id": "test-user-789",
            "session_id": "test-session-789",
        }
        agent_app.register_feedback(invalid_feedback)

    logging.info("All assertions passed for agent feedback test")
