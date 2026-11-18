"""
Reports and Analytics Generation Module.
Computes KPIs, expiration horizons (30, 60, 90 days), category and department matrices,
and generates professional Excel (.xlsx) and PDF audit reports.
"""

import io
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

import config
from excel_database import excel_db
from device_manager import device_manager
from warranty_checker import parse_date

logger = logging.getLogger(__name__)


# Styling for Excel Export
THIN_BORDER = Border(
    left=Side(style='thin', color='E2E8F0'),
    right=Side(style='thin', color='E2E8F0'),
    top=Side(style='thin', color='E2E8F0'),
    bottom=Side(style='thin', color='E2E8F0')
)


class NumberedCanvas(canvas.Canvas):
    """Adds 'Page X of Y' footers and headers to multi-page ReportLab PDFs."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header rule and title
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 575, 752, 575)
        self.drawString(40, 580, f"{config.APP_NAME} — Executive Warranty & Asset Audit Report")
        self.drawRightString(752, 580, f"Generated: {datetime.now().strftime('%B %d, %Y')}")

        # Footer rule and page numbering
        self.line(40, 40, 752, 40)
        self.drawString(40, 28, "CONFIDENTIAL — FOR INTERNAL IT AUDITING AND ASSET MANAGEMENT ONLY")
        self.drawRightString(752, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class ReportService:
    def get_analytics_summary(self, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Calculates comprehensive executive KPIs and distribution matrices."""
        target_today = as_of_date or date.today()
        devices = device_manager.get_all_devices_enriched()
        total_devices = len(devices)

        active_count = 0
        expiring_soon_count = 0
        expired_count = 0

        expiring_30_days = 0
        expiring_60_days = 0
        expiring_90_days = 0
        expiring_this_month = 0

        current_month = target_today.month
        current_year = target_today.year

        category_counts = {cat: 0 for cat in config.DEVICE_CATEGORIES}
        department_counts = {dept: 0 for dept in config.DEPARTMENTS}

        category_status_matrix = {
            cat: {"Active": 0, "Expiring Soon": 0, "Expired": 0, "Total": 0}
            for cat in config.DEVICE_CATEGORIES
        }
        department_status_matrix = {
            dept: {"Active": 0, "Expiring Soon": 0, "Expired": 0, "Total": 0}
            for dept in config.DEPARTMENTS
        }

        total_asset_value = 0.0

        for d in devices:
            status = d.get("status", "Active")
            days_rem = d.get("days_remaining")
            cat = d.get("Category", "Other")
            dept = d.get("Department", "Other")
            price = d.get("Purchase_Price")

            if price and isinstance(price, (int, float)):
                total_asset_value += float(price)

            if cat not in category_counts:
                category_counts[cat] = 0
                category_status_matrix[cat] = {"Active": 0, "Expiring Soon": 0, "Expired": 0, "Total": 0}
            category_counts[cat] += 1
            category_status_matrix[cat]["Total"] += 1
            if status in category_status_matrix[cat]:
                category_status_matrix[cat][status] += 1

            if dept not in department_counts:
                department_counts[dept] = 0
                department_status_matrix[dept] = {"Active": 0, "Expiring Soon": 0, "Expired": 0, "Total": 0}
            department_counts[dept] += 1
            department_status_matrix[dept]["Total"] += 1
            if status in department_status_matrix[dept]:
                department_status_matrix[dept][status] += 1

            if status == "Active":
                active_count += 1
            elif status == "Expiring Soon":
                expiring_soon_count += 1
            elif status == "Expired":
                expired_count += 1

            end_date = parse_date(d.get("Warranty_End_Date"))
            if end_date:
                if end_date.year == current_year and end_date.month == current_month:
                    expiring_this_month += 1

                if days_rem is not None and days_rem >= 0:
                    if days_rem <= 30:
                        expiring_30_days += 1
                    if days_rem <= 60:
                        expiring_60_days += 1
                    if days_rem <= 90:
                        expiring_90_days += 1

        active_percentage = round((active_count / total_devices * 100), 1) if total_devices > 0 else 0.0

        # Sort upcoming expirations
        upcoming = [d for d in devices if d.get("status") in ("Expiring Soon", "Expired")]
        upcoming.sort(key=lambda x: x.get("days_remaining") if x.get("days_remaining") is not None else 9999)

        # Recent devices
        recent_devices = sorted(devices, key=lambda x: str(x.get("Created_At", "")), reverse=True)[:5]

        # Recent activity
        activity_logs = excel_db.get_activity_logs(limit=10)

        # Notifications unread count
        raw_notifs = excel_db.get_notifications()
        unread_notifs = sum(1 for n in raw_notifs if str(n.get("Status", "unread")).strip().lower() == "unread")

        return {
            "total_devices": total_devices,
            "active_warranties": active_count,
            "active_percentage": active_percentage,
            "expiring_soon": expiring_soon_count,
            "expired_warranties": expired_count,
            "expiring_this_month": expiring_this_month,
            "expiring_30_days": expiring_30_days,
            "expiring_60_days": expiring_60_days,
            "expiring_90_days": expiring_90_days,
            "unread_notifications": unread_notifs,
            "total_asset_value": round(total_asset_value, 2),
            "status_distribution": {
                "Active": active_count,
                "Expiring Soon": expiring_soon_count,
                "Expired": expired_count
            },
            "category_distribution": category_counts,
            "category_status_matrix": category_status_matrix,
            "department_status_matrix": department_status_matrix,
            "upcoming_expirations": upcoming[:8],
            "recent_devices": recent_devices,
            "activity_logs": activity_logs
        }

    def generate_excel_report(self, devices: List[Dict[str, Any]], output_path: Optional[str] = None) -> bytes:
        """
        Exports device records and warranty audit data to a professionally styled Excel file.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Warranty_Inventory"

        # Define styling
        title_font = Font(name="Calibri", size=16, bold=True, color="1E293B")
        meta_font = Font(name="Calibri", size=10, italic=True, color="64748B")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        status_fills = {
            "Active": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),       # Light green
            "Expiring Soon": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),# Light amber
            "Expired": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")       # Light red
        }
        status_fonts = {
            "Active": Font(name="Calibri", size=10, bold=True, color="166534"),
            "Expiring Soon": Font(name="Calibri", size=10, bold=True, color="92400E"),
            "Expired": Font(name="Calibri", size=10, bold=True, color="991B1B")
        }

        # Title rows
        ws.merge_cells("A1:M1")
        ws["A1"] = f"{config.APP_NAME} — Device Warranty Master Inventory"
        ws["A1"].font = title_font
        ws["A1"].alignment = Alignment(vertical="center")

        ws.merge_cells("A2:M2")
        ws["A2"] = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Devices: {len(devices)}"
        ws["A2"].font = meta_font

        headers = [
            "Device ID", "Device Name", "Category", "Brand", "Model", "Serial Number",
            "Assigned User", "Department", "Warranty Start", "Warranty End",
            "Days Remaining", "Warranty Status", "Purchase Price", "Supplier", "Invoice #"
        ]

        # Write Headers on Row 4
        ws.append([])
        ws.append(headers)
        header_row = 4
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER
        ws.row_dimensions[header_row].height = 26

        # Write Data
        for row_idx, d in enumerate(devices, start=5):
            status = d.get("status", "Active")
            price = d.get("Purchase_Price")
            row_data = [
                d.get("Device_ID", ""),
                d.get("Device_Name", ""),
                d.get("Category", ""),
                d.get("Brand", ""),
                d.get("Model_Number", ""),
                d.get("Serial_Number", ""),
                d.get("Assigned_User", ""),
                d.get("Department", ""),
                d.get("Warranty_Start_Date", ""),
                d.get("Warranty_End_Date", ""),
                d.get("days_remaining", 0),
                status,
                price if price is not None else 0.0,
                d.get("Supplier", ""),
                d.get("Invoice_Number", "")
            ]
            ws.append(row_data)

            # Row styling
            current_row = ws[row_idx]
            is_even = (row_idx % 2 == 0)
            for c_idx, cell in enumerate(current_row, start=1):
                cell.border = THIN_BORDER
                cell.alignment = Alignment(vertical="center")
                if is_even and c_idx != 12:
                    cell.fill = zebra_fill

                # Format price column as currency
                if c_idx == 13:
                    cell.number_format = '"$"#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")

            # Color status cell
            status_cell = ws.cell(row=row_idx, column=12)
            if status in status_fills:
                status_cell.fill = status_fills[status]
                status_cell.font = status_fonts[status]
                status_cell.alignment = Alignment(horizontal="center", vertical="center")

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len and cell.row > 2:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        data_bytes = buf.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(data_bytes)

        return data_bytes

    def generate_pdf_report(
        self,
        devices: List[Dict[str, Any]],
        summary_data: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Generates an executive PDF warranty audit report using ReportLab.
        Uses landscape letter orientation for optimal table presentation.
        """
        summary = summary_data or self.get_analytics_summary()
        buf = io.BytesIO()

        # Landscape letter: 792 x 612 pt. Margins 36 pt.
        doc = SimpleDocTemplate(
            buf,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=46
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F172A")
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=normal,
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B")
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1E293B")
        )
        table_cell = ParagraphStyle(
            "TableCell",
            parent=normal,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B")
        )
        table_header = ParagraphStyle(
            "TableHeader",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )
        kpi_number_style = ParagraphStyle(
            "KpiNumber",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=1,  # Center
            textColor=colors.HexColor("#2563EB")
        )
        kpi_label_style = ParagraphStyle(
            "KpiLabel",
            parent=normal,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor("#64748B")
        )

        elements = []

        # 1. Header Banner
        header_text = Paragraph(f"<b>{config.APP_NAME}</b>", title_style)
        sub_text = Paragraph(
            f"Comprehensive Device Warranty Audit & Asset Compliance Report • Generated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}",
            subtitle_style
        )
        elements.append(header_text)
        elements.append(Spacer(1, 4))
        elements.append(sub_text)
        elements.append(Spacer(1, 14))

        # 2. Executive KPI Cards Table
        kpi_data = [
            [
                Paragraph(str(summary["total_devices"]), kpi_number_style),
                Paragraph(f"{summary['active_warranties']} ({summary['active_percentage']}%)", kpi_number_style),
                Paragraph(str(summary["expiring_soon"]), ParagraphStyle("ExpiringNum", parent=kpi_number_style, textColor=colors.HexColor("#D97706"))),
                Paragraph(str(summary["expired_warranties"]), ParagraphStyle("ExpiredNum", parent=kpi_number_style, textColor=colors.HexColor("#DC2626"))),
                Paragraph(str(summary["expiring_this_month"]), kpi_number_style),
                Paragraph(str(summary["expiring_30_days"]), kpi_number_style)
            ],
            [
                Paragraph("TOTAL DEVICES", kpi_label_style),
                Paragraph("ACTIVE WARRANTIES", kpi_label_style),
                Paragraph("EXPIRING SOON (≤30d)", kpi_label_style),
                Paragraph("EXPIRED WARRANTIES", kpi_label_style),
                Paragraph("EXPIRING THIS MONTH", kpi_label_style),
                Paragraph("HORIZON (≤30 DAYS)", kpi_label_style)
            ]
        ]
        col_width = 720 / 6
        kpi_table = Table(kpi_data, colWidths=[col_width] * 6)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 18))

        # 3. Main Detailed Device Inventory Table
        elements.append(Paragraph("<b>Device Inventory & Warranty Expiration Schedule</b>", section_style))
        elements.append(Spacer(1, 8))

        table_headers = [
            Paragraph("Device ID", table_header),
            Paragraph("Device Name", table_header),
            Paragraph("Category", table_header),
            Paragraph("Serial Number", table_header),
            Paragraph("Assigned User", table_header),
            Paragraph("Department", table_header),
            Paragraph("Warranty End", table_header),
            Paragraph("Remaining", table_header),
            Paragraph("Status", table_header)
        ]

        table_rows = [table_headers]

        for d in devices:
            status = d.get("status", "Active")
            days_rem = d.get("days_remaining")
            rem_str = f"{days_rem}d" if days_rem is not None else "N/A"
            if days_rem is not None and days_rem < 0:
                rem_str = f"-{abs(days_rem)}d"

            # Color-coded badge for status cell
            if status == "Active":
                status_color = "#166534"
                status_bg = "#DCFCE7"
            elif status == "Expiring Soon":
                status_color = "#92400E"
                status_bg = "#FEF3C7"
            else:
                status_color = "#991B1B"
                status_bg = "#FEE2E2"

            status_p = Paragraph(
                f"<font color='{status_color}'><b>{status}</b></font>",
                ParagraphStyle("StatCell", parent=table_cell, alignment=1)
            )

            row = [
                Paragraph(f"<b>{d.get('Device_ID', '')}</b>", table_cell),
                Paragraph(str(d.get("Device_Name", ""))[:26], table_cell),
                Paragraph(str(d.get("Category", "")), table_cell),
                Paragraph(str(d.get("Serial_Number", ""))[:18], table_cell),
                Paragraph(str(d.get("Assigned_User", ""))[:20], table_cell),
                Paragraph(str(d.get("Department", "")), table_cell),
                Paragraph(str(d.get("Warranty_End_Date", ""))[:10], table_cell),
                Paragraph(rem_str, ParagraphStyle("RemCell", parent=table_cell, alignment=1)),
                status_p
            ]
            table_rows.append(row)

        # Widths sum to 720 pt
        col_widths = [55, 125, 65, 85, 100, 80, 75, 55, 80]
        inv_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        elements.append(inv_table)

        doc.build(elements, canvasmaker=NumberedCanvas)
        buf.seek(0)
        pdf_bytes = buf.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        return pdf_bytes


# Singleton instance
report_service = ReportService()
