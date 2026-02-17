# Tests

This directory contains all tests for the A2A multi-agent system.

## Structure

```
tests/
├── test_config.py          # Shared test configuration (loads from .env)
├── test_utils.py           # Shared test utilities
├── run_all_tests.py        # Master test runner
├── conftest.py             # Pytest configuration
├── integration/            # Integration tests for deployed agents
│   ├── test_deployed_agents.py      # Tests for A2A agents (Cocktail & Weather)
│   ├── test_hosting_agent.py        # Tests for Hosting Agent (ADK)
│   └── ...                          # Other integration tests
├── unit/                   # Unit tests
│   ├── test_agent_cards.py
│   └── ...
├── eval/                   # Evaluation tests
└── load_test/              # Load testing scripts
```

## Configuration

All tests use shared configuration from `test_config.py`, which loads values from environment variables:

- `PROJECT_ID` - GCP project ID
- `PROJECT_NUMBER` - GCP project number
- `GOOGLE_CLOUD_LOCATION` - GCP location (default: us-central1)
- `COCKTAIL_AGENT_ID` - Deployed Cocktail Agent ID
- `WEATHER_AGENT_ID` - Deployed Weather Agent ID
- `HOSTING_AGENT_ID` - Deployed Hosting Agent ID

These can be set in your `.env` file or as environment variables.

## Running Tests

### Run All Tests

```bash
cd tests
python run_all_tests.py
```

### Run Specific Test Suites

**Test Deployed A2A Agents (Cocktail & Weather):**
```bash
cd tests
python integration/test_deployed_agents.py
```

**Test Hosting Agent:**
```bash
cd tests
python integration/test_hosting_agent.py
```

### Run with pytest

```bash
pytest tests/
```

## Test Utilities

The `test_utils.py` module provides shared utilities:

- `get_gcloud_token()` - Get authentication token
- `test_a2a_agent()` - Test A2A agents via A2A protocol
- `test_adk_agent()` - Test ADK agents via agent_engines API
- `print_test_summary()` - Print test results summary

## Example Usage

```python
from test_config import COCKTAIL_AGENT_ID, PROJECT_NUMBER, LOCATION
from test_utils import test_a2a_agent

async def my_test():
    success, response = await test_a2a_agent(
        agent_id=COCKTAIL_AGENT_ID,
        agent_name="Cocktail Agent",
        query="What's in a margarita?",
        project_number=PROJECT_NUMBER,
        location=LOCATION,
    )
    assert success, "Test failed"
```

## Adding New Tests

1. Create test file in appropriate directory (integration, unit, etc.)
2. Import configuration from `test_config`
3. Import utilities from `test_utils`
4. No need to hard-code project IDs or agent IDs
5. Add to `run_all_tests.py` if it's an integration test

## Environment Setup

Ensure your environment has:
1. `.env` file with required variables (or set as env vars)
2. `gcloud` CLI authenticated
3. Required Python packages installed (`uv sync` or `pip install -r requirements.txt`)
