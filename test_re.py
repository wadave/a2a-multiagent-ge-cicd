import vertexai
from vertexai import agent_engines

vertexai.init(project="dw-genai-dev", location="us-central1")
RESOURCE_NAME = "projects/496235138247/locations/us-central1/reasoningEngines/6246548758255894528"
try:
    print(f"Connecting to: {RESOURCE_NAME}")
    re = agent_engines.get(RESOURCE_NAME)
    print("Success:", re.display_name)
except Exception as e:
    print("Error:", e)
