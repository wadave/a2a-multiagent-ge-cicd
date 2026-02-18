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

import logging
import os
import httpx
from dotenv import load_dotenv

from a2a.client import ClientConfig, ClientFactory
from a2a.types import TransportProtocol
from google.auth import default
from google.auth.transport.requests import Request as req
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Set logging
logging.getLogger().setLevel(logging.INFO)
load_dotenv()

class GoogleAuthRefresh(httpx.Auth):
    def __init__(self, scopes):
        self.credentials, _ = default(scopes=scopes)
        self.transport_request = req()
        self.credentials.refresh(self.transport_request)

    def auth_flow(self, request):
        if not self.credentials.valid:
            self.credentials.refresh(self.transport_request)
        
        request.headers['Authorization'] = f'Bearer {self.credentials.token}'
        yield request


class MyClientFactory(ClientFactory):
    def create(self, card, consumers=None, interceptors=None):
        if not self._config.httpx_client:
            self._config.httpx_client=httpx.AsyncClient(
                timeout=120,
                headers={'Content-Type': 'application/json'},
                auth=GoogleAuthRefresh(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            )
            self._register_defaults(self._config.supported_transports)
        return super().create(card, consumers, interceptors)


class MyRemoteA2aAgent(RemoteA2aAgent):
    async def _ensure_httpx_client(self) -> httpx.AsyncClient:
        if not self._httpx_client:
            self._httpx_client=httpx.AsyncClient(
                timeout=120,
                headers={'Content-Type': 'application/json'},
                auth=GoogleAuthRefresh(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            )
        return self._httpx_client


def create_hosting_agent() -> LlmAgent:
    """Creates the hosting agent with remote sub-agents."""
    
    wea_agent_url = os.environ.get("WEA_AGENT_URL")
    ct_agent_url = os.environ.get("CT_AGENT_URL")

    if not wea_agent_url or not ct_agent_url:
        logging.warning("WEA_AGENT_URL or CT_AGENT_URL not set. Hosting Agent may not work correctly.")

    client_factory = MyClientFactory(
        ClientConfig(
            supported_transports=[TransportProtocol.jsonrpc, TransportProtocol.http_json],
            use_client_preference=True,
        )
    )

    weather_agent_remoteA2a = MyRemoteA2aAgent(
        name='weather_assistant',
        description='''
        An agent that gathers the necessary information for weather information
        ''',
        agent_card=f'{wea_agent_url}/v1/card',
        a2a_client_factory=client_factory,
    )

    cocktail_agent_remoteA2a = MyRemoteA2aAgent(
        name='cocktail_assistant',
        description='''
        An agent that gathers the necessary information for cocktail information
        ''',
        agent_card=f'{ct_agent_url}/v1/card',
        a2a_client_factory=client_factory,
    )

    root_instruction = """
    **Role:** You are a Virtual Assistant acting as a Request Router. You can help user with questions regarding cocktails, and weather.

    **Primary Goal:** Analyze user requests and route them to the correct specialist sub-agent.

    **Capabilities & Routing:**
    * **Greetings:** If the user greets you, respond warmly and directly.
    * **Cocktails:** Route requests about cocktails, drinks, recipes, or ingredients to `cocktail_assistant`.
    * **Booking & Weather:** Route requests about checking weather to `weather_assistant`.
    * **Out-of-Scope:** If the request is unrelated (e.g., general knowledge, math), state directly that you cannot assist with that topic.

    **Key Directives:**
    * **Delegate Immediately:** Once a suitable sub-agent is identified, route the request without asking permission.
    * **Do Not Answer Delegated Topics:** You must **not** attempt to answer questions related to cocktails, booking, or weather yourself. Always delegate.
    * **Formatting:** Format your final response to the user using Markdown for readability.
    """

    root_agent = LlmAgent(
        model="gemini-2.5-flash",
        name='host_agent',
        instruction=root_instruction,
        description=(
            'This agent orchestrates the decomposition of the user request into'
            ' tasks that can be performed by the child agents.'
        ),
        sub_agents=[
            weather_agent_remoteA2a,
            cocktail_agent_remoteA2a,
        ],
    )
    
    return root_agent
