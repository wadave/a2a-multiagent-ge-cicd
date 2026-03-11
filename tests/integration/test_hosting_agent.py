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

"""Integration tests for the deployed Hosting Agent (ADK)."""

import asyncio
import sys
from pathlib import Path

import pytest

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from test_config import (
    DEFAULT_USER_ID,
    HOSTING_AGENT_RESOURCE_NAME,
    LOCATION,
    PROJECT_ID,
)
from test_utils import print_test_summary, test_adk_agent


async def test_hosting_agent_weather():
    """Test the Hosting Agent with a weather query."""
    if not HOSTING_AGENT_RESOURCE_NAME or not PROJECT_ID:
        pytest.skip("HOSTING_AGENT_ID and PROJECT_ID must be configured")
    success, response = await test_adk_agent(
        agent_resource_name=HOSTING_AGENT_RESOURCE_NAME,
        query="weather in Dallas, TX",
        project_id=PROJECT_ID,
        location=LOCATION,
        user_id=DEFAULT_USER_ID,
    )
    assert success, "Hosting Agent weather (Dallas) test failed"
    return success


async def test_hosting_agent_cocktail():
    """Test the Hosting Agent with a cocktail query."""
    if not HOSTING_AGENT_RESOURCE_NAME or not PROJECT_ID:
        pytest.skip("HOSTING_AGENT_ID and PROJECT_ID must be configured")
    success, response = await test_adk_agent(
        agent_resource_name=HOSTING_AGENT_RESOURCE_NAME,
        query="what's in a margarita?",
        project_id=PROJECT_ID,
        location=LOCATION,
        user_id=DEFAULT_USER_ID,
    )
    assert success, "Hosting Agent cocktail (Margarita) test failed"
    return success


async def test_hosting_agent_random_cocktail():
    """Test the Hosting Agent with a random cocktail query."""
    if not HOSTING_AGENT_RESOURCE_NAME or not PROJECT_ID:
        pytest.skip("HOSTING_AGENT_ID and PROJECT_ID must be configured")
    success, response = await test_adk_agent(
        agent_resource_name=HOSTING_AGENT_RESOURCE_NAME,
        query="list a random cocktail",
        project_id=PROJECT_ID,
        location=LOCATION,
        user_id=DEFAULT_USER_ID,
    )
    assert success, "Hosting Agent cocktail (Random) test failed"
    return success


async def test_hosting_agent_houston_weather():
    """Test the Hosting Agent with Houston weather query."""
    if not HOSTING_AGENT_RESOURCE_NAME or not PROJECT_ID:
        pytest.skip("HOSTING_AGENT_ID and PROJECT_ID must be configured")
    success, response = await test_adk_agent(
        agent_resource_name=HOSTING_AGENT_RESOURCE_NAME,
        query="weather in Houston, TX",
        project_id=PROJECT_ID,
        location=LOCATION,
        user_id=DEFAULT_USER_ID,
    )
    assert success, "Hosting Agent weather (Houston) test failed"
    return success


async def main():
    """Run all hosting agent tests."""
    print("=" * 80)
    print("TESTING DEPLOYED HOSTING AGENT (ADK)")
    print("=" * 80)

    results = []

    # Test weather queries
    try:
        dallas_passed = await test_hosting_agent_weather()
    except AssertionError:
        dallas_passed = False
    results.append(("Hosting Agent - Weather (Dallas)", dallas_passed))

    await asyncio.sleep(2)

    try:
        houston_passed = await test_hosting_agent_houston_weather()
    except AssertionError:
        houston_passed = False
    results.append(("Hosting Agent - Weather (Houston)", houston_passed))

    await asyncio.sleep(2)

    # Test cocktail queries
    try:
        margarita_passed = await test_hosting_agent_cocktail()
    except AssertionError:
        margarita_passed = False
    results.append(("Hosting Agent - Cocktail (Margarita)", margarita_passed))

    await asyncio.sleep(2)

    try:
        random_passed = await test_hosting_agent_random_cocktail()
    except AssertionError:
        random_passed = False
    results.append(("Hosting Agent - Cocktail (Random)", random_passed))

    # Print summary
    all_passed = print_test_summary(results)
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
