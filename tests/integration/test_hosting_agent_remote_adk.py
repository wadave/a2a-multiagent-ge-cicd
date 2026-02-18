"""Test remote hosting agent using agent_engines API (reference notebook pattern)."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

import vertexai
from vertexai import agent_engines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = "dw-genai-dev"
LOCATION = "us-central1"
RESOURCE_NAME = "projects/496235138247/locations/us-central1/reasoningEngines/6246548758255894528"


async def main():
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    print(f"Connecting to: {RESOURCE_NAME}")
    remote_agent = agent_engines.get(RESOURCE_NAME)
    print(f"✓ Connected: {remote_agent.display_name}")

    # Create session
    session = await remote_agent.async_create_session(user_id="test_user")
    print(f"✓ Session created: {session}")
    session_id = session["id"] if isinstance(session, dict) else session.id

    queries = [
        ("Hello! How are you?", "greeting"),
        ("What is the weather in Houston, TX?", "weather"),
        ("Tell me about a Margarita cocktail", "cocktail"),
        ("What is the capital of France?", "out_of_scope"),
    ]

    results = []
    for query, category in queries:
        print(f"\n{'='*60}")
        print(f"[{category}] Query: {query}")
        print("="*60)

        try:
            events = []
            async for event in remote_agent.async_stream_query(
                user_id="test_user",
                session_id=session_id,
                message=query,
            ):
                events.append(event)

            # Extract final text response
            final_text = None
            for e in events:
                content = e.get("content", {})
                parts = content.get("parts", [{}])
                if parts and parts[0].get("text") and not parts[0].get("functionCall"):
                    final_text = parts[0]["text"]

            if final_text:
                print(f"\n✓ Answer:\n{final_text[:400]}")
                results.append((category, True))
            else:
                print(f"No text response found. Events: {len(events)}")
                for e in events:
                    print(f"  Event: {e}")
                results.append((category, False))

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((category, False))

        await asyncio.sleep(2)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    for cat, ok in results:
        print(f"{'✓' if ok else '✗'} {cat}")
    print(f"\nPassed: {sum(1 for _, ok in results if ok)}/{len(results)}")

    return all(ok for _, ok in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
