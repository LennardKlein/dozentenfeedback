"""
Improved PDF Report Generator with Markdown parsing
"""

from typing import Dict, Any, Optional, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, KeepTogether, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import io
import re


class ImprovedPDFReportGenerator:
    """Generate professional PDF reports with markdown support"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles with better formatting"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Section header style - clean and professional
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=25,
            spaceAfter=15,
            leftIndent=0,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=(0, 0, 8, 2),
            borderColor=colors.HexColor('#3498db')
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceBefore=18,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Body text style with better line spacing
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=16,  # Better line spacing
            textColor=colors.HexColor('#2c2c2c')
        ))
        
        # List item style
        self.styles.add(ParagraphStyle(
            name='ListItem',
            parent=self.styles['BodyText'],
            fontSize=11,
            leftIndent=15,
            spaceAfter=6,
            leading=14,
            textColor=colors.HexColor('#2c2c2c')
        ))
        
        # Score style
        self.styles.add(ParagraphStyle(
            name='Score',
            parent=self.styles['BodyText'],
            fontSize=12,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        ))
        
        # Summary style with background
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=16,
            textColor=colors.HexColor('#2c2c2c'),
            leftIndent=10,
            rightIndent=10,
            spaceBefore=10,
            borderWidth=1,
            borderColor=colors.HexColor('#e0e0e0'),
            borderPadding=10,
            backColor=colors.HexColor('#f8f9fa')
        ))
    
    def _parse_markdown_to_paragraphs(self, text: str, base_style: str = 'CustomBody') -> List:
        """Convert markdown text to ReportLab flowables"""
        flowables = []
        
        # Clean up the text first
        text = text.strip()
        
        # Split by double newlines for paragraphs
        paragraphs = re.split(r'\n\n+', text)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check for headers (# Header or ## Header)
            if para.startswith('#'):
                # Count the number of # symbols
                level = len(para) - len(para.lstrip('#'))
                header_text = para.lstrip('#').strip()
                
                if level == 1:
                    # H1 header - use SubsectionHeader style for prominent display
                    flowables.append(Paragraph(header_text, self.styles['SubsectionHeader']))
                    flowables.append(Spacer(1, 8))
                elif level == 2:
                    # H2 header - use CustomBody with bold
                    flowables.append(Paragraph(f'<b>{header_text}</b>', self.styles['CustomBody']))
                    flowables.append(Spacer(1, 6))
                else:
                    # H3+ headers
                    flowables.append(Paragraph(f'<b>{header_text}</b>', self.styles['CustomBody']))
                    flowables.append(Spacer(1, 4))
                continue
            
            # Check for bullet points
            if para.startswith('- ') or para.startswith('* '):
                # Handle multiple bullet points
                bullets = para.split('\n')
                for bullet in bullets:
                    if bullet.startswith('- ') or bullet.startswith('* '):
                        bullet_text = bullet[2:].strip()
                        # Process markdown within bullet
                        bullet_text = self._process_inline_markdown(bullet_text)
                        flowables.append(Paragraph(f"• {bullet_text}", self.styles['ListItem']))
            else:
                # Regular paragraph with markdown processing
                para_text = self._process_inline_markdown(para)
                flowables.append(Paragraph(para_text, self.styles[base_style]))
                flowables.append(Spacer(1, 6))
        
        return flowables
    
    def _process_inline_markdown(self, text: str) -> str:
        """Process inline markdown (bold, italic) to HTML for ReportLab"""
        # First escape existing HTML characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Then replace markdown with HTML tags
        # Replace **bold** with <b>bold</b>
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        
        # Replace *italic* with <i>italic</i> (but not if it's part of **)
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
        
        return text
    
    def generate_report_pdf(self, complete_report: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Generate a PDF report from the complete analysis with improved formatting
        """
        buffer = io.BytesIO()
        
        # Create document with better margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm,
            title="Dozentenfeedback Analyse",
            author="DozentenFeedback System"
        )
        
        story = []
        
        # Add header with logo space (you could add actual logo here)
        story.append(Spacer(1, 1*cm))
        
        # Title
        title = "Dozentenfeedback - Analyse Bericht"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        # Metadata section with better formatting
        if metadata:
            meta_data = [
                [Paragraph('<b>Thema:</b>', self.styles['CustomBody']), 
                 Paragraph(metadata.get('topic', 'N/A'), self.styles['CustomBody'])],
                [Paragraph('<b>Dozent:</b>', self.styles['CustomBody']), 
                 Paragraph(metadata.get('host_email', 'N/A'), self.styles['CustomBody'])],
                [Paragraph('<b>Dauer:</b>', self.styles['CustomBody']), 
                 Paragraph(f"{metadata.get('duration', 'N/A')} Minuten", self.styles['CustomBody'])],
                [Paragraph('<b>Datum:</b>', self.styles['CustomBody']), 
                 Paragraph(datetime.now().strftime('%d.%m.%Y'), self.styles['CustomBody'])],
                [Paragraph('<b>Meeting ID:</b>', self.styles['CustomBody']), 
                 Paragraph(metadata.get('meeting_id', 'N/A'), self.styles['CustomBody'])],
            ]
            meta_table = Table(meta_data, colWidths=[3.5*cm, 13*cm])
            meta_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(meta_table)
        
        story.append(Spacer(1, 0.8*cm))
        
        # Overall Score Section with visual improvement
        story.append(Paragraph("Gesamtbewertung", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.3*cm))
        
        overall_score = complete_report.get('overall_score', 0)
        score_color = self._get_score_color(overall_score)
        
        # Create score visualization with truly consistent text sizes
        label_style = ParagraphStyle('LabelStyle', parent=self.styles['CustomBody'], fontSize=11, textColor=colors.HexColor('#5a6c7d'))
        value_style = ParagraphStyle('ValueStyle', parent=self.styles['CustomBody'], fontSize=11, fontName='Helvetica-Bold')
        
        score_data = [
            [Paragraph('Gesamtpunktzahl:', label_style), 
             Paragraph(f'<font color="{score_color.hexval()}"><b>{overall_score:.1f} / 5.0</b></font>', value_style)],
            [Paragraph('Bewertung:', label_style), 
             Paragraph(f'<font color="{score_color.hexval()}"><b>{self._get_score_rating(overall_score)}</b></font>', value_style)],
            [Paragraph('Blöcke analysiert:', label_style), 
             Paragraph(f'<b>{complete_report.get("total_blocks", 0)}</b>', value_style)],
        ]
        
        score_table = Table(score_data, colWidths=[5*cm, 11.5*cm])
        score_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#3498db')),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(score_table)
        
        story.append(Spacer(1, 0.8*cm))
        
        # Criteria Scores with improved table
        story.append(Paragraph("Bewertung nach Kriterien", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.3*cm))
        
        criteria_scores = complete_report.get('criteria_scores', {})
        # Create header row with Paragraph objects - consistent sizing
        header_style = ParagraphStyle('HeaderStyle', parent=self.styles['Normal'], 
                                     textColor=colors.white, fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER)
        cell_style = ParagraphStyle('CellStyle', parent=self.styles['Normal'], fontSize=11, textColor=colors.HexColor('#2c3e50'))
        score_style = ParagraphStyle('ScoreCellStyle', parent=self.styles['Normal'], fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER)
        
        criteria_data = [[
            Paragraph('Kriterium', header_style), 
            Paragraph('Punkte', header_style), 
            Paragraph('Bewertung', header_style)
        ]]
        
        for criterion, score in criteria_scores.items():
            score_color = self._get_score_color(score)
            criteria_data.append([
                Paragraph(criterion, cell_style),
                Paragraph(f'<font color="{score_color.hexval()}"><b>{score:.1f}</b></font>', score_style),
                Paragraph(f'<font color="{score_color.hexval()}"><b>{self._get_score_rating(score)}</b></font>', score_style)
            ])
        
        criteria_table = Table(criteria_data, colWidths=[8*cm, 3*cm, 5.5*cm])
        criteria_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(criteria_table)
        
        # New page for detailed analysis
        story.append(PageBreak())
        
        # Executive Summary with markdown parsing
        story.append(Paragraph("Zusammenfassung", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.3*cm))
        summary = complete_report.get('summary', 'Keine Zusammenfassung verfügbar')
        
        # Parse markdown in summary
        summary_flowables = self._parse_markdown_to_paragraphs(summary, 'Summary')
        for flowable in summary_flowables:
            story.append(flowable)
        
        story.append(Spacer(1, 0.8*cm))
        
        # Key Strengths with better formatting
        strengths = complete_report.get('strengths', [])
        if strengths:
            story.append(Paragraph("Stärken", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.3*cm))
            for strength in strengths:
                # Clean and format strength text
                strength_text = self._process_inline_markdown(strength)
                story.append(Paragraph(f"• {strength_text}", self.styles['ListItem']))
            story.append(Spacer(1, 0.8*cm))
        
        # Areas for Improvement with better formatting
        improvements = complete_report.get('improvements', [])
        if improvements:
            story.append(Paragraph("Verbesserungspotenziale", self.styles['SectionHeader']))
            story.append(Spacer(1, 0.3*cm))
            for improvement in improvements:
                # Clean and format improvement text
                improvement_text = self._process_inline_markdown(improvement)
                story.append(Paragraph(f"• {improvement_text}", self.styles['ListItem']))
            story.append(Spacer(1, 0.8*cm))
        
        # Recommendations on new page if they exist
        recommendations = complete_report.get('recommendations', [])
        if recommendations:
            story.append(PageBreak())
            story.append(Paragraph("Empfehlungen", self.styles['SectionHeader']))
            for i, recommendation in enumerate(recommendations, 1):
                rec_text = self._process_inline_markdown(recommendation)
                story.append(Paragraph(f"<b>{i}.</b> {rec_text}", self.styles['CustomBody']))
                story.append(Spacer(1, 0.3*cm))
        
        # Footer with timestamp
        story.append(Spacer(1, 1*cm))
        footer_text = f"<font size='9' color='#7f8c8d'>Erstellt am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')} | DozentenFeedback Analysis System</font>"
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        # Return PDF as bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    
    def _add_page_number(self, canvas, doc):
        """Add page numbers to each page"""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#7f8c8d'))
        page_num = canvas.getPageNumber()
        text = f"Seite {page_num}"
        canvas.drawRightString(A4[0] - 2*cm, 2*cm, text)
        canvas.restoreState()
    
    def _get_score_color(self, score: float) -> colors.Color:
        """Get color based on score with gradient"""
        if score >= 4.5:
            return colors.HexColor('#00a86b')  # Jade green
        elif score >= 4.0:
            return colors.HexColor('#27ae60')  # Green
        elif score >= 3.5:
            return colors.HexColor('#f39c12')  # Orange
        elif score >= 3.0:
            return colors.HexColor('#e67e22')  # Dark orange
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


# For backward compatibility, keep the old class name as an alias
PDFReportGenerator = ImprovedPDFReportGenerator