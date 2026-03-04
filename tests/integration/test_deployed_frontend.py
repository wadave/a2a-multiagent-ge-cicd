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

"""Integration test for deployed frontend UI."""
import asyncio
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from test_config import FRONTEND_URL


async def test_frontend_ui():
    """Test the deployed frontend UI."""

    frontend_url = FRONTEND_URL
    if not frontend_url:
        print("ERROR: FRONTEND_URL not configured. Set PROJECT_NUMBER env var.")
        return False

    print("="*80)
    print("TESTING DEPLOYED FRONTEND UI")
    print("="*80)
    print(f"\nFrontend URL: {frontend_url}")
    print("\nTo test the UI:")
    print(f"1. Open: {frontend_url}")
    print("2. Try these queries:")
    print("   - 'weather in Houston, TX'")
    print("   - 'what's in a margarita?'")
    print("   - 'list a random cocktail'")
    print("   - 'weather in Dallas, TX'")
    print("\n" + "="*80)

    # Test accessibility
    import httpx

    print("\nTesting frontend accessibility...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(frontend_url)
            if response.status_code == 200:
                print(f"✓ Frontend is accessible (HTTP {response.status_code})")
                print(f"✓ Frontend deployed at: {frontend_url}")
                return True
            else:
                print(f"✗ Frontend returned HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error accessing frontend: {e}")
            return False


async def main():
    """Run frontend test."""
    success = await test_frontend_ui()

    print("\n" + "="*80)
    if success:
        print("✓ FRONTEND DEPLOYMENT TEST PASSED!")
        print("\nNext step: Open the URL in your browser and test the chat interface")
    else:
        print("✗ FRONTEND DEPLOYMENT TEST FAILED")
    print("="*80)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
