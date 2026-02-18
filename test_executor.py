import asyncio
import os
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a_agents.cocktail_agent.cocktail_agent_executor import CocktailAgentExecutor

async def test_execution():
    os.environ["CT_MCP_SERVER_URL"] = "$(gcloud run services describe cocktail-mcp-ge-staging --region us-central1 --project dw-genai-dev --format='value(status.url)')/mcp/"
    
    executor = CocktailAgentExecutor()
    context = RequestContext(
        task_id="test",
        context_id="test_ctx",
        current_task=None
    )
    # mock get_user_input
    context.get_user_input = lambda: "Find a cocktail with rum"
    
    q = EventQueue()
    
    # Run the executor
    task = asyncio.create_task(executor.execute(context, q))
    
    async for event in q:
        print(event)
        if event.name in ("task/completed", "task/failed"):
            break
            
asyncio.run(test_execution())
