import asyncio
from a2a_agents.hosting_agent.adk_agent import a2a_agent
from a2a.server.agent_execution.context import RequestContext

async def main():
    ctx = RequestContext(
        task_id="test_task",
        context_id="test_context",
        messages=[{"role": "user", "parts": [{"text": "What is the ingredient for a Margarita"}]}]
    )
    # The A2A framework execute function relies on grpc/http layers, 
    # but we can try invoking the cocktail executor directly.
    from a2a_agents.cocktail_agent.cocktail_agent_executor import CocktailAgentExecutor
    from a2a.server.events.event_queue import EventQueue
    
    executor = CocktailAgentExecutor()
    q = EventQueue()
    
    task = asyncio.create_task(executor.execute(ctx, q))
    
    async for event in q:
        print(f"Event: {event}")
        if event.name == "task/completed" or event.name == "task/failed":
            break

asyncio.run(main())
