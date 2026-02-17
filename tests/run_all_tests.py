# Copyright 2025 Google LLC
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

"""Run all integration tests for the multi-agent system."""
import asyncio
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from test_config import (
    COCKTAIL_AGENT_ID,
    WEATHER_AGENT_ID,
    HOSTING_AGENT_ID,
    PROJECT_ID,
    PROJECT_NUMBER,
    LOCATION,
)


def print_config():
    """Print test configuration."""
    print("="*80)
    print("TEST CONFIGURATION")
    print("="*80)
    print(f"Project ID: {PROJECT_ID}")
    print(f"Project Number: {PROJECT_NUMBER}")
    print(f"Location: {LOCATION}")
    print(f"Cocktail Agent ID: {COCKTAIL_AGENT_ID}")
    print(f"Weather Agent ID: {WEATHER_AGENT_ID}")
    print(f"Hosting Agent ID: {HOSTING_AGENT_ID}")
    print("="*80)
    print()


async def run_deployed_agents_tests():
    """Run tests for deployed A2A agents."""
    print("\n" + "="*80)
    print("RUNNING: Deployed A2A Agents Tests")
    print("="*80)

    from integration.test_deployed_agents import main as test_deployed
    return await test_deployed()


async def run_hosting_agent_tests():
    """Run tests for hosting agent."""
    print("\n" + "="*80)
    print("RUNNING: Hosting Agent Tests")
    print("="*80)

    from integration.test_hosting_agent import main as test_hosting
    return await test_hosting()


async def main():
    """Run all tests."""
    print_config()

    all_results = []

    # Test deployed A2A agents
    try:
        deployed_passed = await run_deployed_agents_tests()
        all_results.append(("Deployed A2A Agents", deployed_passed))
    except Exception as e:
        print(f"\n✗ Error running deployed agents tests: {e}")
        all_results.append(("Deployed A2A Agents", False))

    await asyncio.sleep(3)

    # Test hosting agent
    try:
        hosting_passed = await run_hosting_agent_tests()
        all_results.append(("Hosting Agent", hosting_passed))
    except Exception as e:
        print(f"\n✗ Error running hosting agent tests: {e}")
        all_results.append(("Hosting Agent", False))

    # Final summary
    print("\n" + "="*80)
    print("OVERALL TEST SUMMARY")
    print("="*80)

    for test_suite, passed in all_results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_suite}")

    all_passed = all(result[1] for result in all_results)
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TEST SUITES PASSED!")
    else:
        print("✗ SOME TEST SUITES FAILED")
    print("="*80)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
