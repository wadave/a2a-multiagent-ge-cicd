import urllib.parse
from google.auth import default
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token

raw_url = "https://cocktail-mcp-ge-staging-lxo6yz2aha-uc.a.run.app/mcp/"
parsed_url = urllib.parse.urlparse(raw_url)
audience = f"{parsed_url.scheme}://{parsed_url.netloc}"

try:
    credentials, project = default()
    auth_req = google_auth_requests.Request()
    if credentials.token is None:
        credentials.refresh(auth_req)
        
    print(f"Token type: {type(credentials)}")
    print(f"Has ID token? {hasattr(credentials, 'id_token')}")
    
except Exception as e:
    print(f"Failed to fetch token: {e}")
