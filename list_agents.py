import os
import vertexai
from google.cloud import aiplatform

project_id = os.environ.get("PROJECT_ID")
location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
vertexai.init(project=project_id, location=location)
client = vertexai.Client(project=project_id, location=location, http_options={"api_version": "v1beta1"})

for engine in client.agent_engines.list():
    print(f"Name: {engine.api_resource.display_name} -> ID: {engine.api_resource.name}")
