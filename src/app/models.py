"""Pydantic models for structured outputs from OpenAI API."""

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class CriterionScore(BaseModel):
    """Individual criterion evaluation with score, justification, and quotes."""

    criterion_key: str = Field(description="Key identifier for the criterion")
    criterion_name_de: str = Field(description="Name of the criterion")
    score: Union[int, float] = Field(
        ge=1, le=5, description="Score from 1-5 (accepts floats, will be rounded)"
    )
    traffic_light: str = Field(description="Traffic light emoji (🟢🟡🔴)")
    justification: str = Field(description="Brief justification (max 3 sentences)")
    quotes: list[str] = Field(
        default_factory=list, description="Direct quotes from transcript (required for scores ≤3)"
    )


class TimeBlock(BaseModel):
    """Represents a 30-minute time block of the lecture."""

    block_number: Union[int, str] = Field(
        description="Sequential block number (can be string for sub-blocks like '2.1')"
    )
    start_time: Optional[str] = Field(description="Start time (HH:MM format)")
    end_time: Optional[str] = Field(description="End time (HH:MM format)")
    content: str = Field(description="Raw transcript content for this block")


class BlockAnalysis(BaseModel):
    """Analysis result for a single 30-minute block."""

    block_number: Union[int, str] = Field(
        description="Sequential block number (can be string for sub-blocks)"
    )
    time_range: str = Field(description="Time range (e.g., '09:00-09:30')")
    criteria_scores: list[CriterionScore] = Field(description="Scores for all 10 criteria")
    overall_block_score: float = Field(description="Average score for this block")


class AggregatedAnalysis(BaseModel):
    """Complete aggregated analysis for the entire lecture."""

    overall_score: float = Field(description="Overall daily average score")
    criteria_scores: list[CriterionScore] = Field(
        description="Aggregated scores for all 10 criteria"
    )
    raw_analysis: Optional[str] = Field(
        default=None, description="Raw markdown analysis from OpenAI (replaces individual sections)"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Legacy field - kept for backward compatibility"
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list, description="Legacy field - kept for backward compatibility"
    )
    management_summary: dict[str, Any] = Field(
        default_factory=dict, description="Legacy field - kept for backward compatibility"
    )


class CompleteReport(BaseModel):
    """Complete analysis report including all sections."""

    timestamp: datetime = Field(default_factory=datetime.now)
    overall_score: float = Field(description="Overall daily average score")
    aggregated_analysis: AggregatedAnalysis = Field(description="Main analysis results")
    block_analyses: list[BlockAnalysis] = Field(description="Individual block analyses")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the analysis"
    )
