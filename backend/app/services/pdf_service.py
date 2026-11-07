from datetime import datetime, timezone
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.enums import PdfType


class PDFService:
    @staticmethod
    def generate_pdf(
        pdf_type: PdfType,
        clinic_name: str,
        clinic_phone: str,
        doctor_name: str,
        doctor_specialization: str,
        patient_name: str,
        patient_identifier: str,
        patient_age: str,
        patient_gender: str,
        content_markdown: str,
        signature_hash: str,
        approved_at: datetime,
    ) -> bytes:
        """Generates a professional clinical PDF document using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )
        h2_style = ParagraphStyle(
            "DocH2",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=8,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        footer_style = ParagraphStyle(
            "DocFooter",
            parent=styles["Normal"],
            fontSize=7,
            leading=10,
            textColor=colors.HexColor("#94a3b8"),
        )

        story = []

        # Header: Clinic Name & Telemetry
        story.append(Paragraph(clinic_name, title_style))
        doc_header = f"Attending Doctor: <b>{doctor_name}</b> ({doctor_specialization}) | Tel: {clinic_phone}"
        story.append(Paragraph(doc_header, subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))

        # Patient Info Table
        is_patient_pdf = pdf_type == PdfType.PATIENT_SUMMARY_PDF
        doc_type_label = "PATIENT CARE SUMMARY & DISCHARGE INSTRUCTIONS" if is_patient_pdf else "OUTPATIENT CLINICAL CONSULTATION NOTE (SOAP)"

        meta_data = [
            [
                Paragraph(f"<b>Patient:</b> {patient_name}", body_style),
                Paragraph(f"<b>UHID / ID:</b> {patient_identifier}", body_style),
            ],
            [
                Paragraph(f"<b>Age / Sex:</b> {patient_age} / {patient_gender}", body_style),
                Paragraph(f"<b>Date:</b> {approved_at.strftime('%d-%b-%Y %I:%M %p')}", body_style),
            ],
        ]
        t = Table(meta_data, colWidths=[260, 260])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ])
        )
        story.append(t)
        story.append(Spacer(1, 10))

        # Title of Document
        story.append(Paragraph(f"<b>{doc_type_label}</b>", h2_style))
        story.append(Spacer(1, 6))

        import re

        def md_to_rl(txt: str) -> str:
            # Escape HTML special chars first
            cleaned = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convert **bold** to <b>bold</b>
            cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
            # Convert __bold__ to <b>bold</b>
            cleaned = re.sub(r"__(.+?)__", r"<b>\1</b>", cleaned)
            # Convert *italic* to <i>italic</i>
            cleaned = re.sub(r"\*(.+?)\*", r"<i>\1</i>", cleaned)
            return cleaned

        # Body: Process markdown lines into styled paragraphs
        for line in content_markdown.splitlines():
            line_str = line.strip()
            if not line_str:
                story.append(Spacer(1, 4))
            elif line_str.startswith("#"):
                clean_heading = md_to_rl(line_str.lstrip("#").strip())
                story.append(Paragraph(f"<b>{clean_heading}</b>", h2_style))
            elif line_str.startswith("- ") or line_str.startswith("* "):
                bullet_txt = md_to_rl(line_str[2:])
                story.append(Paragraph(f"• {bullet_txt}", body_style))
            else:
                formatted_txt = md_to_rl(line_str)
                story.append(Paragraph(formatted_txt, body_style))

        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=6))

        # Doctor Sign-Off & Cryptographic Verification Box
        sig_data = [
            [
                Paragraph(
                    f"<b>Signed & Approved by:</b> {doctor_name}<br/>"
                    f"<b>Timestamp:</b> {approved_at.strftime('%Y-%m-%dT%H:%M:%SZ')}<br/>"
                    f"<b>SHA-256 Signature Hash:</b> <code>{signature_hash[:32]}...</code>",
                    body_style,
                )
            ]
        ]
        sig_table = Table(sig_data, colWidths=[520])
        sig_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ])
        )
        story.append(sig_table)
        story.append(Spacer(1, 8))

        # Disclaimer
        disclaimer = (
            "CONFIDENTIAL MEDICAL RECORD. Generated and digitally approved under ArogyaScribe B2B Clinical Platform. "
            "If symptoms worsen or emergency signs appear, report immediately to the nearest hospital emergency department."
        )
        story.append(Paragraph(disclaimer, footer_style))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
