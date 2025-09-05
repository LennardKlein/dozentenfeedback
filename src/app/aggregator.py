"""Score aggregation and consolidation logic."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from .analyzer import LectureAnalyzer
from .config import EVALUATION_CRITERIA, TRAFFIC_LIGHTS, CriterionInfo
from .models import (
    AggregatedAnalysis,
    BlockAnalysis,
    CompleteReport,
    CriterionScore,
)

logger = logging.getLogger(__name__)


class ScoreAggregator:
    """Handles aggregation of block analyses into final report."""

    def __init__(self) -> None:
        """Initialize aggregator with OpenAI client for final consolidation."""
        self.analyzer = LectureAnalyzer()

    def aggregate_scores(self, block_analyses: list[BlockAnalysis]) -> AggregatedAnalysis:
        """
        Aggregate individual block analyses into consolidated analysis.

        Args:
            block_analyses: List of BlockAnalysis objects

        Returns:
            AggregatedAnalysis with consolidated scores and feedback
        """
        if not block_analyses:
            return self._create_empty_analysis()

        # Aggregate criterion scores
        aggregated_criteria = self._aggregate_criterion_scores(block_analyses)

        # Calculate overall score
        overall_score = sum(cs.score for cs in aggregated_criteria) / len(aggregated_criteria)
        overall_score = round(overall_score, 1)

        # Generate consolidated analysis using OpenAI
        consolidated_analysis = self._generate_consolidated_analysis(block_analyses)

        # Generate management summary for Akademieleitung
        management_summary_markdown = self._generate_management_summary(
            overall_score=overall_score,
            criteria_scores=aggregated_criteria,
            block_analyses=block_analyses,
        )

        return AggregatedAnalysis(
            overall_score=overall_score,
            criteria_scores=aggregated_criteria,
            raw_analysis=consolidated_analysis.get("raw_analysis"),
            management_summary={"markdown": management_summary_markdown},
        )

    def _aggregate_criterion_scores(
        self, block_analyses: list[BlockAnalysis]
    ) -> list[CriterionScore]:
        """Aggregate scores for each criterion across all blocks."""
        criterion_totals = defaultdict(list)
        criterion_quotes = defaultdict(list)
        criterion_justifications = defaultdict(list)

        # Collect all scores, quotes, and justifications for each criterion
        for block_analysis in block_analyses:
            for criterion_score in block_analysis.criteria_scores:
                criterion_totals[criterion_score.criterion_key].append(criterion_score.score)
                if criterion_score.quotes:
                    criterion_quotes[criterion_score.criterion_key].extend(criterion_score.quotes)
                if criterion_score.justification:
                    criterion_justifications[criterion_score.criterion_key].append(
                        criterion_score.justification
                    )

        aggregated_criteria = []

        for criterion_key, scores in criterion_totals.items():
            if not scores:
                continue

            # Calculate average score
            avg_score = sum(scores) / len(scores)
            rounded_score = round(avg_score, 1)

            # Get criterion info
            criterion_info: CriterionInfo | dict[str, Any] = EVALUATION_CRITERIA.get(
                criterion_key, {}
            )
            criterion_name = str(criterion_info.get("name_de", criterion_key))

            # Determine traffic light based on rounded score
            traffic_light_score = round(rounded_score)
            traffic_light = TRAFFIC_LIGHTS.get(traffic_light_score, "🟡")

            # Get all justifications and quotes for this criterion
            all_justifications = criterion_justifications.get(criterion_key, [])
            all_quotes = criterion_quotes.get(criterion_key, [])

            # Generate LLM-based reasoning for this criterion
            justification = self._generate_criterion_reasoning(
                criterion_key=criterion_key,
                criterion_name=criterion_name,
                score=rounded_score,
                justifications=all_justifications,
                quotes=all_quotes,
            )

            # Select representative quotes (prioritize for scores ≤3)
            if rounded_score <= 3:
                selected_quotes = all_quotes[:2]  # Take up to 2 most relevant quotes
            else:
                selected_quotes = (
                    all_quotes[:1] if all_quotes else []
                )  # Optional quote for good scores

            aggregated_criteria.append(
                CriterionScore(
                    criterion_key=criterion_key,
                    criterion_name_de=criterion_name,
                    score=rounded_score,
                    traffic_light=traffic_light,
                    justification=justification,
                    quotes=selected_quotes,
                )
            )

        # Sort by criterion order in config
        criterion_order = list(EVALUATION_CRITERIA.keys())
        aggregated_criteria.sort(
            key=lambda x: criterion_order.index(x.criterion_key)
            if x.criterion_key in criterion_order
            else 999
        )

        return aggregated_criteria

    def _generate_criterion_reasoning(
        self,
        criterion_key: str,
        criterion_name: str,
        score: float,
        justifications: list[str],
        quotes: list[str],
    ) -> str:
        """Generate LLM reasoning for a specific criterion score."""
        try:
            # Prepare justifications text
            justifications_text = (
                "\n".join([f"- {j}" for j in justifications])
                if justifications
                else "Keine spezifischen Begründungen verfügbar."
            )

            # Prepare quotes text
            quotes_text = (
                "\n".join([f'"{q}"' for q in quotes[:3]])
                if quotes
                else "Keine relevanten Zitate verfügbar."
            )

            prompt = f"""Du bist ein erfahrener Hochschuldidaktiker. Erstelle eine SEHR KURZE \
Begründung (maximal 200-250 Zeichen inkl. Leerzeichen) für diese Bewertung.

Kriterium: {criterion_name}
Durchschnittliche Bewertung: {score}/5

1. Begründungen aus den Einzelblöcken:
{justifications_text}

2. Relevante Zitate aus dem Transkript:
{quotes_text}

WICHTIG: Maximal 200-250 Zeichen!
Bei Scores ≤3: Ein kurzes Problem + optional ein kurzes relevantes Zitat aus dem \
Transkript (oben 2.).
Bei Scores >3: Kurze positive Aussage.

Geben Sie das Kriterium oder die Bewertung NICHT in der Antwort an.
"""

            response = self.analyzer.client.chat.completions.create(
                model=self.analyzer.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du bist ein Experte für Hochschuldidaktik. Erstelle EXTREM KURZE, "
                            "tabellengeeignete Begründungen (max 200-250 Zeichen). "
                            "Verwende Kurzform und Abkürzungen."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            if content:
                # Clean up the response for table format
                cleaned_content = content.strip()
                # Remove newlines and replace with spaces
                cleaned_content = cleaned_content.replace("\n", " ").replace("\r", " ")
                # Remove pipe characters that would break the table
                cleaned_content = cleaned_content.replace("|", "")
                # Collapse multiple spaces into single spaces
                cleaned_content = " ".join(cleaned_content.split())
                return " ".join(cleaned_content.split())
            logger.warning(f"Empty response for criterion {criterion_key}")
            return f"Bewertung: {score}/5 - Automatische Begründung nicht verfügbar."

        except Exception as e:
            logger.error(f"Error generating reasoning for criterion {criterion_key}: {e}")
            return (
                f"Bewertung: {score}/5 - Begründung aufgrund technischer Probleme nicht verfügbar."
            )

    def _generate_management_summary(
        self,
        overall_score: float,
        criteria_scores: list[CriterionScore],
        block_analyses: list[BlockAnalysis],
    ) -> str:
        """Generate management summary as formatted markdown for Akademieleitung."""
        try:
            # Prepare summary of criteria with low scores (≤3)
            critical_criteria = [cs for cs in criteria_scores if cs.score <= 3]
            critical_summary = ", ".join([cs.criterion_name_de for cs in critical_criteria[:3]])

            # Prepare summary of criteria with high scores (>4)
            strong_criteria = [cs for cs in criteria_scores if cs.score > 4]
            strong_summary = ", ".join([cs.criterion_name_de for cs in strong_criteria[:3]])

            # Prepare block analysis summary
            block_summary = []
            for block in block_analyses[-3:]:  # Last 3 blocks for trend
                block_summary.append(f"Block {block.block_number}: {block.overall_block_score}/5")

            prompt = f"""Du bist ein erfahrener Hochschuldidaktiker und erstellst eine \
Kurzfassung für die Akademieleitung.

Erstelle eine Kurzfassung im folgenden Markdown-Format (EXAKT dieses Format verwenden):

# Kurzfassung für Akademieleitung

## Kurzfassung
- Aktueller Overall Score: {overall_score} / 5 [hier optional Trendinfo einfügen, falls erkennbar]
- [Zweiter zweiter Punkt der Zusammenfassung]
- [Dritter Punkt der Zusammenfassung]

## Ausführliche Version
[Ein Absatz mit 5-7 Sätzen über Gesamtsituation, Trends, kritische Punkte, \
positive Aspekte, und konkrete Handlungsempfehlungen für die Akademieleitung]

DATEN ZUR ANALYSE:
Overall Score: {overall_score}/5
Kritische Bereiche (≤3): {critical_summary if critical_summary else "Keine"}
Starke Bereiche (>4): {strong_summary if strong_summary else "Keine"}
Letzte Blöcke: {" | ".join(block_summary)}

WICHTIG: Verwende das EXAKTE Markdown-Format oben. Keine zusätzlichen \
Überschriften oder Abschnitte."""

            response = self.analyzer.client.chat.completions.create(
                model=self.analyzer.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du bist ein Experte für Hochschuldidaktik. Erstelle präzise "
                            "Management-Summaries im vorgegebenen Markdown-Format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            if content:
                return content.strip()
            logger.warning("Empty response for management summary")
            return f"""# Kurzfassung für Akademieleitung

## Kurzfassung (3 Bullets):
- Aktueller Overall Score: {overall_score} / 5
- Automatische Analyse nicht verfügbar
- Manuelle Prüfung erforderlich

## Ausführliche Version (Fließtext):
Die automatische Generierung der Management-Kurzfassung war nicht möglich. \
Bitte prüfen Sie die detaillierten Analyseergebnisse manuell."""

        except Exception as e:
            logger.error(f"Error generating management summary: {e}")
            return f"""# Kurzfassung für Akademieleitung

## Kurzfassung (3 Bullets):
- Aktueller Overall Score: {overall_score} / 5
- Technisches Problem bei der Analyse
- Detailbericht verfügbar

## Ausführliche Version (Fließtext):
Die Generierung der Management-Kurzfassung schlug aufgrund eines technischen \
Problems fehl. Die detaillierten Analyseergebnisse sind im Hauptbericht verfügbar."""

    def _generate_consolidated_analysis(
        self, block_analyses: list[BlockAnalysis]
    ) -> dict[str, Any]:
        """Generate consolidated analysis using OpenAI."""
        try:
            # Prepare summary of all block analyses
            analysis_summary = self._prepare_analysis_summary(block_analyses)

            prompt = f"""Du bist ein erfahrener Hochschuldidaktiker und \
Performance-Coach für Dozierende.

Basierend auf den folgenden Mini-Analysen der gesamten 4h-Vorlesung, \
erstelle eine konsolidierte Analyse:

{analysis_summary}

Erstelle:
1. **Max. 3 Stärken des Vortrags**
2. **Max. 3 Konkrete Verbesserungsvorschläge**

Nutze markdown format für die Ausgabe wie:

## Stärken des Vortrags

1.
2.
3.

## Konkrete Verbesserungsvorschläge

1.
2.
3.
"""

            logger.info("Generating consolidated analysis using OpenAI...")

            response = self.analyzer.client.chat.completions.create(
                model=self.analyzer.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du bist ein Experte für Hochschuldidaktik. "
                            "Antworte genau im vorgegebenen Format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            if content:
                logger.info("Successfully generated consolidated analysis")
                return {"raw_analysis": content.strip()}
            logger.error("Empty response from OpenAI for consolidated analysis")
            raise Exception("OpenAI returned empty response for consolidated analysis")

        except Exception as e:
            logger.error(f"Error generating consolidated analysis: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to generate consolidated analysis: {e}") from e

    def _prepare_analysis_summary(self, block_analyses: list[BlockAnalysis]) -> str:
        """Prepare a summary of all block analyses for consolidation."""
        summary_parts = []

        for block in block_analyses:
            block_summary = f"\n## Block {block.block_number} ({block.time_range})\n"
            block_summary += f"Overall Score: {block.overall_block_score}\n\n"

            for criterion in block.criteria_scores:
                block_summary += (
                    f"- {criterion.criterion_name_de}: {criterion.score}/5 - "
                    f"{criterion.justification}\n"
                )
                if criterion.quotes:
                    for quote in criterion.quotes[:1]:  # Include first quote
                        block_summary += f'  > "{quote}"\n'

            summary_parts.append(block_summary)

        return "\n".join(summary_parts)

    def _create_empty_analysis(self) -> AggregatedAnalysis:
        """Create empty analysis when no blocks provided."""
        return AggregatedAnalysis(
            overall_score=0.0,
            criteria_scores=[],
            strengths=["Keine Analyse möglich - keine Daten verfügbar"],
            improvement_suggestions=["Transkript prüfen und erneut analysieren"],
            management_summary={
                "bullets": ["Keine verwertbaren Daten verfügbar"],
                "detailed": (
                    "Es konnten keine verwertbaren Daten aus dem Transkript extrahiert werden."
                ),
            },
        )

    def create_complete_report(
        self,
        block_analyses: list[BlockAnalysis],
    ) -> CompleteReport:
        """
        Create complete analysis report.

        Args:
            block_analyses: Individual block analysis results

        Returns:
            CompleteReport with all analysis components
        """
        # Generate aggregated analysis
        aggregated_analysis = self.aggregate_scores(block_analyses)

        # Create metadata
        metadata = {
            "total_blocks": len(block_analyses),
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": self.analyzer.model,
        }

        return CompleteReport(
            overall_score=aggregated_analysis.overall_score,
            aggregated_analysis=aggregated_analysis,
            block_analyses=block_analyses,
            metadata=metadata,
        )
