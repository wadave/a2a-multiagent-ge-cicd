# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Author: Dave Wang
import asyncio
import logging
import os
from typing import AsyncIterator, List

import gradio as gr
import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Initialize Vertex AI session
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Connect to the deployed ADK hosting agent
RESOURCE_NAME = (
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
)
logger.info(f"Connecting to agent: {RESOURCE_NAME}")
remote_agent = agent_engines.get(RESOURCE_NAME)
logger.info(f"Connected to agent: {remote_agent.display_name}")


async def get_response_from_agent(
    query: str,
    history: List[gr.ChatMessage],
) -> AsyncIterator[gr.ChatMessage]:
    """Get response from host agent using the ADK agent_engines API."""

    try:
        logger.info(f"Sending query to agent: {query}")

        # Create a session for this conversation
        session = await remote_agent.async_create_session(user_id="frontend_user")
        session_id = session["id"] if isinstance(session, dict) else session.id

        # Stream the response from the agent
        final_text = None
        async for event in remote_agent.async_stream_query(
            user_id="frontend_user",
            session_id=session_id,
            message=query,
        ):
            # Extract text from events
            content = event.get("content", {})
            parts = content.get("parts", [])
            if parts:
                text = parts[0].get("text")
                function_call = parts[0].get("functionCall")
                # Only capture text responses, not function calls
                if text and not function_call:
                    final_text = text

        if final_text:
            logger.info(f"Response received: {final_text[:50]}...")
            yield gr.ChatMessage(role="assistant", content=final_text)
        else:
            logger.warning("No text response found in events")
            yield gr.ChatMessage(
                role="assistant",
                content="I processed your request but found no text response.",
            )

    except Exception as e:
        logger.error(
            f"Error in get_response_from_agent (Type: {type(e).__name__}): {e}",
            exc_info=True,
        )
        yield gr.ChatMessage(
            role="assistant",
            content=f"An error occurred: {e}",
        )


async def main() -> None:
    """Main gradio app that launches the Gradio interface."""

    with gr.Blocks(theme=gr.themes.Ocean(), title="A2A Host Agent") as demo:
        with gr.Row():
            gr.Image(
                "static/a2a.png",
                width=100,
                height=100,
                scale=0,
                show_label=False,
                show_download_button=False,
                container=False,
                show_fullscreen_button=False,
                elem_classes=["centered-image"],
            )

        gr.ChatInterface(
            get_response_from_agent,
            title="A2A Host Agent",
            description="This assistant can help you to check weather and find cocktail information",
        )

    logger.info("Launching Gradio interface on http://0.0.0.0:8080")
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=8080,
    )
    logger.info("Gradio application has been shut down")


if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
        logger.info("Created 'static' directory. Please add your 'a2a.png' image there.")

    asyncio.run(main())
