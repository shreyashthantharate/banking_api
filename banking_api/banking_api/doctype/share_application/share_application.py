# Copyright (c) 2026, Talib Sheikh and contributors
# For license information, please see license.txt

from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl import Workbook
import frappe
import csv
import io
from frappe import _
from frappe.model.document import Document
import io
import frappe
from frappe import _
from frappe.utils import getdate, formatdate
from frappe.model.document import Document
from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


class ShareApplication(Document):
    def autoname(self):
        from frappe import _
        from frappe.model.naming import getseries

        sol_id = str(self.sol_id or "").strip()

        if not sol_id:
            frappe.throw(_("SOL ID is mandatory for naming."))

        if not sol_id.isdigit():
            frappe.throw(_("SOL ID must contain digits only."))

        if len(sol_id) != 4:
            frappe.throw(_("SOL ID must be exactly 4 digits."))

        prefix = f"{sol_id}01"

        for _ in range(5):
            sequence = getseries("Share Application-", 9)
            new_name = f"{prefix}{sequence}"

            if not frappe.db.exists("Share Application", new_name):
                self.name = new_name
                return

        frappe.throw(
            _("Unable to generate a unique Share Application ID. Please try again."))

    def validate(self):
        if self.docstatus == 1:
            if self.payment_status != "Success":
                frappe.throw(
                    _("Only documents with Status = 'Success' can be submitted."))

            if not self.transaction_id:
                frappe.throw(
                    _("Transaction ID is mandatory before submission."))

#########################################################################################


# @frappe.whitelist()
# def download_proceeding_form(account_opening_date):
#     if not account_opening_date:
#         frappe.throw(_("Account Opening Date is required."))

#     try:
#         selected_date = getdate(account_opening_date)
#     except Exception:
#         frappe.throw(_("Invalid date selected."))

#     records = frappe.get_all(
#         "Share Application",
#         filters={"account_opening_date": selected_date},
#         fields=["name", "customer_name"],
#         order_by="name asc"
#     )

#     if not records:
#         frappe.throw(
#             _("No Share Application records found for the selected Account Opening Date."))

#     doc = DocxDocument()

#     section = doc.sections[0]
#     section.top_margin = Inches(0.6)
#     section.bottom_margin = Inches(0.6)
#     section.left_margin = Inches(0.7)
#     section.right_margin = Inches(0.7)

#     # def add_center(text, bold=False, size=12):
#     #     p = doc.add_paragraph()
#     #     p.alignment = WD_ALIGN_PARAGRAPH.CENTER
#     #     r = p.add_run(text)
#     #     r.bold = bold
#     #     r.font.size = Pt(size)
#     #     return p

#     # def add_left(text, bold=False, size=12):
#     #     p = doc.add_paragraph()
#     #     p.alignment = WD_ALIGN_PARAGRAPH.LEFT
#     #     r = p.add_run(text)
#     #     r.bold = bold
#     #     r.font.size = Pt(size)
#     #     return p

#     def set_run_font(run, bold=False, size=14, font_name="Kokila"):
#         run.bold = bold
#         run.font.size = Pt(size)
#         run.font.name = font_name
#         r = run._element
#         r.rPr.rFonts.set(qn("w:ascii"), font_name)
#         r.rPr.rFonts.set(qn("w:hAnsi"), font_name)
#         r.rPr.rFonts.set(qn("w:cs"), font_name)
#         r.rPr.rFonts.set(qn("w:eastAsia"), font_name)

#     def add_center(text, bold=False, size=14):
#         p = doc.add_paragraph()
#         p.alignment = WD_ALIGN_PARAGRAPH.CENTER
#         run = p.add_run(text)
#         set_run_font(run, bold=bold, size=size)
#         return p

#     def add_left(text, bold=False, size=14):
#         p = doc.add_paragraph()
#         p.alignment = WD_ALIGN_PARAGRAPH.LEFT
#         run = p.add_run(text)
#         set_run_font(run, bold=bold, size=size)
#         return p

#     def add_left_mixed(parts, size=14):
#         p = doc.add_paragraph()
#         p.alignment = WD_ALIGN_PARAGRAPH.LEFT

#         for part in parts:
#             if isinstance(part, str):
#                 run = p.add_run(part)
#                 set_run_font(run, bold=False, size=size)
#             else:
#                 text, is_bold = part
#                 run = p.add_run(text)
#                 set_run_font(run, bold=is_bold, size=size)

#         return p

#     formatted_date = formatdate(selected_date, "dd / mm / yyyy")

#     add_center("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.",
#                bold=True, size=24)
#     add_center("")
#     add_left("सभासद उपसमिती बैठकीची कार्यवाही", bold=True, size=14)

#     add_left(f"बैठक क्र.: __________", bold=True, size=14)
#     add_left(f"दिनांक: {formatted_date}", bold=True, size=14)
#     add_left("वेळ: ___________", bold=True, size=14)
#     add_left("स्थळ: मुख्यालय, गोंदिया", bold=True, size=14)
#     add_left("विषय क्र. ____: नवीन सभासदत्व मंजूर करण्याबाबत", bold=True, size=14)

#     # add_left(
#     #     "मुख्य कार्यकारी अधिकारी यांनी सभेस अवगत केले की, संस्थेचे सभासदत्व प्राप्त करण्यासाठी विविध अर्जदारांकडून विहित नमुन्यात अर्ज प्राप्त झाले आहेत. सदर अर्जांची कार्यालयीन स्तरावर छाननी व पडताळणी करण्यात आली असून, अर्जदारांनी मल्टी स्टेट को-ऑपरेटिव्ह सोसायटीज अधिनियम, 2002, त्याअंतर्गत नियम व संस्थेच्या उपविधींनुसार आवश्यक पात्रता, प्रवेश फी, भागभांडवल रक्कम व इतर आवश्यक कागदपत्रांची पूर्तता केलेली आहे."
#     # )
#     add_left_mixed([
#         "मुख्य कार्यकारी अधिकारी यांनी सभेस अवगत केले की, संस्थेचे सभासदत्व प्राप्त करण्यासाठी विविध अर्जदारांकडून विहित नमुन्यात अर्ज प्राप्त झाले आहेत. सदर अर्जांची कार्यालयीन स्तरावर छाननी व पडताळणी करण्यात आली असून, अर्जदारांनी ",
#         ("मल्टी स्टेट को-ऑपरेटिव्ह सोसायटीज अधिनियम, 2002,", True),
#         " त्याअंतर्गत नियम व संस्थेच्या उपविधींनुसार आवश्यक पात्रता, प्रवेश फी, भागभांडवल रक्कम व इतर आवश्यक कागदपत्रांची पूर्तता केलेली आहे."
#     ], size=14)
#     # add_left(
#     #     'सदर अर्जदारांची तपशीलवार यादी "परिशिष्ट – अ" मध्ये जोडण्यात आलेली असून ती सभासद उपसमिती समोर विचारार्थ सादर करण्यात आली.'
#     # )

#     add_left_mixed([
#         ('सदर अर्जदारांची तपशीलवार यादी', False), ("परिशिष्ट – अ",
#                                                    True), ('मध्ये जोडण्यात आलेली असून ती सभासद उपसमिती समोर विचारार्थ सादर करण्यात आली.')
#     ])

#     add_left("")
#     add_left("ठराव क्र. ______", bold=True)
#     add_left(
#         'सभासद उपसमिती विषयावर सविस्तर चर्चा केली. परिशिष्ट – अ मधील सर्व अर्जदारांनी संस्थेच्या उपविधींनुसार सभासदत्वासाठी आवश्यक अटी पूर्ण केल्याचे निदर्शनास आले.'
#     )
#     add_left(
#         'त्याअनुषंगाने खालीलप्रमाणे ठराव एकमताने मंजूर करण्यात आला :', bold=True
#     )
#     add_left(
#         '"ठरविण्यात येते की, मल्टी स्टेट को-ऑपरेटिव्ह सोसायटीज अधिनियम, 2002, त्याअंतर्गत नियम व संस्थेच्या उपविधींमधील तरतुदींनुसार परिशिष्ट – अ मध्ये नमूद १ ते १०० अर्जदारांना संस्थेचे नियमित सभासद म्हणून प्रवेश देण्यास मंजुरी देण्यात येत आहे. तसेच संबंधित अर्जदारांकडून विहित प्रवेश फी, भागभांडवल रक्कम व इतर आवश्यक औपचारिकता पूर्ण करून त्यांची सभासद म्हणून नोंद सदस्य नोंदवहीत करण्यात यावी व नियमानुसार सभासदत्व/भाग प्रमाणपत्र निर्गमित करण्यात यावे. असे सर्व समंतीने ठरविण्यात आले."', bold=True
#     )

#     add_left("")
#     add_left("प्रस्तावक : _______________________", bold=True)
#     add_left("अनुमोदक : _______________________", bold=True)
#     add_left("ठराव सर्वानुमते मंजूर.", bold=True)
#     add_left("")
#     add_left("")
#     add_left(
#         "अध्यक्ष                                                      मुख्य कार्यकारी अधिकारी", bold=True)
#     add_left("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.     सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.", bold=True)
#     add_left(
#         "मुख्यालय, गोंदिया                                           मुख्यालय, गोंदिया", bold=True)

#     doc.add_page_break()

#     add_center("परिशिष्ट – अ", bold=True, size=14)
#     add_center(
#         "नवीन सभासदत्वासाठी मंजुरी देण्यात आलेल्या अर्जदारांची यादी", bold=True, size=14)
#     add_left("बैठक क्र.: __________", bold=True)
#     add_left(f"दिनांक: {formatted_date}", bold=True)
#     add_left("")

#     table = doc.add_table(rows=1, cols=6)
#     table.style = "Table Grid"

#     # hdr = table.rows[0].cells
#     # hdr[0].text = "अ.क्र."
#     # hdr[1].text = "अर्ज क्र."
#     # hdr[2].text = "अर्जदाराचे नाव"
#     # hdr[3].text = "गाव/शहर"
#     # hdr[4].text = "भागभांडवल रक्कम"
#     # hdr[5].text = "प्रवेश फी"
#     hdr = table.rows[0].cells
#     headers = [
#         "अ.क्र.",
#         "अर्ज क्र.",
#         "अर्जदाराचे नाव",
#         "गाव/शहर",
#         "भागभांडवल रक्कम",
#         "प्रवेश फी"
#     ]

#     for i, text in enumerate(headers):
#         paragraph = hdr[i].paragraphs[0]
#         run = paragraph.add_run(text)
#         set_run_font(run, bold=True, size=14)

#     # for idx, row in enumerate(records, start=1):
#     #     cells = table.add_row().cells
#     #     cells[0].text = str(idx)
#     #     cells[1].text = row.get("name") or ""
#     #     cells[2].text = row.get("customer_name") or ""
#     #     cells[3].text = ""
#     #     cells[4].text = ""
#     #     cells[5].text = ""

#     for idx, row in enumerate(records, start=1):
#         cells = table.add_row().cells
#         row_values = [
#             str(idx),
#             row.get("name") or "",
#             row.get("customer_name") or "",
#             "",
#             "",
#             ""
#         ]

#         for col_idx, value in enumerate(row_values):
#             paragraph = cells[col_idx].paragraphs[0]
#             run = paragraph.add_run(value)
#             set_run_font(run, bold=False, size=14)

#     add_left("")
#     add_left(
#         "प्रमाणित करण्यात येते की, परिशिष्ट – अ मध्ये नमूद १ ते १०० अर्जदारांची यादी संचालक मंडळाच्या बैठकी क्र. _____ दिनांक _____ मध्ये मंजूर करण्यात आलेल्या ठराव क्र. _____ चा अविभाज्य भाग आहे.", bold=True
#     )
#     add_left("")
#     add_left("मुख्य कार्यकारी अधिकारी", bold=True)
#     add_left("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.", bold=True)
#     add_left("मुख्यालय, गोंदिया", bold=True)
#     add_left("")
#     add_left("अध्यक्ष", bold=True)
#     add_left("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.", bold=True)
#     add_left("मुख्यालय, गोंदिया", bold=True)

#     file_buffer = io.BytesIO()
#     doc.save(file_buffer)
#     file_buffer.seek(0)

#     frappe.response.filename = f"Proceeding_Form_{selected_date}.docx"
#     frappe.response.filecontent = file_buffer.getvalue()
#     frappe.response.type = "download"
#     frappe.response.display_content_as = "attachment"


@frappe.whitelist()
def download_proceeding_form(account_opening_date):
    import io
    import frappe
    from frappe import _
    from frappe.utils import getdate, formatdate
    from docx import Document as DocxDocument
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml.ns import qn

    if not account_opening_date:
        frappe.throw(_("Account Opening Date is required."))

    try:
        selected_date = getdate(account_opening_date)
    except Exception:
        frappe.throw(_("Invalid date selected."))

    # records = frappe.get_all(
    #     "Share Application",
    #     filters={"account_opening_date": selected_date},
    #     fields=["name", "customer_name"],
    #     order_by="name asc"
    # )
    records = frappe.get_all(
        "Share Application",
        filters={
            "account_opening_date": selected_date,
            "payment_status": "Success"
        },
        fields=["name", "customer_name"],
        order_by="name asc"
    )

    # if not records:
    #     frappe.throw(
    #         _("No Share Application records found for the selected Account Opening Date.")
    #     )

    if not records:
        frappe.throw(
            _("No Share Application records with successful payment found for the selected Account Opening Date."))

    doc = DocxDocument()

    section = doc.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

    DEFAULT_FONT = "Kokila"
    DEFAULT_SIZE = 14

    def set_run_font(run, bold=False, size=DEFAULT_SIZE, font_name=DEFAULT_FONT):
        run.bold = bold
        run.font.size = Pt(size)
        run.font.name = font_name
        r = run._element
        if r.rPr is None:
            r.get_or_add_rPr()
        r.rPr.rFonts.set(qn("w:ascii"), font_name)
        r.rPr.rFonts.set(qn("w:hAnsi"), font_name)
        r.rPr.rFonts.set(qn("w:cs"), font_name)
        r.rPr.rFonts.set(qn("w:eastAsia"), font_name)

    def apply_paragraph_spacing(paragraph, alignment=WD_ALIGN_PARAGRAPH.LEFT):
        paragraph.alignment = alignment
        pf = paragraph.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        # change this only if you want tighter/looser line height
        pf.line_spacing = Pt(22)
        return paragraph

    def add_center(text, bold=False, size=DEFAULT_SIZE):
        p = doc.add_paragraph()
        apply_paragraph_spacing(p, WD_ALIGN_PARAGRAPH.CENTER)
        run = p.add_run(text)
        set_run_font(run, bold=bold, size=size)
        return p

    def add_left(text, bold=False, size=DEFAULT_SIZE):
        p = doc.add_paragraph()
        apply_paragraph_spacing(p, WD_ALIGN_PARAGRAPH.LEFT)
        run = p.add_run(text)
        set_run_font(run, bold=bold, size=size)
        return p

    def add_left_mixed(parts, size=DEFAULT_SIZE):
        p = doc.add_paragraph()
        apply_paragraph_spacing(p, WD_ALIGN_PARAGRAPH.LEFT)

        for part in parts:
            if isinstance(part, str):
                run = p.add_run(part)
                set_run_font(run, bold=False, size=size)
            else:
                text, is_bold = part
                run = p.add_run(text)
                set_run_font(run, bold=is_bold, size=size)

        return p

    def set_table_col_widths(table, widths):
        table.autofit = False
        try:
            table.allow_autofit = False
        except Exception:
            pass

        for col_idx, width in enumerate(widths):
            try:
                table.columns[col_idx].width = width
            except Exception:
                pass

        for row in table.rows:
            for col_idx, width in enumerate(widths):
                row.cells[col_idx].width = width

    def format_cell_paragraph(paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER):
        apply_paragraph_spacing(paragraph, alignment)
        return paragraph

    formatted_date = formatdate(selected_date, "dd / mm / yyyy")

    add_center("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.",
               bold=True, size=24)
    add_center("")
    add_left("सभासद उपसमिती बैठकीची कार्यवाही", bold=True, size=14)

    add_left("बैठक क्र.: __________", bold=True, size=14)
    add_left(f"दिनांक: {formatted_date}", bold=True, size=14)
    add_left("वेळ: ___________", bold=True, size=14)
    add_left("स्थळ: मुख्यालय, गोंदिया", bold=True, size=14)
    add_left("विषय क्र. ____: नवीन सभासदत्व मंजूर करण्याबाबत", bold=True, size=14)

    add_left_mixed([
        "मुख्य कार्यकारी अधिकारी यांनी सभेस अवगत केले की, संस्थेचे सभासदत्व प्राप्त करण्यासाठी विविध अर्जदारांकडून विहित नमुन्यात अर्ज प्राप्त झाले आहेत. सदर अर्जांची कार्यालयीन स्तरावर छाननी व पडताळणी करण्यात आली असून, अर्जदारांनी ",
        ("मल्टी स्टेट को-ऑपरेटिव्ह सोसायटीज अधिनियम, 2002,", True),
        " त्याअंतर्गत नियम व संस्थेच्या उपविधींनुसार आवश्यक पात्रता, प्रवेश फी, भागभांडवल रक्कम व इतर आवश्यक कागदपत्रांची पूर्तता केलेली आहे."
    ], size=14)

    add_left_mixed([
        "सदर अर्जदारांची तपशीलवार यादी ",
        ("परिशिष्ट – अ", True),
        " मध्ये जोडण्यात आलेली असून ती सभासद उपसमिती समोर विचारार्थ सादर करण्यात आली."
    ], size=14)

    add_left("")
    add_left("ठराव क्र. ______", bold=True)

    p = doc.add_paragraph()
    apply_paragraph_spacing(p, WD_ALIGN_PARAGRAPH.LEFT)

    r1 = p.add_run(
        "सभासद उपसमिती विषयावर सविस्तर चर्चा केली. परिशिष्ट – अ मधील सर्व अर्जदारांनी संस्थेच्या उपविधींनुसार सभासदत्वासाठी आवश्यक अटी पूर्ण केल्याचे निदर्शनास आले.\n"
    )
    set_run_font(r1, bold=False, size=14)

    r2 = p.add_run(
        "त्याअनुषंगाने खालीलप्रमाणे ठराव एकमताने मंजूर करण्यात आला :\n"
    )
    set_run_font(r2, bold=False, size=14)

    r3 = p.add_run(
        '"ठरविण्यात येते की, मल्टी स्टेट को-ऑपरेटिव्ह सोसायटीज अधिनियम, 2002, त्याअंतर्गत नियम व संस्थेच्या उपविधींमधील तरतुदींनुसार परिशिष्ट – अ मध्ये नमूद १ ते १०० अर्जदारांना संस्थेचे नियमित सभासद म्हणून प्रवेश देण्यास मंजुरी देण्यात येत आहे. तसेच संबंधित अर्जदारांकडून विहित प्रवेश फी, भागभांडवल रक्कम व इतर आवश्यक औपचारिकता पूर्ण करून त्यांची सभासद म्हणून नोंद सदस्य नोंदवहीत करण्यात यावी व नियमानुसार सभासदत्व/भाग प्रमाणपत्र निर्गमित करण्यात यावे. असे सर्व समंतीने ठरविण्यात आले. "'
    )
    set_run_font(r3, bold=False, size=14)

    add_left("")
    add_left("प्रस्तावक : _______________________", bold=True)
    add_left("अनुमोदक : _______________________", bold=True)
    add_left("ठराव सर्वानुमते मंजूर.", bold=True)
    add_left("")
    add_left("")
    add_left("अध्यक्ष                                                      मुख्य कार्यकारी अधिकारी", bold=True)
    add_left("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.     सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.", bold=True)
    add_left(
        "मुख्यालय, गोंदिया                                           मुख्यालय, गोंदिया", bold=True)

    doc.add_page_break()

    add_center("परिशिष्ट – अ", bold=True, size=14)
    add_center(
        "नवीन सभासदत्वासाठी मंजुरी देण्यात आलेल्या अर्जदारांची यादी", bold=True, size=14)
    add_left("बैठक क्र.: __________", bold=True)
    add_left(f"दिनांक: {formatted_date}", bold=True)
    add_left("")

    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    table.autofit = False

    col_widths = [
        Inches(0.45),  # अ.क्र.
        Inches(1.55),  # अर्ज क्र.
        Inches(2.45),  # अर्जदाराचे नाव
        Inches(1.05),  # गाव/शहर
        Inches(0.80),  # भागभांडवल रक्कम
        Inches(0.75),  # प्रवेश फी
    ]

    hdr = table.rows[0].cells
    headers = [
        "अ.क्र.",
        "अर्ज क्र.",
        "अर्जदाराचे नाव",
        "गाव/शहर",
        "भागभांडवल रक्कम",
        "प्रवेश फी"
    ]

    for i, text in enumerate(headers):
        paragraph = hdr[i].paragraphs[0]
        format_cell_paragraph(paragraph, WD_ALIGN_PARAGRAPH.CENTER)
        run = paragraph.add_run(text)
        set_run_font(run, bold=True, size=14)

    set_table_col_widths(table, col_widths)

    for idx, row in enumerate(records, start=1):
        cells = table.add_row().cells
        row_values = [
            str(idx),
            row.get("name") or "",
            row.get("customer_name") or "",
            "",
            "10",
            "10"
        ]

        for col_idx, value in enumerate(row_values):
            paragraph = cells[col_idx].paragraphs[0]

            if col_idx in (0, 4, 5):
                format_cell_paragraph(paragraph, WD_ALIGN_PARAGRAPH.CENTER)
            else:
                format_cell_paragraph(paragraph, WD_ALIGN_PARAGRAPH.LEFT)

            run = paragraph.add_run(value)
            set_run_font(run, bold=False, size=14)

        set_table_col_widths(table, col_widths)

    add_left("")
    add_left(
        "प्रमाणित करण्यात येते की, परिशिष्ट – अ मध्ये नमूद १ ते १०० अर्जदारांची यादी संचालक मंडळाच्या बैठकी क्र. _____ दिनांक _____ मध्ये मंजूर करण्यात आलेल्या ठराव क्र. _____ चा अविभाज्य भाग आहे.",
        bold=True
    )
    add_left("")
    add_left("मुख्य कार्यकारी अधिकारी", bold=True)
    add_left("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.", bold=True)
    add_left("मुख्यालय, गोंदिया", bold=True)
    add_left("")
    add_left("अध्यक्ष", bold=True)
    add_left("सहयोग मल्टीस्टेट क्रेडिट को-ऑपरेटिव्ह सोसायटी लि.", bold=True)
    add_left("मुख्यालय, गोंदिया", bold=True)

    file_buffer = io.BytesIO()
    doc.save(file_buffer)
    file_buffer.seek(0)

    frappe.response.filename = f"Proceeding_Form_{selected_date}.docx"
    frappe.response.filecontent = file_buffer.getvalue()
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"
# ########################################################################################


@frappe.whitelist()
def download_share_application_report(report_type):
    report_type = (report_type or "").strip().lower()

    filters = {}
    filename = ""

    export_fields = [
        "name",
        # "docstatus",
        "sol_id",
        "cif",
        "account_number",
        "customer_name",
        "scheme_type",
        "scheme_code",
        "transaction_amount",
        "payment_status",
        "failed_reason",
        "transaction_id",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        # "retry_attempted",
        # "last_retry_attempted",
        # "owner",
        # "creation",
        "address",
        # "error_log",
    ]

    db_fields = [
        "name",
        # "docstatus",
        "sol_id",
        "cif",
        "account_number",
        "customer_name",
        "scheme_type",
        "scheme_code",
        "transaction_amount",
        "payment_status",
        "transaction_id",
        "fund_transfer_date",
        "cif_creation_date",
        "account_opening_date",
        # "retry_attempted",
        # "last_retry_attempted",
        # "owner",
        # "creation",
        "address",
        # "error_log",
        "insufficient_balance",
        "account_closed",
        "account_frozen",
        "account_not_found",
    ]

    if report_type == "success":
        filters = {"payment_status": "Success"}
        filename = "share_application_success_report.csv"

    elif report_type == "failed":
        filters = {"payment_status": "Failed"}
        filename = "share_application_failed_report.csv"

    elif report_type == "pending":
        filters = {"payment_status": "Pending"}
        filename = "share_application_pending_report.csv"

    elif report_type == "consolidated":
        filters = {}
        filename = "share_application_consolidated_report.csv"

    else:
        frappe.throw(_("Invalid report type."))

    label_map = {
        "name": "Share Application ID",
        # "docstatus": "Doc Status",
        "sol_id": "SOL ID",
        "cif": "CIF",
        "account_number": "Account Number",
        "customer_name": "Customer Name",
        "scheme_type": "Scheme Type",
        "scheme_code": "Scheme Code",
        "transaction_amount": "Transaction Amount",
        "payment_status": "Payment Status",
        "failed_reason": "Failed Reason",
        "transaction_id": "Transaction ID",
        "fund_transfer_date": "Fund Transfer Date",
        "cif_creation_date": "CIF Creation Date",
        "account_opening_date": "Account Opening Date",
        # "retry_attempted": "Retry Attempted",
        # "last_retry_attempted": "Last Retry Attempted",
        # "owner": "Owner",
        # "creation": "Created On",
        "address": "Address",
        # "error_log": "API Response",
    }

    docstatus_map = {
        0: "Draft",
        1: "Submitted",
        2: "Cancelled",
    }

    def get_failed_reason(row):
        if row.get("payment_status") != "Failed":
            return ""

        if row.get("insufficient_balance"):
            return "Insufficient Balance"
        if row.get("account_closed"):
            return "Account Closed"
        if row.get("account_frozen"):
            return "Account Frozen"
        if row.get("account_not_found"):
            return "Account Not Found"

        return "Network Issue"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([label_map.get(field, field) for field in export_fields])

    chunk_size = 10000
    start = 0

    while True:
        records = frappe.get_all(
            "Share Application",
            filters=filters,
            fields=db_fields,
            limit_start=start,
            limit_page_length=chunk_size,
            order_by="name asc"
        )

        if not records:
            break

        for row in records:
            row_data = []

            for field in export_fields:
                if field == "failed_reason":
                    value = get_failed_reason(row)
                elif field == "docstatus":
                    value = docstatus_map.get(row.get(field), row.get(field))
                else:
                    value = row.get(field, "")

                row_data.append(value)

            writer.writerow(row_data)

        start += chunk_size

    frappe.response.filename = filename
    frappe.response.filecontent = output.getvalue()
    frappe.response.type = "download"
    frappe.response.display_content_as = "attachment"


@frappe.whitelist()
def get_share_application_status_counts():
    data = frappe.db.sql("""
        SELECT payment_status, COUNT(*) AS count
        FROM `tabShare Application`
        GROUP BY payment_status
    """, as_dict=True)

    counts = {
        "Success": 0,
        "Pending": 0,
        "Failed": 0
    }

    for row in data:
        status = row.get("payment_status")
        if status in counts:
            counts[status] = row.get("count", 0)

    return counts
