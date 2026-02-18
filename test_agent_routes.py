import asyncio
from a2a.client import ClientFactory, ClientConfig
from a2a.types import TransportProtocol
import httpx
from google.auth import default
from google.auth.transport.requests import Request as req

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

async def main():
    agent_url = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/7385853910864363520/a2a"
    client = httpx.AsyncClient(
        auth=GoogleAuthRefresh(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    )
    
    # Let's try to get the card directly
    url = f"{agent_url}/v1/card"
    print(f"Fetching card from {url}")
    resp = await client.get(url)
    print(resp.status_code)
    print(resp.text)

asyncio.run(main())
