"""Configuration module for the Dozenten Feedback Analysis System."""

import os
from typing import TypedDict

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# Chunking Configuration
CHUNK_DURATION_MINUTES = 30
MAX_TOKENS_PER_CHUNK = 15000


# Type definitions
class CriterionInfo(TypedDict):
    name_en: str
    name_de: str
    rubric: dict[int, str]


# Evaluation Criteria with names and rubrics
EVALUATION_CRITERIA: dict[str, CriterionInfo] = {
    "struktur_klarheit": {
        "name_en": "Structure & Clarity",
        "name_de": "Struktur & Klarheit",
        "rubric": {
            5: "Klare Agenda, roter Faden, saubere Übergänge",
            4: "Größtenteils klar, kleinere Sprünge",
            3: "Teilweise nachvollziehbar, unsicherer Einstieg",
            2: "Kein erkennbarer Ablauf, Orientierung fehlt",
            1: "Chaotisch, keine Struktur",
        },
    },
    "erklaerungskompetenz": {
        "name_en": "Explanation Competence",
        "name_de": "Erklärungskompetenz",
        "rubric": {
            5: "Komplexes einfach erklärt, Beispiele, präzise Antworten",
            4: "Verständlich, aber teils abstrakt/schnell",
            3: "Teils klar, teils vage",
            2: "Oberflächlich, ausweichende Antworten",
            1: "Unverständlich, keine Erklärung",
        },
    },
    "praxisbezug": {
        "name_en": "Practical Relevance",
        "name_de": "Praxisbezug",
        "rubric": {
            5: "Mehrere konkrete, sofort anwendbare Beispiele",
            4: "Beispiele vorhanden, teils allgemein",
            3: "Wenige Beispiele, oft oberflächlich",
            2: "Vage, kaum Mehrwert",
            1: "Kein Praxisbezug",
        },
    },
    "interaktivitaet": {
        "name_en": "Interactivity",
        "name_de": "Interaktivität",
        "rubric": {
            5: "Mehrere echte Interaktionen (Fragen, Gruppenarbeit, Diskussion)",
            4: "Mind. eine Interaktion, aber oberflächlich",
            3: "Angesetzt, aber abgebrochen/zu kurz",
            2: "Kaum Interaktion, nur rhetorische Fragen",
            1: "Keine Interaktion",
        },
    },
    "zeitmanagement": {
        "name_en": "Time Management",
        "name_de": "Zeitmanagement",
        "rubric": {
            5: "Zeitplan eingehalten, Pausen korrekt",
            4: "Kleinere Abweichungen",
            3: "Überzogen/zu schnell, aber tolerierbar",
            2: "Deutlich überzogen (>10-15 Min.)",
            1: "Keine Zeitkontrolle",
        },
    },
    "zielgruppenanpassung": {
        "name_en": "Target Group Adaptation",
        "name_de": "Anpassung an Zielgruppe",
        "rubric": {
            5: "Perfekt anfängergerecht, kein Vorwissen nötig",
            4: "Großteils passend, einzelne Stellen komplex",
            3: "Mischform: teils verständlich, teils abstrakt",
            2: "Meist zu schwer/oberflächlich",
            1: "Zielgruppe komplett verfehlt",
        },
    },
    "kommunikationsstil": {
        "name_en": "Communication Style",
        "name_de": "Kommunikationsstil",
        "rubric": {
            5: "Klar, strukturiert, motivierend, wertschätzend",
            4: "Positiv, kleinere Schwächen (Füllwörter)",
            3: "Freundlich, aber monoton/unsicher",
            2: "Holprig, distanziert",
            1: "Negativ, verwirrend",
        },
    },
    "engagement_begeisterung": {
        "name_en": "Engagement & Enthusiasm",
        "name_de": "Engagement & Begeisterung",
        "rubric": {
            5: "Hohe Energie, Begeisterung spürbar",
            4: "Engagement vorhanden, nicht durchgängig",
            3: "Bemüht, aber routiniert/monoton",
            2: "Wenig Leidenschaft",
            1: "Lustlos",
        },
    },
    "empathie_umgang": {
        "name_en": "Empathy & Student Interaction",
        "name_de": "Empathie & Umgang mit Teilnehmern",
        "rubric": {
            5: "Sehr geduldig, jede Frage ernst genommen",
            4: "Freundlich, einzelne Antworten zu kurz",
            3: "Respektvoll, teils abweisend/unklar",
            2: "Mehrfach ungeduldig",
            1: "Respektlos",
        },
    },
    "technische_herausforderungen": {
        "name_en": "Technical Challenges",
        "name_de": "Umgang mit technischen Herausforderungen",
        "rubric": {
            5: "Souverän gelöst, kein Einfluss",
            4: "Kleinere Störungen, gut behoben",
            3: "Störungen leicht beeinträchtigend",
            2: "Probleme erheblich",
            1: "Sitzung massiv gestört",
        },
    },
}

# Traffic light mapping
TRAFFIC_LIGHTS = {5: "🟢", 4: "🟢", 3: "🟡", 2: "🔴", 1: "🔴"}

# Prompts
MINI_ANALYSIS_PROMPT = """Du bist ein erfahrener Hochschuldidaktiker und Performance-Coach für
Dozierende. Deine Aufgabe ist es, basierend auf dem Transkript der heutigen Vorlesung (4 Stunden
Online-Session via Zoom, inkl. 1-2 Pausen), ein präzises, effizientes und praxisnahes Feedback zu
geben.

Ziel:
- Unterstützung und Coaching der Dozierenden (mit konkreten Beispielen und sofort umsetzbaren
  Tipps).
- Qualitätssicherung für die Akademieleitung (klare Bewertung anhand definierter Standards).
- Dozierende sollen spüren, dass ihre Performance aktiv beobachtet und bewertet wird.

Rahmenbedingungen:
- Vorlesung immer mit Theorie-Input und mindestens einer Interaktionsphase (Gruppenarbeit, offene
  Fragen, Diskussion).
- Pausen (mind. 1-2) sind verpflichtend.
- Gruppengröße 6-20 TN, Teilnehmende oft ohne Vorwissen, unsicher und teils schwierige
  Gruppendynamik.
- Akademie stellt Folien, Tools können ergänzend genutzt werden; wenn Tools vorgestellt werden,
  sollen sie auch praktisch gezeigt werden.

Bewerte die Vorlesung anhand der 10 Kriterien (1-5 Punkte). Bei Bewertungen von 3 oder schlechter
MUSS mindestens 1-2 vollständige wörtliche Sätze (O-Ton) aus dem Transkript als Beleg angegeben
werden.

WICHTIG: Antworte ausschließlich in der vorgegebenen JSON-Struktur."""

AGGREGATION_PROMPT = """Du bist ein erfahrener Hochschuldidaktiker und Performance-Coach für
Dozierende. Hier sind die Mini-Analysen der gesamten 4h-Vorlesung, blockweise aufbereitet.

Erstelle daraus eine konsolidierte Analyse:

Ziel:
- Unterstützung und Coaching der Dozierenden (mit konkreten Beispielen und sofort umsetzbaren
  Tipps).
- Qualitätssicherung für die Akademieleitung (klare Bewertung anhand definierter Standards).
- Dozierende sollen spüren, dass ihre Performance aktiv beobachtet und bewertet wird.

Rahmenbedingungen:
- Vorlesung immer mit Theorie-Input und mindestens einer Interaktionsphase (Gruppenarbeit, offene
  Fragen, Diskussion).
- Pausen (mind. 1-2) sind verpflichtend.
- Gruppengröße 6-20 TN, Teilnehmende oft ohne Vorwissen, unsicher und teils schwierige
  Gruppendynamik.
- Akademie stellt Folien, Tools können ergänzend genutzt werden; wenn Tools vorgestellt werden,
  sollen sie auch praktisch gezeigt werden.

Führe die Ergebnisse aller Mini-Analysen zu einer konsolidierten Gesamt-Scorecard zusammen.
Berechne für jedes der 10 Kriterien den Durchschnittswert aus allen Blöcken (auf eine
Nachkommastelle).

WICHTIG: Antworte ausschließlich in der vorgegebenen JSON-Struktur."""
