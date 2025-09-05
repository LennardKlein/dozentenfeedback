#!/usr/bin/env python3
"""
Test script to generate PDF reports locally for design testing
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd() / "src"))

from app.pdf_formatter import PDFReportGenerator
from datetime import datetime

# Sample test data that mimics real output
test_report = {
    'overall_score': 3.8,
    'total_blocks': 3,
    'criteria_scores': {
        'Struktur & Klarheit': 2.7,
        'Erklärungskompetenz': 3.3,
        'Praxisbezug': 3.3,
        'Interaktivität': 4.0,
        'Zeitmanagement': 4.0,
        'Anpassung an Zielgruppe': 3.7,
        'Kommunikationsstil': 4.0,
        'Engagement & Begeisterung': 4.0,
        'Empathie & Umgang mit Teilnehmern': 4.3,
        'Umgang mit technischen Herausforderungen': 4.3
    },
    'summary': """# Kurzfassung für Akademieleitung

## Kurzfassung - Aktueller Overall Score: 3.8 / 5 [positiver Trend erkenntbar]

**Zwischenzeitliche Evaluation** - Stärkere Leistungen im Bereich Empathie und technischer Kompetenz.

## Ausführliche Version

Die aktuelle Evaluation der akademischen Lehre zeigt einen **Overall Score von 3.8/5**, wobei ein positiver Trend aus den letzten Blöcken erkennbar ist. Während Block 1 mit 2.9/5 den niedrigsten Score aufwies, zeigen die folgenden Blöcke eine erhebliche Verbesserung, insbesondere Block 3 mit 4.7/5.

**Kritische Bereiche** die Aufmerksamkeit erfordern, sind Struktur und Klarheit der Inhalte, da diese jeweils Bewertungen von ≤3 erhielten. Positiv hervorzuheben sind die Empathie und der effektive Umgang mit technischen Herausforderungen, die in den Bewertungen konstant über 4 lagen.

### Stärken:
- Empathie & Umgang mit Teilnehmern
- Umgang mit technischen Herausforderungen  
- Engagement & Begeisterung

### Verbesserungspotenziale:
- Struktur & Klarheit der Präsentation
- Stärkere Einbindung von Praxisbeispielen
- Bessere Zeitplanung für komplexe Themen

**DATEN ZUR ANALYSE:**
- Overall Score: 3.8/5
- Kritische Bereiche (≤3): Struktur & Klarheit
- Stärke Bereiche (≥4): Empathie, Umgang mit Teilnehmern
- Letzte Blöcke: Block 1: 2.9/5 | Block 2: 3.7/5 | Block 3: 4.7/5""",
    'strengths': [
        'Sehr gute Empathie und Umgang mit Teilnehmerfragen',
        'Effektiver Umgang mit technischen Problemen während der Präsentation',
        'Hohes Engagement und Begeisterung für das Thema erkennbar',
        'Gute Kommunikation und verständliche Erklärungen',
        'Positive Entwicklung über die Blöcke hinweg'
    ],
    'improvements': [
        'Struktur und Klarheit der Präsentation verbessern',
        'Mehr konkrete Praxisbeispiele einbauen',
        'Zeitmanagement bei komplexen Themen optimieren',
        'Klarere Lernziele zu Beginn definieren',
        'Interaktivität in den ersten Blöcken erhöhen'
    ],
    'recommendations': []
}

test_metadata = {
    'topic': 'Karriere-Insights & Best Practices',
    'host_email': 'admin@talentspring-academy.com',
    'duration': '71',
    'meeting_id': '8QKMBVFhTXmKzIYpPBzGLw==',
    'score': 3.8
}

def test_pdf_generation():
    """Generate a test PDF with sample data"""
    print("Generating test PDF...")
    
    # Create PDF generator
    generator = PDFReportGenerator()
    
    # Generate PDF
    pdf_bytes = generator.generate_report_pdf(test_report, test_metadata)
    
    # Save to file
    output_path = "test_report.pdf"
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    
    print(f"✅ PDF saved to: {output_path}")
    print(f"   Size: {len(pdf_bytes):,} bytes")
    print(f"   Open with: open {output_path}")
    
    return output_path

if __name__ == "__main__":
    test_pdf_generation()