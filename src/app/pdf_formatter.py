"""
PDF Report Generator for Recording Analysis
"""

from typing import Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import io
import os


class PDFReportGenerator:
    """Generate professional PDF reports from analysis results"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=20,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=20,
            spaceAfter=12,
            leftIndent=0
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=12,
            spaceAfter=8
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        ))
        
        # Score style
        self.styles.add(ParagraphStyle(
            name='Score',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        ))
    
    def generate_report_pdf(self, complete_report: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Generate a PDF report from the complete analysis
        
        Args:
            complete_report: The complete analysis report dictionary
            metadata: Optional metadata about the recording
            
        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        story = []
        
        # Title
        title = "Dozentenfeedback - Analyse Bericht"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        
        # Metadata section
        if metadata:
            story.append(Spacer(1, 12))
            meta_data = [
                ['Thema:', metadata.get('topic', 'N/A')],
                ['Dozent:', metadata.get('host_email', 'N/A')],
                ['Dauer:', metadata.get('duration', 'N/A')],
                ['Datum:', datetime.now().strftime('%d.%m.%Y')],
            ]
            meta_table = Table(meta_data, colWidths=[30*mm, 120*mm])
            meta_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(meta_table)
        
        story.append(Spacer(1, 20))
        
        # Overall Score Section
        story.append(Paragraph("Gesamtbewertung", self.styles['SectionHeader']))
        
        overall_score = complete_report.get('overall_score', 0)
        score_color = self._get_score_color(overall_score)
        
        score_data = [
            ['Gesamtpunktzahl:', f'{overall_score:.1f} / 5.0'],
            ['Bewertung:', self._get_score_rating(overall_score)],
            ['Blöcke analysiert:', str(complete_report.get('total_blocks', 0))],
        ]
        
        score_table = Table(score_data, colWidths=[40*mm, 110*mm])
        score_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1, 0), (1, 0), score_color),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, 0), 14),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(score_table)
        
        story.append(Spacer(1, 20))
        
        # Kriterien Scores
        story.append(Paragraph("Bewertung nach Kriterien", self.styles['SectionHeader']))
        
        criteria_scores = complete_report.get('criteria_scores', {})
        criteria_data = [['Kriterium', 'Punktzahl', 'Bewertung']]
        
        for criterion, score in criteria_scores.items():
            criteria_data.append([
                criterion,
                f'{score:.1f}',
                self._get_score_rating(score)
            ])
        
        criteria_table = Table(criteria_data, colWidths=[70*mm, 30*mm, 50*mm])
        criteria_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(criteria_table)
        
        story.append(PageBreak())
        
        # Executive Summary
        story.append(Paragraph("Zusammenfassung", self.styles['SectionHeader']))
        summary = complete_report.get('summary', 'Keine Zusammenfassung verfügbar')
        story.append(Paragraph(summary, self.styles['CustomBody']))
        
        story.append(Spacer(1, 20))
        
        # Key Strengths
        strengths = complete_report.get('strengths', [])
        if strengths:
            story.append(Paragraph("Stärken", self.styles['SubsectionHeader']))
            for strength in strengths:
                story.append(Paragraph(f"• {strength}", self.styles['CustomBody']))
        
        story.append(Spacer(1, 15))
        
        # Areas for Improvement
        improvements = complete_report.get('improvements', [])
        if improvements:
            story.append(Paragraph("Verbesserungspotenziale", self.styles['SubsectionHeader']))
            for improvement in improvements:
                story.append(Paragraph(f"• {improvement}", self.styles['CustomBody']))
        
        story.append(PageBreak())
        
        # Recommendations
        recommendations = complete_report.get('recommendations', [])
        if recommendations:
            story.append(Paragraph("Empfehlungen", self.styles['SectionHeader']))
            for i, recommendation in enumerate(recommendations, 1):
                story.append(Paragraph(f"{i}. {recommendation}", self.styles['CustomBody']))
        
        # Build PDF
        doc.build(story)
        
        # Return PDF as bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    
    def _get_score_color(self, score: float) -> colors.Color:
        """Get color based on score"""
        if score >= 4.0:
            return colors.HexColor('#27ae60')  # Green
        elif score >= 3.0:
            return colors.HexColor('#f39c12')  # Orange
        else:
            return colors.HexColor('#e74c3c')  # Red
    
    def _get_score_rating(self, score: float) -> str:
        """Get text rating based on score"""
        if score >= 4.5:
            return "Hervorragend"
        elif score >= 4.0:
            return "Sehr Gut"
        elif score >= 3.5:
            return "Gut"
        elif score >= 3.0:
            return "Befriedigend"
        elif score >= 2.5:
            return "Ausreichend"
        else:
            return "Verbesserungsbedürftig"
    
    def save_pdf(self, complete_report: Dict[str, Any], output_path: str, metadata: Optional[Dict[str, Any]] = None):
        """Save PDF report to file"""
        pdf_bytes = self.generate_report_pdf(complete_report, metadata)
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        return output_path