"""
PDF Generator - Generare PDF pentru variante cu LaTeX rendering
"""
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from psycopg import Connection
from psycopg.rows import dict_row


class VariantPDFGenerator:
    """Generator de PDF-uri pentru variante"""

    def __init__(self, conn: Connection):
        self.conn = conn
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configurează stiluri custom pentru PDF"""
        # Titlu principal
        self.styles.add(ParagraphStyle(
            name='VariantTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Subtitlu (info examen)
        self.styles.add(ParagraphStyle(
            name='ExamInfo',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))

        # Titlu subiect
        self.styles.add(ParagraphStyle(
            name='SubjectTitle',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#3498db'),
            spaceAfter=12,
            spaceBefore=18,
            fontName='Helvetica-Bold'
        ))

        # Enunț exercițiu
        self.styles.add(ParagraphStyle(
            name='Exercise',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=10,
            leading=16,
            fontName='Helvetica',
            alignment=TA_JUSTIFY
        ))

        # Punctaj
        self.styles.add(ParagraphStyle(
            name='Points',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#27ae60'),
            fontName='Helvetica-Bold'
        ))

    def generate_variant_pdf(self, variant_id: uuid.UUID) -> BytesIO:
        """
        Generează PDF pentru o variantă

        Args:
            variant_id: ID-ul variantei

        Returns:
            BytesIO cu conținutul PDF-ului
        """
        # 1. Obține datele variantei
        variant_data = self._get_variant_data(variant_id)
        exercises = self._get_variant_exercises(variant_id)

        # 2. Grupează exercițiile pe secțiuni
        exercises_by_section = self._group_exercises_by_section(exercises)

        # 3. Creează PDF-ul
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=variant_data['name']
        )

        # 4. Construiește conținutul
        story = []

        # Header
        story.extend(self._build_header(variant_data))

        # Exerciții pe secțiuni
        for section_name in sorted(exercises_by_section.keys()):
            section_exercises = exercises_by_section[section_name]
            story.extend(self._build_section(section_name, section_exercises))

        # Footer
        story.extend(self._build_footer(variant_data))

        # 5. Generează PDF
        doc.build(story)
        buffer.seek(0)

        return buffer

    def _get_variant_data(self, variant_id: uuid.UUID) -> Dict[str, Any]:
        """Obține datele variantei"""
        query = """
        SELECT id, name, exam_type, profile, year, session,
               total_points, duration_minutes, status, created_at
        FROM variants
        WHERE id = %s;
        """

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (variant_id,))
            return cur.fetchone()

    def _get_variant_exercises(self, variant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Obține exercițiile variantei"""
        query = """
        SELECT
            ve.id, ve.order_index, ve.section_name,
            e.statement_latex, e.statement_text, e.points, e.item_type,
            e.subject_part, e.difficulty
        FROM variant_exercises ve
        JOIN exercises e ON ve.exercise_id = e.id
        WHERE ve.variant_id = %s
        ORDER BY ve.order_index;
        """

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (variant_id,))
            return cur.fetchall()

    def _group_exercises_by_section(self, exercises: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Grupează exercițiile pe secțiuni"""
        sections = {}
        for ex in exercises:
            section = ex.get('section_name') or 'Exerciții'
            if section not in sections:
                sections[section] = []
            sections[section].append(ex)
        return sections

    def _build_header(self, variant_data: Dict[str, Any]) -> List:
        """Construiește header-ul PDF-ului"""
        story = []

        # Titlu
        title = Paragraph(variant_data['name'], self.styles['VariantTitle'])
        story.append(title)

        # Info examen
        exam_info_parts = []
        if variant_data.get('exam_type'):
            exam_info_parts.append(variant_data['exam_type'].replace('_', ' ').title())
        if variant_data.get('profile'):
            exam_info_parts.append(f"Profil: {variant_data['profile']}")
        if variant_data.get('year'):
            exam_info_parts.append(f"Anul {variant_data['year']}")
        if variant_data.get('session'):
            exam_info_parts.append(variant_data['session'].title())

        if exam_info_parts:
            exam_info = Paragraph(' • '.join(exam_info_parts), self.styles['ExamInfo'])
            story.append(exam_info)

        # Info timp și punctaj
        meta_parts = []
        if variant_data.get('duration_minutes'):
            meta_parts.append(f"Timp de lucru: {variant_data['duration_minutes']} minute")
        if variant_data.get('total_points'):
            meta_parts.append(f"Punctaj total: {variant_data['total_points']} puncte")

        if meta_parts:
            meta_info = Paragraph(' | '.join(meta_parts), self.styles['ExamInfo'])
            story.append(meta_info)

        story.append(Spacer(1, 0.5*cm))

        # Linie separator
        story.append(self._create_separator_line())
        story.append(Spacer(1, 0.3*cm))

        return story

    def _build_section(self, section_name: str, exercises: List[Dict[str, Any]]) -> List:
        """Construiește o secțiune de exerciții"""
        story = []

        # Titlu secțiune
        section_title = Paragraph(f"<b>{section_name}</b>", self.styles['SubjectTitle'])
        story.append(section_title)
        story.append(Spacer(1, 0.3*cm))

        # Exerciții
        for i, exercise in enumerate(exercises, 1):
            # Număr exercițiu și punctaj
            exercise_header = f"<b>{i}.</b> "
            if exercise.get('points'):
                exercise_header += f"<font color='#27ae60'>({exercise['points']}p)</font> "

            # Enunț
            statement = exercise.get('statement_text') or exercise.get('statement_latex', '')

            # Clean up LaTeX pentru PDF simplu (pentru versiunea simplă)
            # În viitor se poate integra latex2pdf pentru rendering adevărat
            statement = self._clean_latex_for_pdf(statement)

            exercise_text = exercise_header + statement
            exercise_para = Paragraph(exercise_text, self.styles['Exercise'])
            story.append(exercise_para)

            # Spațiu pentru răspuns
            story.append(Spacer(1, 1*cm))

        story.append(Spacer(1, 0.5*cm))

        return story

    def _build_footer(self, variant_data: Dict[str, Any]) -> List:
        """Construiește footer-ul PDF-ului"""
        story = []

        story.append(Spacer(1, 1*cm))
        story.append(self._create_separator_line())
        story.append(Spacer(1, 0.3*cm))

        # Data generării
        footer_text = f"<i>Generat cu EduContent • {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
        footer = Paragraph(footer_text, self.styles['ExamInfo'])
        story.append(footer)

        return story

    def _create_separator_line(self):
        """Creează o linie separator"""
        return Table(
            [['']],
            colWidths=[17*cm],
            style=TableStyle([
                ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#bdc3c7')),
            ])
        )

    def _clean_latex_for_pdf(self, text: str) -> str:
        """
        Curăță LaTeX pentru afișare simplă în PDF
        În viitor se poate înlocui cu rendering LaTeX real
        """
        if not text:
            return ""

        # Înlocuiri simple pentru simboluri comune
        replacements = {
            '\\mathbb{R}': 'ℝ',
            '\\mathbb{N}': 'ℕ',
            '\\mathbb{Z}': 'ℤ',
            '\\mathbb{Q}': 'ℚ',
            '\\mathbb{C}': 'ℂ',
            '\\in': '∈',
            '\\subset': '⊂',
            '\\subseteq': '⊆',
            '\\forall': '∀',
            '\\exists': '∃',
            '\\to': '→',
            '\\rightarrow': '→',
            '\\leftarrow': '←',
            '\\Rightarrow': '⇒',
            '\\Leftarrow': '⇐',
            '\\Leftrightarrow': '⇔',
            '\\infty': '∞',
            '\\int': '∫',
            '\\sum': '∑',
            '\\prod': '∏',
            '\\sqrt': '√',
            '\\leq': '≤',
            '\\geq': '≥',
            '\\neq': '≠',
            '\\approx': '≈',
            '\\times': '×',
            '\\cdot': '·',
            '\\pm': '±',
            '\\alpha': 'α',
            '\\beta': 'β',
            '\\gamma': 'γ',
            '\\Delta': 'Δ',
            '\\pi': 'π',
            '\\theta': 'θ',
            '\\lambda': 'λ',
            '\\mu': 'μ',
            '\\sigma': 'σ',
            '\\omega': 'ω',
        }

        for latex, unicode_char in replacements.items():
            text = text.replace(latex, unicode_char)

        # Șterge comenzi LaTeX rămase
        import re
        text = re.sub(r'\$([^\$]+)\$', r'\1', text)  # Inline math
        text = re.sub(r'\\\w+\{([^}]+)\}', r'\1', text)  # Commands with args
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # Simple commands

        return text


def get_pdf_generator(conn: Connection) -> VariantPDFGenerator:
    """Factory function pentru VariantPDFGenerator"""
    return VariantPDFGenerator(conn)
