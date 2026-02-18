import os
import asyncio
from vertexai import agent_engines

async def main():
    RESOURCE_NAME = "projects/496235138247/locations/us-central1/reasoningEngines/6246548758255894528"
    print(f"Connecting to {RESOURCE_NAME}...")
    remote_agent = agent_engines.get(RESOURCE_NAME)
    print(dir(remote_agent))
    
    session = await remote_agent.async_create_session(user_id="test_user")
    session_id = session["id"] if isinstance(session, dict) else session.id
    print(f"Session: {session_id}")
    
    final_text = ""
    async for event in remote_agent.async_stream_query(
        user_id="test_user",
        session_id=session_id,
        message="list a random cocktail"
    ):
        content = event.get("content", {}) if isinstance(event, dict) else getattr(event, "content", {})
        if content:
            parts = content.get("parts", []) if isinstance(content, dict) else getattr(content, "parts", [])
            for part in parts:
                if isinstance(part, dict):
                    text = part.get("text")
                    has_fn = part.get("functionCall") or part.get("function_call")
                else:
                    text = getattr(part, "text", None)
                    has_fn = getattr(part, "function_call", None) or getattr(part, "functionCall", None)
                if text and not has_fn:
                    final_text += text
    
    print("\nResponse:")
    print(final_text)

asyncio.run(main())
