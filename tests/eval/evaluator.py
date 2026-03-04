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
"""LLM-based evaluator using Google GenAI SDK Flex Tier.

Note: Flex Pay-as-you-go (Flex Tier) is primarily available in the 'global' location.
Recommended preview models for Flex: gemini-3-flash-preview, gemini-3.1-flash-image-preview, etc.
"""

import json
import logging

from google import genai
from google.genai.types import HttpOptions

logger = logging.getLogger(__name__)

class LLMEvaluator:
    """Evaluates agent responses using an LLM with Flex Tier."""

    def __init__(self, project_id: str, location: str = "global", model_id: str = "gemini-3-flash-preview"):
        """Initialize the LLM evaluator.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            model_id: Gemini model ID to use for evaluation
        """
        self.project_id = project_id
        self.location = location
        self.model_id = model_id

        # Initialize client with Flex Tier options
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=HttpOptions(
                api_version="v1",
                headers={
                    "X-Vertex-AI-LLM-Request-Type": "shared",
                    "X-Vertex-AI-LLM-Shared-Request-Type": "flex"
                },
                timeout=1800000,  # 30 minutes in milliseconds
            )
        )
        logger.info(f"Initialized LLMEvaluator with model {model_id} in {location} using Flex Tier")

    async def score_response(self, input_text: str, response_text: str, rubrics: list[dict]) -> dict[str, float]:
        """Score an agent response against multiple rubrics.

        Args:
            input_text: The user's original query
            response_text: The agent's response
            rubrics: List of rubric definitions from eval_config.json

        Returns:
            Dictionary mapping rubricId to a float score (0.0 to 1.0)
        """
        rubric_descriptions = "\n".join([
            f"- {r['rubricId']}: {r['rubricContent']['textProperty']}"
            for r in rubrics
        ])

        prompt = f"""
        You are an expert evaluator of AI agent responses.
        Evaluate the following agent response based on the provided user query and rubrics.

        User Query: {input_text}

        Agent Response:
        ---
        {response_text}
        ---

        Rubrics:
        {rubric_descriptions}

        For each rubric, provide a score between 0.0 (completely failing) and 1.0 (perfect).
        Return only a JSON object where keys are the rubric identifiers and values are the scores.
        Example: {{"relevance": 0.9, "helpfulness": 1.0, "format": 0.8, "tool_routing": 1.0}}
        """

        try:
            # Note: The google-genai SDK uses synchronous calls by default unless using generate_content_stream
            # or wrapped in an async way. For simplicity in this eval script, we'll call it and wrap if needed.
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                }
            )

            if response.text:
                scores = json.loads(response.text)
            else:
                logger.error("LLM returned empty response text")
                scores = {}

            # Ensure all requested rubrics are present, default to 0.0 if missing
            results = {}
            for r in rubrics:
                rid = r["rubricId"]
                results[rid] = float(scores.get(rid, 0.0))

            return results

        except Exception as e:
            logger.error(f"Error during LLM evaluation: {e}")
            # Fallback to zeros if evaluation fails
            return {r["rubricId"]: 0.0 for r in rubrics}
