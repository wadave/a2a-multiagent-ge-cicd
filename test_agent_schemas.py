import os
from vertexai import agent_engines

RESOURCE_NAME = "projects/496235138247/locations/us-central1/reasoningEngines/6246548758255894528"
print(f"Connecting to {RESOURCE_NAME}...")

remote_agent = agent_engines.get(RESOURCE_NAME)
print("Agent display name:", remote_agent.display_name)
print("Available operations:")
try:
    print(remote_agent.operation_schemas())
except Exception as e:
    print("Error getting schemas:", e)
