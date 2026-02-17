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
from a2a_agents.common.adk_orchestrator_agent_executor import AdkOrchestratorAgentExecutor
from a2a_agents.hosting_agent.adk_agent import create_hosting_agent
from google.adk import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
import logging
import os
from dotenv import load_dotenv

# Set logging
logging.getLogger().setLevel(logging.INFO)
load_dotenv()


class HostingAgentExecutor(AdkOrchestratorAgentExecutor):
    """Agent Executor that uses create_hosting_agent for the ADK agent.
    
    This executor bridges the A2A protocol with the hosting agent defined
    in adk_agent.py (which uses LlmAgent with sub-agents).
    """

    def __init__(self) -> None:
        """Initialize."""
        # We don't need remote_agent_addresses for super because we override _init_agent
        super().__init__(remote_agent_addresses=[])

    async def _init_agent(self) -> None:
        """
        Lazy initialization of agent resources using create_hosting_agent.
        """
        if self.agent is None:
            # Create the actual agent using the factory
            # This factory reads CT_AGENT_URL and WEA_AGENT_URL from env
            self.agent = create_hosting_agent()

            # The Runner orchestrates the agent execution
            self.runner = Runner(
                app_name=self.agent.name,
                agent=self.agent,
                # In-memory services for simplicity
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService(),
            )
