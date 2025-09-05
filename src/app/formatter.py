"""Output formatting module for generating markdown reports."""

import json
from typing import Any

from .models import CompleteReport, CriterionScore


class MarkdownFormatter:
    """Handles formatting of analysis results into markdown reports."""

    def format_complete_report(self, report: CompleteReport) -> str:
        """
        Format complete analysis report as markdown.

        Args:
            report: CompleteReport object with all analysis data

        Returns:
            Formatted markdown string
        """
        sections = []

        # Header
        sections.append(self._format_header(report))

        # Overall Score (must be first visible line)
        sections.append(self._format_overall_score(report.overall_score))

        # Gesamt-Scorecard
        sections.append(self._format_scorecard(report.aggregated_analysis.criteria_scores))

        # Consolidated analysis from OpenAI (replaces individual sections)
        if report.aggregated_analysis.raw_analysis:
            sections.append(report.aggregated_analysis.raw_analysis)
        else:
            # This should never happen since we removed fallbacks
            raise Exception("No consolidated analysis available and fallbacks removed")

        return "\n".join(sections)

    def _format_header(self, report: CompleteReport) -> str:
        """Format report header with metadata."""
        return "# Feedback zur Vorlesung\n\n"

    def _format_overall_score(self, overall_score: float) -> str:
        """Format the overall score section."""
        return f"**Overall Score (Tagesdurchschnitt): {overall_score} / 5**\n"

    def _format_scorecard(self, criteria_scores: list[CriterionScore]) -> str:
        """Format the main scorecard table."""
        lines = [
            "## Gesamt-Scorecard",
            "",
            "| Kriterium | Bewertung | Ampel | Begründung mit O-Ton |",
            "|-----------|-----------|-------|---------------------|",
        ]

        for criterion in criteria_scores:
            # Use the LLM-generated justification directly
            justification = criterion.justification

            lines.append(
                f"| {criterion.criterion_name_de} | {criterion.score} | {criterion.traffic_light} "
                f"| {justification} |"
            )

        lines.append("")
        return "\n".join(lines)

    def _format_strengths(self, strengths: list[str]) -> str:
        """Format the strengths section."""
        lines = ["## Stärken des Vortrags", ""]

        for strength in strengths:
            lines.append(f"- {strength}")

        lines.append("")
        return "\n".join(lines)

    def _format_improvements(self, improvements: list[str]) -> str:
        """Format the improvement suggestions section."""
        lines = ["## Konkrete Verbesserungsvorschläge", ""]

        priority_labels = ["Dringend", "Wichtig", "Nice-to-have"]

        for i, improvement in enumerate(improvements):
            label = priority_labels[i] if i < len(priority_labels) else "Zusätzlich"
            lines.append(f"- **{label}:** {improvement}")

        lines.append("")
        return "\n".join(lines)

    def _format_management_summary(self, management_summary: dict[str, Any]) -> str:
        """Format the management summary section."""
        lines = [
            "## Management Summary (für Akademieleitung)",
            "",
            "**Kurzfassung (3 Bullets):**",
        ]

        # Add bullet points
        bullets = management_summary.get("bullets", [])
        for bullet in bullets:
            lines.append(f"- {bullet}")

        lines.extend(
            [
                "",
                "**Ausführliche Version (Fließtext):**",
                management_summary.get("detailed", "Keine detaillierte Analyse verfügbar."),
                "",
            ]
        )

        return "\n".join(lines)

    def format_json_report(self, report: CompleteReport) -> str:
        """
        Format complete report as JSON.

        Args:
            report: CompleteReport object

        Returns:
            JSON string representation
        """
        # Convert to dictionary for JSON serialization
        report_dict = {
            "timestamp": report.timestamp.isoformat(),
            "overall_score": report.overall_score,
            "criteria_scores": [
                {
                    "criterion_key": cs.criterion_key,
                    "criterion_name_de": cs.criterion_name_de,
                    "score": cs.score,
                    "traffic_light": cs.traffic_light,
                    "justification": cs.justification,
                    "quotes": cs.quotes,
                }
                for cs in report.aggregated_analysis.criteria_scores
            ],
            "strengths": report.aggregated_analysis.strengths,
            "improvement_suggestions": report.aggregated_analysis.improvement_suggestions,
            "management_summary": report.aggregated_analysis.management_summary,
            "block_analyses": [
                {
                    "block_number": ba.block_number,
                    "time_range": ba.time_range,
                    "overall_block_score": ba.overall_block_score,
                    "criteria_scores": [
                        {
                            "criterion_key": cs.criterion_key,
                            "score": cs.score,
                            "justification": cs.justification,
                            "quotes": cs.quotes,
                        }
                        for cs in ba.criteria_scores
                    ],
                }
                for ba in report.block_analyses
            ],
            "metadata": report.metadata,
        }

        return json.dumps(report_dict, indent=2, ensure_ascii=False)

    def format_kurzfassung(self, report: CompleteReport) -> str:
        """
        Format kurzfassung (management summary) for Akademieleitung.

        Args:
            report: CompleteReport object

        Returns:
            Pre-formatted markdown string from LLM
        """
        management_summary = report.aggregated_analysis.management_summary
        if management_summary and "markdown" in management_summary:
            return management_summary["markdown"]
        # Fallback if no management summary available
        return f"""# Kurzfassung für Akademieleitung

## Kurzfassung (3 Bullets):
- Aktueller Overall Score: {report.overall_score} / 5
- Automatische Kurzfassung nicht verfügbar
- Detailbericht verfügbar

## Ausführliche Version (Fließtext):
Die automatische Generierung der Management-Kurzfassung war nicht möglich. Bitte konsultieren Sie
den detaillierten Analysebericht für weitere Informationen."""

    def format_block_summary(self, report: CompleteReport) -> str:
        """
        Format a brief summary of block analyses.

        Args:
            report: CompleteReport object

        Returns:
            Summary string for console output
        """
        if not report.block_analyses:
            return "Keine Blockanalysen verfügbar."

        lines = [
            f"Analysiert: {len(report.block_analyses)} Blöcke",
            f"Overall Score: {report.overall_score} / 5",
            "",
        ]

        for block in report.block_analyses:
            lines.append(
                f"Block {block.block_number} ({block.time_range}): {block.overall_block_score}/5"
            )

        return "\n".join(lines)
