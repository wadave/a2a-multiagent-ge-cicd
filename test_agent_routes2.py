import asyncio
import uuid
import httpx
from google.auth import default
from google.auth.transport.requests import Request as req
from google.oauth2 import id_token as google_id_token

class GoogleAuthRefresh(httpx.Auth):
    def __init__(self, audience):
        self.audience = audience
        self.transport_request = req()
        self.token = google_id_token.fetch_id_token(self.transport_request, self.audience)

    def auth_flow(self, request):
        try:
            self.token = google_id_token.fetch_id_token(self.transport_request, self.audience)
        except Exception as e:
            print(f"Failed to refresh ID token: {e}")
        request.headers['Authorization'] = f'Bearer {self.token}'
        yield request

async def main():
    agent_url = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/496235138247/locations/us-central1/reasoningEngines/7385853910864363520/a2a"
    
    auth = GoogleAuthRefresh(audience=agent_url)
    headers = {
        "Content-Type": "application/json",
    }
    client = httpx.AsyncClient(auth=auth, headers=headers)
    
    payload = {
        "text": "List a random cocktail",
        "sessionId": str(uuid.uuid4())
    }
    
    url = f"{agent_url}/v1/message:send"
    print(f"Sending message to {url} with {payload}")
    resp = await client.post(url, json=payload)
    print(resp.status_code)
    print(resp.text)

asyncio.run(main())
