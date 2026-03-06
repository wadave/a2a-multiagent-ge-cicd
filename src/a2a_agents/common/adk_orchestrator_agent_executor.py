# Copyright 2026 Google LLC
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
import logging
from typing import NoReturn

import httpx

# A2A
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Role,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from aiobreaker import CircuitBreaker, CircuitBreakerError
from dotenv import load_dotenv
from google.adk import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.genai import types

from a2a_agents.common.adk_orchestrator_agent import get_orchestrator_agent
from a2a_agents.common.auth_utils import GoogleAuth

# Set logging
logging.getLogger().setLevel(logging.INFO)
load_dotenv()


# Global shared HTTP client for the orchestrator
_shared_httpx_client: httpx.AsyncClient | None = None

# Create a circuit breaker that:
# 1. Trips open after 3 consecutive failures
# 2. Stays open for 30 seconds before attempting a test request (half-open)
llm_api_breaker = CircuitBreaker(fail_max=3, timeout_duration=30)


class CircuitBreakerTransport(httpx.AsyncBaseTransport):
    """Wraps an httpx transport to enforce an aiobreaker circuit breaker."""

    def __init__(self, underlying: httpx.AsyncBaseTransport):
        self._underlying = underlying

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:

            @llm_api_breaker
            async def _make_request():
                response = await self._underlying.handle_async_request(request)
                # We want 5xx server errors and network timeouts to count as failures
                if getattr(response, "status_code", 200) >= 500:
                    response.raise_for_status()
                return response

            return await _make_request()
        except CircuitBreakerError:
            logging.warning(f"Circuit Breaker OPEN. Fast-failing request to {request.url}")
            return httpx.Response(status_code=503, content=b"Circuit Breaker Open", request=request)
        except httpx.HTTPStatusError as e:
            # We must return the actual response object to satisfy httpx.AsyncClient
            return e.response


def get_shared_httpx_client() -> httpx.AsyncClient:
    """Gets or creates a shared httpx.AsyncClient with GoogleAuth and Circuit Breaker."""
    global _shared_httpx_client
    if _shared_httpx_client is None:
        base_transport = httpx.AsyncHTTPTransport(retries=0)
        cb_transport = CircuitBreakerTransport(base_transport)

        _shared_httpx_client = httpx.AsyncClient(
            transport=cb_transport,
            timeout=60.0,
            auth=GoogleAuth(),
        )
        _shared_httpx_client.headers["Content-Type"] = "application/json"
    return _shared_httpx_client


class AdkOrchestratorAgentExecutor(AgentExecutor):
    """Agent Executor that bridges A2A protocol with our ADK agent.

    The executor handles:
    1. Protocol translation (A2A messages to/from agent format)
    2. Task lifecycle management (submitted -> working -> completed)
    3. Session management for multi-turn conversations
    4. Error handling and recovery
    """

    def __init__(self, remote_agent_addresses: list[str]) -> None:
        """Initialize with lazy loading pattern.

        Args:
            remote_agent_addresses: A list of remote agent addresses.
        """
        self.remote_agent_addresses = remote_agent_addresses
        self.agent = None
        self.runner = None
        # Act as an LRU cache bounded to 10000 items to prevent memory leaks.
        self._context_to_session_id: dict[str, str] = {}

    async def _init_agent(self) -> None:
        """
        Lazy initialization of agent resources.
        This now constructs the agent and its serializable auth.
        """
        if self.agent is None:
            # --- Environment setup ---
            # Use the shared HTTP client for efficiency and connection pooling
            httpx_client = get_shared_httpx_client()

            # Create the actual agent
            self.agent = await get_orchestrator_agent(
                remote_agent_addresses=self.remote_agent_addresses, httpx_client=httpx_client
            )

            # The Runner orchestrates the agent execution
            # It manages the LLM calls, tool execution, and state
            import os

            from google.adk.sessions.in_memory_session_service import InMemorySessionService

            engine_id = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID")
            session_service = (
                VertexAiSessionService(agent_engine_id=engine_id)
                if engine_id
                else InMemorySessionService()
            )

            self.runner = Runner(
                app_name=self.agent.name,
                agent=self.agent,
                # In-memory services for simplicity
                # In production, you might use persistent storage
                artifact_service=InMemoryArtifactService(),
                session_service=session_service,
                memory_service=InMemoryMemoryService(),
            )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Process a user query and return the answer.

        This method is called by the A2A protocol handler when:
        1. A new message arrives (message/send)
        2. A streaming request is made (message/stream)
        """
        # Initialize agent on first call
        if self.agent is None:
            await self._init_agent()

        # Extract the user's question from the protocol message
        query = context.get_user_input()
        logging.info(f"Received query: {query}")

        # Create a TaskUpdater for managing task state
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        # Update task status through its lifecycle
        # submitted -> working -> completed/failed
        if not context.current_task:
            # New task - mark as submitted
            await updater.submit()

        # Mark task as working (processing)
        await updater.start_work()

        try:
            # Get or create a session for this conversation
            session = await self._get_or_create_session(context.context_id)
            logging.info(f"Using session: {session.id}")

            # Prepare the user message in ADK format
            content = types.Content(role=Role.user, parts=[types.Part(text=query)])

            # Run the agent asynchronously
            # This may involve multiple LLM calls and tool uses
            async for event in self.runner.run_async(
                session_id=session.id,
                user_id="user",  # In production, use actual user ID
                new_message=content,
            ):
                # The agent may produce multiple events
                # We're interested in the final response
                if event.is_final_response():
                    # Extract the answer text from the response
                    answer = self._extract_answer(event)
                    logging.info(f" {answer}")

                    # Add the answer as an artifact
                    # Artifacts are the "outputs" or "results" of a task
                    # They're separate from status messages
                    await updater.add_artifact(
                        [TextPart(text=answer)],
                        name="answer",  # Name helps clients identify artifacts
                    )

                    # Mark task as completed successfully
                    await updater.complete()
                    break

        except Exception as e:
            # Errors should never pass silently (Zen of Python)
            # Always inform the client when something goes wrong
            logging.error(f"Error during execution: {e!s}", exc_info=True)
            await updater.failed(
                message=updater.new_agent_message([TextPart(text=f"Error: {e!s}")])
            )
            # Re-raise for proper error handling up the stack
            raise

    async def _get_or_create_session(self, context_id: str):
        """Get existing session or create new one."""
        vertex_session_id = self._context_to_session_id.get(context_id)

        if vertex_session_id:
            try:
                session = await self.runner.session_service.get_session(
                    app_name=self.runner.app_name,
                    user_id="user",
                    session_id=vertex_session_id,
                )
                if session:
                    logging.info(
                        f"Resuming existing session for context {context_id} -> Vertex session {vertex_session_id}."
                    )
                    # Bump to end for LRU cache effect
                    if context_id in self._context_to_session_id:
                        val = self._context_to_session_id.pop(context_id)
                        self._context_to_session_id[context_id] = val
                    return session
            except Exception as e:
                logging.warning(
                    f"Vertex session {vertex_session_id} not found or error occurred: {e}. Creating new one."
                )

        logging.info(f"No active session found for context {context_id}, creating new one.")
        session = await self.runner.session_service.create_session(
            app_name=self.runner.app_name,
            user_id="user",
        )
        self._context_to_session_id[context_id] = session.id

        # Prevent unbounded memory growth (max 10000 sessions)
        if len(self._context_to_session_id) > 10000:
            oldest_key = next(iter(self._context_to_session_id))
            if oldest_key != context_id:
                del self._context_to_session_id[oldest_key]

        return session

    def _extract_answer(self, event) -> str:
        """Extract text answer from agent response."""
        parts = event.content.parts
        text_parts = [part.text for part in parts if part.text]

        # Join all text parts with space
        return " ".join(text_parts) if text_parts else "No answer found."

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> NoReturn:
        """Handle task cancellation requests.

        For long-running agents, this would:
        1. Stop any ongoing processing
        2. Clean up resources
        3. Update task state to 'cancelled'
        """
        logging.warning(f"Cancellation requested for task {context.task_id}, but not supported.")
        # Inform client that cancellation isn't supported
        raise ServerError(error=UnsupportedOperationError())
