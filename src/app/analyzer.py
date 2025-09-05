"""OpenAI API integration for analyzing lecture transcriptions."""

import json
import logging
from random import uniform
from time import sleep
from typing import Any

from openai import OpenAI

from .config import (
    EVALUATION_CRITERIA,
    MINI_ANALYSIS_PROMPT,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    TRAFFIC_LIGHTS,
)
from .models import BlockAnalysis, CriterionScore, TimeBlock

logger = logging.getLogger(__name__)


class LectureAnalyzer:
    """Handles OpenAI API integration for lecture analysis."""

    def __init__(self) -> None:
        """Initialize OpenAI client."""
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")

        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL

    def _create_analysis_schema(self) -> dict[str, Any]:
        """Create JSON schema for structured output from OpenAI."""
        criteria_properties = {}

        for criterion_key, criterion_info in EVALUATION_CRITERIA.items():
            criteria_properties[criterion_key] = {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 5,
                        "description": (
                            f"Score for {criterion_info['name_de']} (1-5, can be fractional)"
                        ),
                    },
                    "justification": {
                        "type": "string",
                        "description": "Brief justification (max 3 sentences)",
                    },
                    "quotes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Direct quotes from transcript (required for scores ≤3)",
                    },
                },
                "required": ["score", "justification", "quotes"],
                "additionalProperties": False,
            }

        return {
            "type": "object",
            "properties": {
                "block_analysis": {
                    "type": "object",
                    "properties": {
                        "criteria": {
                            "type": "object",
                            "properties": criteria_properties,
                            "required": list(EVALUATION_CRITERIA.keys()),
                            "additionalProperties": False,
                        },
                        "overall_block_score": {
                            "type": "number",
                            "description": "Average score for this block",
                        },
                    },
                    "required": ["criteria", "overall_block_score"],
                    "additionalProperties": False,
                }
            },
            "required": ["block_analysis"],
            "additionalProperties": False,
        }

    def _build_analysis_prompt(self, block: TimeBlock) -> str:
        """Build the complete analysis prompt for a time block."""
        criteria_description = "\n".join(
            [
                f"- **{info['name_de']}** (1-5):\n"
                + "\n".join([f"  - {score}: {desc}" for score, desc in info["rubric"].items()])
                for key, info in EVALUATION_CRITERIA.items()
            ]
        )

        return f"""{MINI_ANALYSIS_PROMPT}

## Bewertungskriterien:
{criteria_description}

## Zu analysierender Block:
**Block {block.block_number}** ({block.start_time} - {block.end_time})

**Transkriptinhalt:**
{block.content}

Bewerte jedes Kriterium von 1-5 basierend auf diesem Transkriptblock.
Bei Bewertungen ≤3 MÜSSEN wörtliche Zitate aus dem Transkript angegeben werden.
"""

    def _parse_api_response(self, response: dict[str, Any], block: TimeBlock) -> BlockAnalysis:
        """Parse OpenAI API response into BlockAnalysis object."""
        try:
            block_data = response.get("block_analysis", {})
            criteria_data = block_data.get("criteria", {})

            criterion_scores = []
            total_score = 0

            for criterion_key, criterion_info in EVALUATION_CRITERIA.items():
                criterion_result = criteria_data.get(criterion_key, {})

                score = criterion_result.get("score", 3)  # Default to 3 if missing
                justification = criterion_result.get("justification", "Keine Begründung verfügbar")
                quotes = criterion_result.get("quotes", [])

                # Ensure score is in valid range and round if float
                score = float(score) if score is not None else 3.0
                score = max(1.0, min(5.0, score))
                score = round(score)  # Round to nearest integer for traffic light logic

                # Get traffic light
                traffic_light = TRAFFIC_LIGHTS.get(score, "🟡")

                criterion_scores.append(
                    CriterionScore(
                        criterion_key=criterion_key,
                        criterion_name_de=criterion_info["name_de"],
                        score=score,
                        traffic_light=traffic_light,
                        justification=justification,
                        quotes=quotes,
                    )
                )

                total_score += score

            # Calculate overall block score
            overall_score = total_score / len(EVALUATION_CRITERIA) if EVALUATION_CRITERIA else 0

            return BlockAnalysis(
                block_number=block.block_number,
                time_range=f"{block.start_time}-{block.end_time}",
                criteria_scores=criterion_scores,
                overall_block_score=round(overall_score, 1),
            )

        except Exception as e:
            logger.error(f"Error parsing API response: {e}")
            raise Exception(
                f"Failed to parse API response for block {block.block_number}: {e}"
            ) from e

    def analyze_block(self, block: TimeBlock, retry_count: int = 3) -> BlockAnalysis:
        """
        Analyze a single time block using OpenAI API.

        Args:
            block: TimeBlock to analyze
            retry_count: Number of retries for API calls

        Returns:
            BlockAnalysis with scores and feedback
        """
        prompt = self._build_analysis_prompt(block)
        schema = self._create_analysis_schema()

        for attempt in range(retry_count):
            try:
                logger.info(f"Analyzing block {block.block_number}, attempt {attempt + 1}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Du bist ein Experte für Hochschuldidaktik. "
                                "Antworte ausschließlich in der vorgegebenen JSON-Struktur."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "lecture_analysis",
                            "schema": schema,
                            "strict": True,
                        },
                    },
                )

                # Parse response
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from OpenAI")

                response_data = json.loads(content)
                return self._parse_api_response(response_data, block)

            except Exception as e:
                logger.error(
                    f"Error analyzing block {block.block_number}, attempt {attempt + 1}: {e}"
                )

                if attempt < retry_count - 1:
                    # Exponential backoff with jitter
                    wait_time = (2**attempt) + uniform(0, 1)  # nosec B311 # noqa: S311
                    sleep(wait_time)
                    continue
                logger.error(
                    f"Failed to analyze block {block.block_number} after {retry_count} attempts"
                )
                raise Exception(
                    f"Failed to analyze block {block.block_number} after {retry_count} attempts"
                ) from None

        # This should never be reached
        raise Exception(f"Unexpected error in analyze_block for block {block.block_number}")

    def analyze_blocks(self, blocks: list[TimeBlock]) -> list[BlockAnalysis]:
        """
        Analyze all blocks sequentially.

        Args:
            blocks: List of TimeBlock objects to analyze

        Returns:
            List of BlockAnalysis results
        """
        if not blocks:
            return []

        logger.info(f"Starting analysis of {len(blocks)} blocks")
        analyses = []

        for i, block in enumerate(blocks, 1):
            logger.info(f"Analyzing block {i}/{len(blocks)}")
            analysis = self.analyze_block(block)
            analyses.append(analysis)

            # Small delay between requests to be nice to the API
            if i < len(blocks):
                sleep(1)

        logger.info(f"Completed analysis of all {len(blocks)} blocks")
        return analyses
