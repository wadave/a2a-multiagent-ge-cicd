# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Author: Dave Wang

"""Integration tests for deployed A2A agents (Cocktail and Weather)."""

import asyncio
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from test_config import (
    COCKTAIL_AGENT_ID,
    DEFAULT_POLL_ATTEMPTS,
    DEFAULT_TIMEOUT,
    LOCATION,
    POLL_INTERVAL,
    PROJECT_NUMBER,
    WEATHER_AGENT_ID,
)
from test_utils import print_test_summary, test_a2a_agent


async def test_cocktail_agent():
    """Test the Cocktail Agent with a sample query."""
    success, response = await test_a2a_agent(
        agent_id=COCKTAIL_AGENT_ID,
        agent_name="Cocktail Agent",
        query="What are the ingredients for a Margarita?",
        project_number=PROJECT_NUMBER,
        location=LOCATION,
        timeout=DEFAULT_TIMEOUT,
        poll_attempts=DEFAULT_POLL_ATTEMPTS,
        poll_interval=POLL_INTERVAL,
    )
    return success


async def test_weather_agent():
    """Test the Weather Agent with a sample query."""
    success, response = await test_a2a_agent(
        agent_id=WEATHER_AGENT_ID,
        agent_name="Weather Agent",
        query="What is the weather in San Francisco, CA?",
        project_number=PROJECT_NUMBER,
        location=LOCATION,
        timeout=DEFAULT_TIMEOUT,
        poll_attempts=DEFAULT_POLL_ATTEMPTS,
        poll_interval=POLL_INTERVAL,
    )
    return success


async def test_cocktail_random():
    """Test the Cocktail Agent with a random cocktail query."""
    success, response = await test_a2a_agent(
        agent_id=COCKTAIL_AGENT_ID,
        agent_name="Cocktail Agent (Random)",
        query="list a random cocktail",
        project_number=PROJECT_NUMBER,
        location=LOCATION,
        timeout=DEFAULT_TIMEOUT,
        poll_attempts=DEFAULT_POLL_ATTEMPTS,
        poll_interval=POLL_INTERVAL,
    )
    return success


async def test_weather_houston():
    """Test the Weather Agent with Houston weather query."""
    success, response = await test_a2a_agent(
        agent_id=WEATHER_AGENT_ID,
        agent_name="Weather Agent (Houston)",
        query="weather in Houston, TX",
        project_number=PROJECT_NUMBER,
        location=LOCATION,
        timeout=DEFAULT_TIMEOUT,
        poll_attempts=DEFAULT_POLL_ATTEMPTS,
        poll_interval=POLL_INTERVAL,
    )
    return success


async def main():
    """Run all remote agent tests."""
    print("=" * 80)
    print("TESTING DEPLOYED A2A AGENTS")
    print("=" * 80)

    results = []

    # Test Cocktail Agent
    cocktail_passed = await test_cocktail_agent()
    results.append(("Cocktail Agent - Margarita", cocktail_passed))

    await asyncio.sleep(2)

    # Test Weather Agent
    weather_passed = await test_weather_agent()
    results.append(("Weather Agent - San Francisco", weather_passed))

    await asyncio.sleep(2)

    # Test Cocktail Agent with random query
    cocktail_random_passed = await test_cocktail_random()
    results.append(("Cocktail Agent - Random", cocktail_random_passed))

    await asyncio.sleep(2)

    # Test Weather Agent with Houston
    weather_houston_passed = await test_weather_houston()
    results.append(("Weather Agent - Houston", weather_houston_passed))

    # Print summary
    all_passed = print_test_summary(results)
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
