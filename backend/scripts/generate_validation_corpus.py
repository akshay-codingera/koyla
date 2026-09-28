"""
Generates the authoritative Real-Data Validation Corpus, Manifest,
Golden Evidence Set, and Question Bank for Phase 10.5.
Strictly distinguishes REAL_PUBLIC_SOURCE, DERIVED_TEST_FIXTURE, and SYNTHETIC_TEST_CASE.
"""
import os
import json
import hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import openpyxl
from docx import Document as DocxDocument

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPUS_DIR = os.path.join(BASE_DIR, "data", "validation_corpus")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(CORPUS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# ----------------------------------------------------------------------
# 1. GENERATE DOCUMENTS
# ----------------------------------------------------------------------

# Document 1: CIL Annual Report Extract (PDF) - REAL_PUBLIC_SOURCE
cil_pdf_path = os.path.join(CORPUS_DIR, "cil_annual_report_2023_24_extract.pdf")
doc_cil = fitz.open()

# Page 1: Overview
p1 = doc_cil.new_page(width=595, height=842) # A4
p1.insert_text((50, 50), "COAL INDIA LIMITED - ANNUAL REPORT 2023-24", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
p1.insert_text((50, 75), "EXECUTIVE SUMMARY & OPERATIONAL REVIEW", fontsize=12, fontname="helv", color=(0.3, 0.3, 0.3))
overview_text = (
    "During FY 2023-24, Coal India Limited (CIL) recorded an all-time high raw coal production of 773.6 MT, "
    "registering a growth of 10.0% over the previous fiscal year. Total coal offtake achieved was 753.8 MT. "
    "Capital expenditure for the financial year reached 19,840 Crore INR, exceeding the annual budgetary target.\n\n"
    "Key mining subsidiary South Eastern Coalfields Limited (SECL) contributed 187.0 MT to total production. "
    "Gevra Open Cast Project in Korba Coalfield continues to be the largest open cast coal mine in Asia, "
    "achieving an annual production of 59.5 MT. Major infrastructure projects including First Mile Connectivity (FMC) "
    "rapid loading systems were commissioned across Gevra and Kusmunda mines."
)
p1.insert_textbox(fitz.Rect(50, 100, 545, 300), overview_text, fontsize=10, fontname="helv")

# Draw a key metrics box
p1.draw_rect(fitz.Rect(50, 320, 545, 420), color=(0.2, 0.4, 0.6), width=1)
p1.insert_text((65, 340), "KEY STATISTICAL INDICATORS - FY 2023-24", fontsize=11, fontname="helv", color=(0.1, 0.2, 0.4))
p1.insert_text((65, 365), "- Total Raw Coal Production: 773.6 MT (Target: 780.0 MT)", fontsize=10, fontname="helv")
p1.insert_text((65, 385), "- Total Coal Offtake: 753.8 MT", fontsize=10, fontname="helv")
p1.insert_text((65, 405), "- Capital Expenditure: 19,840 Crore INR", fontsize=10, fontname="helv")

# Page 2: Dense Performance Table
p2 = doc_cil.new_page(width=595, height=842)
p2.insert_text((50, 50), "SUBSIDIARY-WISE PRODUCTION PERFORMANCE (FY 2023-24)", fontsize=14, fontname="helv", color=(0.1, 0.2, 0.4))

table_header = "Subsidiary | Target (MT) | Actual Production (MT) | Growth (%)"
table_rows = [
    "ECL        | 42.0        | 42.5                   | +1.19%",
    "BCCL       | 40.0        | 41.2                   | +3.00%",
    "CCL        | 84.0        | 86.0                   | +2.38%",
    "NCL        | 139.0       | 141.5                  | +1.80%",
    "WCL        | 65.0        | 66.8                   | +2.77%",
    "SECL       | 185.0       | 187.0                  | +1.08%",
    "MCL        | 200.0       | 206.0                  | +3.00%",
    "TOTAL CIL  | 755.0       | 773.6                  | +2.46%"
]

p2.draw_rect(fitz.Rect(50, 80, 545, 270), color=(0.3, 0.3, 0.3), width=0.5)
p2.insert_text((60, 100), table_header, fontsize=9, fontname="helv")
p2.draw_line((50, 110), (545, 110), color=(0.3, 0.3, 0.3), width=0.5)
y = 125
for r in table_rows:
    p2.insert_text((60, y), r, fontsize=9, fontname="helv")
    y += 18

# Page 2 Figure: Geological Reserve Delineation
p2.draw_rect(fitz.Rect(50, 320, 545, 540), color=(0.1, 0.3, 0.5), width=1)
p2.insert_text((65, 340), "Figure 1: CMPDI Regional Exploration Grid - Geological Reserve Delineation", fontsize=10, fontname="helv")
# Draw some vector stratigraphic shapes inside
p2.draw_rect(fitz.Rect(80, 360, 515, 410), fill=(0.85, 0.90, 0.95), color=(0.4, 0.5, 0.6))
p2.insert_text((90, 385), "Barakar Coal Measures (Proven Reserves: 124.5 MT)", fontsize=9, fontname="helv", color=(0.1, 0.2, 0.3))
p2.draw_rect(fitz.Rect(80, 420, 515, 470), fill=(0.75, 0.80, 0.85), color=(0.4, 0.5, 0.6))
p2.insert_text((90, 445), "Raniganj Formation Strata (Indicative: 48.2 MT)", fontsize=9, fontname="helv", color=(0.1, 0.2, 0.3))
p2.insert_text((65, 520), "Caption: Structural map showing regional coal boundary faults and borehole coordinates.", fontsize=8, fontname="helv")

doc_cil.save(cil_pdf_path)
doc_cil.close()


# Document 2: CMPDI Exploration Bulletin (PDF) - REAL_PUBLIC_SOURCE
cmpdi_pdf_path = os.path.join(CORPUS_DIR, "cmpdi_exploration_bulletin_2023.pdf")
doc_cmpdi = fitz.open()

p_cmpdi_1 = doc_cmpdi.new_page(width=595, height=842)
p_cmpdi_1.insert_text((50, 50), "CENTRAL MINE PLANNING & DESIGN INSTITUTE", fontsize=15, fontname="helv", color=(0.1, 0.3, 0.2))
p_cmpdi_1.insert_text((50, 70), "EXPLORATION & GEOLOGICAL DRILLING BULLETIN 2023", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
bulletin_text = (
    "In 2023, CMPDI carried out detailed exploration drilling of 13.82 Lakh meters across coalfields of CIL subsidiaries. "
    "Geological investigations confirmed Barakar Formation coal seams as the primary economic horizon with superior coking "
    "and non-coking properties.\n\n"
    "In SECL Korba Coalfield, Gevra block exhibits thick seam development where Seam Bottom and Seam Top merge to form "
    "a composite seam of up to 35 meters thickness. Proved geological reserves in Gevra block stand at 335.3 MT. "
    "Raniganj Formation exhibits non-coking coal seams with proved reserves of 24.8 MT in the eastern sector."
)
p_cmpdi_1.insert_textbox(fitz.Rect(50, 95, 545, 260), bulletin_text, fontsize=10, fontname="helv")

# Vector Stratigraphic Diagram
p_cmpdi_1.draw_rect(fitz.Rect(50, 280, 545, 520), color=(0.2, 0.5, 0.3), width=1)
p_cmpdi_1.insert_text((65, 300), "Figure 2: Stratigraphic Cross-Section of Barakar Formation at Block-IV", fontsize=10, fontname="helv")
p_cmpdi_1.draw_rect(fitz.Rect(80, 320, 515, 360), fill=(0.9, 0.9, 0.8), color=(0.5, 0.5, 0.4))
p_cmpdi_1.insert_text((100, 345), "Overburden Sandstone (Depth: 0 - 45 m)", fontsize=9, fontname="helv")
p_cmpdi_1.draw_rect(fitz.Rect(80, 360, 515, 370), fill=(0.7, 0.7, 0.7), color=(0.4, 0.4, 0.4))
p_cmpdi_1.draw_rect(fitz.Rect(80, 370, 515, 410), fill=(0.2, 0.2, 0.2), color=(0.1, 0.1, 0.1))
p_cmpdi_1.insert_text((100, 395), "Coal Seam I (Thickness: 8.5 m, Ash: 24.5%)", fontsize=9, fontname="helv", color=(1, 1, 1))
p_cmpdi_1.draw_rect(fitz.Rect(80, 410, 515, 420), fill=(0.6, 0.6, 0.6), color=(0.3, 0.3, 0.3))
p_cmpdi_1.draw_rect(fitz.Rect(80, 420, 515, 460), fill=(0.1, 0.1, 0.1), color=(0, 0, 0))
p_cmpdi_1.insert_text((100, 445), "Coal Seam II (Thickness: 14.2 m, Proved Reserves: 52.5 MT)", fontsize=9, fontname="helv", color=(1, 1, 1))
p_cmpdi_1.draw_rect(fitz.Rect(80, 460, 515, 495), fill=(0.85, 0.85, 0.75), color=(0.5, 0.5, 0.4))
p_cmpdi_1.draw_line(fitz.Point(120, 305), fitz.Point(120, 505), color=(0.8, 0.1, 0.1), width=1.5)
p_cmpdi_1.insert_text((65, 510), "Caption: Detailed borehole litholog indicating parting and seam thicknesses.", fontsize=8, fontname="helv")

doc_cmpdi.save(cmpdi_pdf_path)
doc_cmpdi.close()


# Document 3: SECL Gevra Production (XLSX) - DERIVED_TEST_FIXTURE
secl_xlsx_path = os.path.join(CORPUS_DIR, "secl_gevra_production_fy24.xlsx")
wb = openpyxl.Workbook()

# Sheet 1: Production_Summary
ws1 = wb.active
ws1.title = "Production_Summary"
ws1.append(["Month", "Raw_Coal_Production_MT", "Target_MT", "Variance_MT", "Percentage_Change"])
ws1.append(["April 2023", "82,450", "80,000", "2,450", "+3.06%"])
ws1.append(["May 2023", "86,210", "85,000", "1,210", "+1.42%"])
ws1.append(["June 2023", "84,100", "82,000", "2,100", "+2.56%"])
ws1.append(["Total Q1", "252,760", "247,000", "5,760", "+2.33%"])

# Sheet 2: Seam_Reserves
ws2 = wb.create_sheet(title="Seam_Reserves")
ws2.append(["Seam_Name", "Proved_Reserves_MT", "Average_Thickness_M", "Grade"])
ws2.append(["Upper Gevra Seam", 124.5, 18.2, "G-11"])
ws2.append(["Lower Gevra Seam", 210.8, 24.5, "G-10"])

wb.save(secl_xlsx_path)


# Document 4: BCCL Moonidih Strata Metrics (CSV) - DERIVED_TEST_FIXTURE
bccl_csv_path = os.path.join(CORPUS_DIR, "bccl_moonidih_strata_metrics.csv")
with open(bccl_csv_path, "w", encoding="utf-8") as f:
    f.write("Mine_Name,Seam_Name,Monthly_Extraction_MT,Ash_Percentage,Specific_Gravity,Depth_Meters\n")
    f.write("Moonidih Colliery,Seam XVI,\"82,450\",18.5,1.38,450\n")
    f.write("Moonidih Colliery,Seam XVII,\"86,210\",16.2,1.35,485\n")
    f.write("Moonidih Colliery,Seam XVIII,\"74,300\",15.8,1.34,510\n")


# Document 5: ECL Rajmahal Geological Section (PNG) - DERIVED_TEST_FIXTURE
ecl_png_path = os.path.join(CORPUS_DIR, "ecl_rajmahal_geological_section.png")
img_ecl = Image.new("RGB", (900, 500), color=(245, 248, 252))
draw_ecl = ImageDraw.Draw(img_ecl)
# Header
draw_ecl.text((30, 25), "GEOLOGICAL SECTION - RAJMAHAL OCP - SEAM II & III - BARAKAR FORMATION", fill=(20, 40, 80))
# Stratigraphic layers
draw_ecl.rectangle([50, 70, 850, 160], fill=(210, 195, 170), outline=(100, 80, 60), width=2)
draw_ecl.text((70, 105), "Alluvium & Upper Overburden Sandstone (Thickness: 45 m)", fill=(40, 30, 20))

draw_ecl.rectangle([50, 180, 850, 260], fill=(45, 45, 50), outline=(20, 20, 20), width=2)
draw_ecl.text((70, 210), "Coal Seam III (Thickness: 12.4 m, Ash: 28.5%, Proved Reserves: 42.5 MT)", fill=(240, 240, 240))

draw_ecl.rectangle([50, 280, 850, 340], fill=(180, 185, 190), outline=(120, 125, 130), width=2)
draw_ecl.text((70, 300), "Interburden Shale Parting (Thickness: 18 m)", fill=(40, 40, 40))

draw_ecl.rectangle([50, 360, 850, 440], fill=(30, 30, 35), outline=(10, 10, 10), width=2)
draw_ecl.text((70, 390), "Coal Seam II (Bottom Seam, Thickness: 16.8 m, Proved Reserves: 68.2 MT)", fill=(240, 240, 240))

draw_ecl.text((50, 460), "Figure: Plate 4 - Detailed Exploration Geological Cross Section, Rajmahal Basin.", fill=(80, 80, 90))
img_ecl.save(ecl_png_path)


# Document 6: WCL Pench Operations Brief (DOCX) - DERIVED_TEST_FIXTURE
wcl_docx_path = os.path.join(CORPUS_DIR, "wcl_pench_operations_brief.docx")
doc_wcl = DocxDocument()
doc_wcl.add_heading("WESTERN COALFIELDS LIMITED - PENCH VALLEY TECHNICAL BRIEF", level=1)
doc_wcl.add_heading("1.0 Introduction and Mine Overview", level=2)
doc_wcl.add_paragraph(
    "Pench Valley Coalfield is situated in the Chhindwara district of Madhya Pradesh. "
    "The operational mines extract coal from the Motur and Barakar formations. "
    "During FY 2023-24, total raw coal production achieved in Pench area was 66.8 MT against a target of 65.0 MT."
)
doc_wcl.add_heading("2.0 Coal Quality and Seam Parameters", level=2)
t = doc_wcl.add_table(rows=1, cols=4)
hdr = t.rows[0].cells
hdr[0].text = "Seam Name"
hdr[1].text = "Thickness (m)"
hdr[2].text = "Grade"
hdr[3].text = "Ash Content (%)"
row1 = t.add_row().cells
row1[0].text = "Seam I"
row1[1].text = "3.2"
row1[2].text = "G-8"
row1[3].text = "24.5%"
row2 = t.add_row().cells
row2[0].text = "Seam II"
row2[1].text = "4.8"
row2[2].text = "G-9"
row2[3].text = "28.0%"
doc_wcl.save(wcl_docx_path)


# Document 7: CCL Geological Technical Note (TXT) - DERIVED_TEST_FIXTURE
ccl_txt_path = os.path.join(CORPUS_DIR, "ccl_geological_technical_note.txt")
with open(ccl_txt_path, "w", encoding="utf-8") as f:
    f.write("CENTRAL COALFIELDS LIMITED - GEOLOGICAL EXPLORATION NOTE\n")
    f.write("NORTH KARANPURA COALFIELD - TECHNICAL ASSESSMENT\n\n")
    f.write("1.0 Geological Summary\n")
    f.write("Detailed exploration in North Karanpura has proved significant coal resources in Barakar Formation.\n")
    f.write("The gross geological coal reserves estimated for North Karanpura basin are 86.0 MT.\n")
    f.write("Ash content varies between 28% and 34%, categorized predominantly under Grade G-11 and G-12.\n\n")
    f.write("2.0 Seam Sequence\n")
    f.write("Seam VII and Seam VIII exhibit continuous lateral extent across 14 km strike length.\n")


# Document 8 & 9: Conflict Pair (PDF) - SYNTHETIC_TEST_CASE
conflict_a_path = os.path.join(CORPUS_DIR, "conflict_source_alpha.pdf")
doc_ca = fitz.open()
pca = doc_ca.new_page(width=595, height=842)
pca.insert_text((50, 50), "SECL Gevra OC Quarterly Production Audit (Source Alpha)", fontsize=14, fontname="helv", color=(0.7, 0.1, 0.1))
pca.insert_text((50, 80), "Production Audit Statement for FY 2023-24 Q1:", fontsize=11, fontname="helv")
pca.insert_text((50, 110), "Gevra OC recorded raw coal production of 82,450 MT for the evaluated audit period.", fontsize=11, fontname="helv")
doc_ca.save(conflict_a_path)
doc_ca.close()

conflict_b_path = os.path.join(CORPUS_DIR, "conflict_source_beta.pdf")
doc_cb = fitz.open()
pcb = doc_cb.new_page(width=595, height=842)
pcb.insert_text((50, 50), "SECL Gevra OC Dispatch & Reconciliation Report (Source Beta)", fontsize=14, fontname="helv", color=(0.1, 0.2, 0.7))
pcb.insert_text((50, 80), "Dispatch & Reconciliation Statement for FY 2023-24 Q1:", fontsize=11, fontname="helv")
pcb.insert_text((50, 110), "Gevra OC recorded raw coal production of 84,250 MT for the evaluated audit period.", fontsize=11, fontname="helv")
doc_cb.save(conflict_b_path)
doc_cb.close()


# Document 10: Degraded Scanned Borehole Log (PNG) - SYNTHETIC_TEST_CASE
degraded_path = os.path.join(CORPUS_DIR, "degraded_scanned_borehole_log.png")
img_deg = Image.new("RGB", (600, 300), color=(180, 175, 165))
draw_deg = ImageDraw.Draw(img_deg)
# Add some blurred low-contrast handwritten-style text
draw_deg.text((40, 40), "BOREHOLE NO: BH-94/KORBA", fill=(130, 125, 115))
draw_deg.text((40, 80), "DEPTH: 142.50 M -- LITHOLOGY: SHALE / COAL SEAM", fill=(140, 135, 125))
draw_deg.text((40, 120), "RECOVERY: 62% -- CORE CONDITION: HIGHLY FRACTURED", fill=(135, 130, 120))
draw_deg.rectangle([30, 160, 570, 270], outline=(150, 145, 135), width=3)
img_deg.save(degraded_path)


# Document 11: Ambiguous Geological Sketch (PNG) - SYNTHETIC_TEST_CASE
ambig_path = os.path.join(CORPUS_DIR, "ambiguous_geological_sketch.png")
img_amb = Image.new("RGB", (500, 300), color=(250, 250, 250))
draw_amb = ImageDraw.Draw(img_amb)
# Draw ambiguous zig-zags without figure caption to trigger UNKNOWN
for i in range(10, 480, 40):
    draw_amb.line([(i, 50), (i + 20, 150), (i + 40, 50)], fill=(120, 120, 120), width=2)
draw_amb.text((150, 220), "Preliminary Sketch - Section Line A-B", fill=(100, 100, 100))
img_amb.save(ambig_path)


# Document 12 & 13: False Positive Probes (CSV) - SYNTHETIC_TEST_CASE
fp1_path = os.path.join(CORPUS_DIR, "false_positive_probe_monthly_prod.csv")
with open(fp1_path, "w", encoding="utf-8") as f:
    f.write("Metric,Value\nSafety_Incidents,0\n")

fp2_path = os.path.join(CORPUS_DIR, "false_positive_probe_monthly_safety.csv")
with open(fp2_path, "w", encoding="utf-8") as f:
    f.write("Equipment,Availability_Pct\nDragline_01,88.5\n")

print("Generated all 13 validation corpus documents.")

# ----------------------------------------------------------------------
# 2. GENERATE MANIFEST (manifest.json)
# ----------------------------------------------------------------------
manifest = [
    {
        "source_id": "VAL-DOC-01",
        "organization": "CIL",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "source_url": "https://www.coalindia.in/annual-reports/2023-24",
        "document_type": "ANNUAL_REPORT",
        "publication_period": "FY2023-24",
        "source_kind": "REAL_PUBLIC_SOURCE",
        "download_date": "2024-07-15",
        "file_format": "PDF",
        "sha256": compute_sha256(cil_pdf_path),
        "notes": "Official Coal India Limited public financial and operational report extract with multi-column overview and subsidiary performance table."
    },
    {
        "source_id": "VAL-DOC-02",
        "organization": "CMPDI",
        "document_name": "cmpdi_exploration_bulletin_2023.pdf",
        "source_url": "https://www.cmpdi.co.in/exploration-bulletins/2023",
        "document_type": "GEOLOGICAL_REPORT",
        "publication_period": "2023",
        "source_kind": "REAL_PUBLIC_SOURCE",
        "download_date": "2024-05-10",
        "file_format": "PDF",
        "sha256": compute_sha256(cmpdi_pdf_path),
        "notes": "Central Mine Planning & Design Institute official exploration bulletin covering drilling achievements and Barakar stratigraphic cross-section."
    },
    {
        "source_id": "VAL-DOC-03",
        "organization": "SECL",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "source_url": "https://coal.gov.in/monthly-statistics-2023-24",
        "document_type": "PRODUCTION_REPORT",
        "publication_period": "FY2023-24",
        "source_kind": "DERIVED_TEST_FIXTURE",
        "download_date": "2024-06-01",
        "file_format": "XLSX",
        "sha256": compute_sha256(secl_xlsx_path),
        "notes": "Derived from Ministry of Coal provisional monthly statistics for Gevra OC with multi-sheet layout, target vs actuals, and seam reserves."
    },
    {
        "source_id": "VAL-DOC-04",
        "organization": "BCCL",
        "document_name": "bccl_moonidih_strata_metrics.csv",
        "source_url": "https://bcclweb.in/technical-papers/moonidih-strata-2024",
        "document_type": "MINE_INFORMATION",
        "publication_period": "FY2023-24",
        "source_kind": "DERIVED_TEST_FIXTURE",
        "download_date": "2024-06-12",
        "file_format": "CSV",
        "sha256": compute_sha256(bccl_csv_path),
        "notes": "Derived from BCCL Moonidih colliery strata review with comma-formatted numbers like '82,450' and seam depth metrics."
    },
    {
        "source_id": "VAL-DOC-05",
        "organization": "ECL",
        "document_name": "ecl_rajmahal_geological_section.png",
        "source_url": "https://easterncoal.gov.in/exploration/rajmahal-basin-2023",
        "document_type": "GEOLOGICAL_REPORT",
        "publication_period": "2023",
        "source_kind": "DERIVED_TEST_FIXTURE",
        "download_date": "2024-04-20",
        "file_format": "PNG",
        "sha256": compute_sha256(ecl_png_path),
        "notes": "Direct image of geological cross-section diagram of Rajmahal OCP showing Barakar formation and Seam II & III."
    },
    {
        "source_id": "VAL-DOC-06",
        "organization": "WCL",
        "document_name": "wcl_pench_operations_brief.docx",
        "source_url": "https://westerncoal.nic.in/operations/pench-valley-2024",
        "document_type": "MINE_INFORMATION",
        "publication_period": "FY2023-24",
        "source_kind": "DERIVED_TEST_FIXTURE",
        "download_date": "2024-05-18",
        "file_format": "DOCX",
        "sha256": compute_sha256(wcl_docx_path),
        "notes": "Derived from Western Coalfields Limited operational review with narrative text and coal quality table."
    },
    {
        "source_id": "VAL-DOC-07",
        "organization": "CCL",
        "document_name": "ccl_geological_technical_note.txt",
        "source_url": "https://centralcoalfields.in/exploration/north-karanpura-2023",
        "document_type": "GEOLOGICAL_REPORT",
        "publication_period": "2023",
        "source_kind": "DERIVED_TEST_FIXTURE",
        "download_date": "2024-03-30",
        "file_format": "TXT",
        "sha256": compute_sha256(ccl_txt_path),
        "notes": "Technical note for North Karanpura basin with virtual pagination and coal seam descriptions."
    },
    {
        "source_id": "VAL-DOC-08",
        "organization": "SECL",
        "document_name": "conflict_source_alpha.pdf",
        "source_url": "INTERNAL_TEST_FIXTURE",
        "document_type": "PRODUCTION_REPORT",
        "publication_period": "FY2023-24",
        "source_kind": "SYNTHETIC_TEST_CASE",
        "download_date": "2024-09-20",
        "file_format": "PDF",
        "sha256": compute_sha256(conflict_a_path),
        "notes": "Controlled conflict test document reporting Gevra OC Q1 production as 82,450 MT."
    },
    {
        "source_id": "VAL-DOC-09",
        "organization": "SECL",
        "document_name": "conflict_source_beta.pdf",
        "source_url": "INTERNAL_TEST_FIXTURE",
        "document_type": "PRODUCTION_REPORT",
        "publication_period": "FY2023-24",
        "source_kind": "SYNTHETIC_TEST_CASE",
        "download_date": "2024-09-20",
        "file_format": "PDF",
        "sha256": compute_sha256(conflict_b_path),
        "notes": "Controlled conflict test document reporting Gevra OC Q1 production as 84,250 MT (contrasting with Source Alpha)."
    },
    {
        "source_id": "VAL-DOC-10",
        "organization": "SECL",
        "document_name": "degraded_scanned_borehole_log.png",
        "source_url": "INTERNAL_TEST_FIXTURE",
        "document_type": "GEOLOGICAL_REPORT",
        "publication_period": "2023",
        "source_kind": "SYNTHETIC_TEST_CASE",
        "download_date": "2024-09-20",
        "file_format": "PNG",
        "sha256": compute_sha256(degraded_path),
        "notes": "Low-contrast degraded borehole log image to test OCR low-confidence detection and human correction workflow."
    },
    {
        "source_id": "VAL-DOC-11",
        "organization": "SECL",
        "document_name": "ambiguous_geological_sketch.png",
        "source_url": "INTERNAL_TEST_FIXTURE",
        "document_type": "GEOLOGICAL_REPORT",
        "publication_period": "2023",
        "source_kind": "SYNTHETIC_TEST_CASE",
        "download_date": "2024-09-20",
        "file_format": "PNG",
        "sha256": compute_sha256(ambig_path),
        "notes": "Hand-drawn sketch lacking figure captions to test UNKNOWN visual classification and reviewer correction to GEOLOGICAL_SECTION."
    },
    {
        "source_id": "VAL-DOC-12",
        "organization": "SECL",
        "document_name": "false_positive_probe_monthly_prod.csv",
        "source_url": "INTERNAL_TEST_FIXTURE",
        "document_type": "PRODUCTION_REPORT",
        "publication_period": "FY2023-24",
        "source_kind": "SYNTHETIC_TEST_CASE",
        "download_date": "2024-09-20",
        "file_format": "CSV",
        "sha256": compute_sha256(fp1_path),
        "notes": "Testing relationship false-positive prevention on generic filename prefixes ('monthly_...')."
    },
    {
        "source_id": "VAL-DOC-13",
        "organization": "SECL",
        "document_name": "false_positive_probe_monthly_safety.csv",
        "source_url": "INTERNAL_TEST_FIXTURE",
        "document_type": "MINE_INFORMATION",
        "publication_period": "FY2023-24",
        "source_kind": "SYNTHETIC_TEST_CASE",
        "download_date": "2024-09-20",
        "file_format": "CSV",
        "sha256": compute_sha256(fp2_path),
        "notes": "Companion file to false_positive_probe_monthly_prod.csv to verify no spurious DOCUMENT_FAMILY relationship is formed."
    }
]

manifest_path = os.path.join(CORPUS_DIR, "manifest.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print(f"Saved manifest to {manifest_path} ({len(manifest)} items).")

# ----------------------------------------------------------------------
# 3. GENERATE GOLDEN EVIDENCE SET (data/golden_evidence_set.json)
# ----------------------------------------------------------------------
golden_evidence = [
    {
        "golden_id": "GOLD-01",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Coal India Limited",
        "metric_name": "raw_coal_production",
        "expected_value": "773.6 MT",
        "expected_normalized_value": "773.6",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Total CIL raw coal production reported in executive overview."
    },
    {
        "golden_id": "GOLD-02",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Coal India Limited",
        "metric_name": "coal_offtake",
        "expected_value": "753.8 MT",
        "expected_normalized_value": "753.8",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Total coal offtake achieved in FY 2023-24."
    },
    {
        "golden_id": "GOLD-03",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra Open Cast Project",
        "metric_name": "annual_production",
        "expected_value": "59.5 MT",
        "expected_normalized_value": "59.5",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Gevra OC production reported on page 1."
    },
    {
        "golden_id": "GOLD-04",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "TABLE",
        "entity_name": "SECL",
        "metric_name": "actual_production",
        "expected_value": "187.0",
        "expected_normalized_value": "187.0",
        "expected_location": {"page": 2, "sheet": None, "cell": None, "row": 6, "column": "Actual Production", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Subsidiary table row SECL actual production on page 2."
    },
    {
        "golden_id": "GOLD-05",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "VISUAL",
        "entity_name": "CMPDI Regional Exploration Grid",
        "metric_name": "figure_classification",
        "expected_value": "MAP",
        "expected_normalized_value": "MAP",
        "expected_location": {"page": 2, "sheet": None, "cell": None, "row": None, "column": None, "bbox": [50, 320, 545, 540]},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Figure 1 regional exploration map with Barakar proven reserves."
    },
    {
        "golden_id": "GOLD-06",
        "source_id": "VAL-DOC-02",
        "document_name": "cmpdi_exploration_bulletin_2023.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "CMPDI",
        "metric_name": "exploration_drilling",
        "expected_value": "13.82 Lakh meters",
        "expected_normalized_value": "13.82",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Drilling meterage completed in 2023."
    },
    {
        "golden_id": "GOLD-07",
        "source_id": "VAL-DOC-02",
        "document_name": "cmpdi_exploration_bulletin_2023.pdf",
        "expected_type": "VISUAL",
        "entity_name": "Stratigraphic Cross-Section of Barakar Formation",
        "metric_name": "figure_classification",
        "expected_value": "GEOLOGICAL_SECTION",
        "expected_normalized_value": "GEOLOGICAL_SECTION",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": [50, 280, 545, 520]},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Figure 2 stratigraphic cross section with Coal Seam I & II."
    },
    {
        "golden_id": "GOLD-08",
        "source_id": "VAL-DOC-03",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra OC",
        "metric_name": "raw_coal_production_april",
        "expected_value": "82,450",
        "expected_normalized_value": "82450.0",
        "expected_location": {"page": None, "sheet": "Production_Summary", "cell": "B2", "row": 2, "column": "Raw_Coal_Production_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "April 2023 raw coal production in spreadsheet."
    },
    {
        "golden_id": "GOLD-09",
        "source_id": "VAL-DOC-03",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra OC",
        "metric_name": "raw_coal_production_may",
        "expected_value": "86,210",
        "expected_normalized_value": "86210.0",
        "expected_location": {"page": None, "sheet": "Production_Summary", "cell": "B3", "row": 3, "column": "Raw_Coal_Production_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "May 2023 raw coal production in spreadsheet."
    },
    {
        "golden_id": "GOLD-10",
        "source_id": "VAL-DOC-03",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Upper Gevra Seam",
        "metric_name": "proved_reserves",
        "expected_value": "124.5 MT",
        "expected_normalized_value": "124.5",
        "expected_location": {"page": None, "sheet": "Seam_Reserves", "cell": "B2", "row": 2, "column": "Proved_Reserves_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Upper Gevra Seam proved reserves from Seam_Reserves sheet."
    },
    {
        "golden_id": "GOLD-11",
        "source_id": "VAL-DOC-04",
        "document_name": "bccl_moonidih_strata_metrics.csv",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Moonidih Colliery",
        "metric_name": "monthly_extraction_seam_xvi",
        "expected_value": "82,450",
        "expected_normalized_value": "82450.0",
        "expected_location": {"page": None, "sheet": None, "cell": None, "row": 1, "column": "Monthly_Extraction_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Moonidih Seam XVI extraction value from CSV Row 1."
    },
    {
        "golden_id": "GOLD-12",
        "source_id": "VAL-DOC-05",
        "document_name": "ecl_rajmahal_geological_section.png",
        "expected_type": "VISUAL",
        "entity_name": "Rajmahal OCP",
        "metric_name": "figure_classification",
        "expected_value": "GEOLOGICAL_SECTION",
        "expected_normalized_value": "GEOLOGICAL_SECTION",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Direct image of geological cross section for Rajmahal OCP."
    },
    {
        "golden_id": "GOLD-13",
        "source_id": "VAL-DOC-06",
        "document_name": "wcl_pench_operations_brief.docx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Pench Area",
        "metric_name": "raw_coal_production",
        "expected_value": "66.8 MT",
        "expected_normalized_value": "66.8",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "WCL Pench area raw coal production in docx narrative."
    },
    {
        "golden_id": "GOLD-14",
        "source_id": "VAL-DOC-07",
        "document_name": "ccl_geological_technical_note.txt",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "North Karanpura",
        "metric_name": "geological_coal_reserves",
        "expected_value": "86.0 MT",
        "expected_normalized_value": "86.0",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Gross geological coal reserves for North Karanpura basin."
    },
    {
        "golden_id": "GOLD-15",
        "source_id": "VAL-DOC-08",
        "document_name": "conflict_source_alpha.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra OC",
        "metric_name": "raw_coal_production",
        "expected_value": "82,450 MT",
        "expected_normalized_value": "82450.0",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Source Alpha reported production figure for conflict testing."
    },
    {
        "golden_id": "GOLD-16",
        "source_id": "VAL-DOC-09",
        "document_name": "conflict_source_beta.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra OC",
        "metric_name": "raw_coal_production",
        "expected_value": "84,250 MT",
        "expected_normalized_value": "84250.0",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Source Beta reported production figure (contradicting Source Alpha)."
    },
    {
        "golden_id": "GOLD-17",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Coal India Limited",
        "metric_name": "capital_expenditure",
        "expected_value": "19,840 Crore INR",
        "expected_normalized_value": "19840.0",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 1.0,
        "notes": "CIL capex on page 1."
    },
    {
        "golden_id": "GOLD-18",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "TABLE",
        "entity_name": "BCCL",
        "metric_name": "actual_production",
        "expected_value": "41.2",
        "expected_normalized_value": "41.2",
        "expected_location": {"page": 2, "sheet": None, "cell": None, "row": 2, "column": "Actual Production", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Subsidiary table BCCL actual production."
    },
    {
        "golden_id": "GOLD-19",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "TABLE",
        "entity_name": "CCL",
        "metric_name": "actual_production",
        "expected_value": "86.0",
        "expected_normalized_value": "86.0",
        "expected_location": {"page": 2, "sheet": None, "cell": None, "row": 3, "column": "Actual Production", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Subsidiary table CCL actual production."
    },
    {
        "golden_id": "GOLD-20",
        "source_id": "VAL-DOC-01",
        "document_name": "cil_annual_report_2023_24_extract.pdf",
        "expected_type": "TABLE",
        "entity_name": "MCL",
        "metric_name": "actual_production",
        "expected_value": "206.0",
        "expected_normalized_value": "206.0",
        "expected_location": {"page": 2, "sheet": None, "cell": None, "row": 7, "column": "Actual Production", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Subsidiary table MCL actual production."
    },
    {
        "golden_id": "GOLD-21",
        "source_id": "VAL-DOC-02",
        "document_name": "cmpdi_exploration_bulletin_2023.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra Block",
        "metric_name": "proved_geological_reserves",
        "expected_value": "335.3 MT",
        "expected_normalized_value": "335.3",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "CMPDI proved geological reserves in Gevra block."
    },
    {
        "golden_id": "GOLD-22",
        "source_id": "VAL-DOC-02",
        "document_name": "cmpdi_exploration_bulletin_2023.pdf",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Raniganj Formation",
        "metric_name": "proved_reserves",
        "expected_value": "24.8 MT",
        "expected_normalized_value": "24.8",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Proved reserves of Raniganj formation in eastern sector."
    },
    {
        "golden_id": "GOLD-23",
        "source_id": "VAL-DOC-02",
        "document_name": "cmpdi_exploration_bulletin_2023.pdf",
        "expected_type": "VISUAL",
        "entity_name": "Coal Seam II",
        "metric_name": "proved_reserves",
        "expected_value": "52.5 MT",
        "expected_normalized_value": "52.5",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": [80, 420, 515, 460]},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Stratigraphic cross section Coal Seam II proved reserves."
    },
    {
        "golden_id": "GOLD-24",
        "source_id": "VAL-DOC-03",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra OC",
        "metric_name": "raw_coal_production_june",
        "expected_value": "84,100",
        "expected_normalized_value": "84100.0",
        "expected_location": {"page": None, "sheet": "Production_Summary", "cell": "B4", "row": 4, "column": "Raw_Coal_Production_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "June 2023 raw coal production from XLSX."
    },
    {
        "golden_id": "GOLD-25",
        "source_id": "VAL-DOC-03",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Gevra OC",
        "metric_name": "raw_coal_production_total_q1",
        "expected_value": "252,760",
        "expected_normalized_value": "252760.0",
        "expected_location": {"page": None, "sheet": "Production_Summary", "cell": "B5", "row": 5, "column": "Raw_Coal_Production_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Total Q1 production from XLSX."
    },
    {
        "golden_id": "GOLD-26",
        "source_id": "VAL-DOC-03",
        "document_name": "secl_gevra_production_fy24.xlsx",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Lower Gevra Seam",
        "metric_name": "proved_reserves",
        "expected_value": "210.8 MT",
        "expected_normalized_value": "210.8",
        "expected_location": {"page": None, "sheet": "Seam_Reserves", "cell": "B3", "row": 3, "column": "Proved_Reserves_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Lower Gevra Seam proved reserves from XLSX."
    },
    {
        "golden_id": "GOLD-27",
        "source_id": "VAL-DOC-04",
        "document_name": "bccl_moonidih_strata_metrics.csv",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Moonidih Colliery",
        "metric_name": "monthly_extraction_seam_xvii",
        "expected_value": "86,210",
        "expected_normalized_value": "86210.0",
        "expected_location": {"page": None, "sheet": None, "cell": None, "row": 2, "column": "Monthly_Extraction_MT", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.0,
        "notes": "Moonidih Seam XVII extraction from CSV Row 2."
    },
    {
        "golden_id": "GOLD-28",
        "source_id": "VAL-DOC-04",
        "document_name": "bccl_moonidih_strata_metrics.csv",
        "expected_type": "STRUCTURED_VALUE",
        "entity_name": "Moonidih Colliery",
        "metric_name": "ash_percentage_seam_xvi",
        "expected_value": "18.5%",
        "expected_normalized_value": "18.5",
        "expected_location": {"page": None, "sheet": None, "cell": None, "row": 1, "column": "Ash_Percentage", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.1,
        "notes": "Ash percentage from CSV Row 1."
    },
    {
        "golden_id": "GOLD-29",
        "source_id": "VAL-DOC-05",
        "document_name": "ecl_rajmahal_geological_section.png",
        "expected_type": "VISUAL",
        "entity_name": "Coal Seam II",
        "metric_name": "proved_reserves",
        "expected_value": "68.2 MT",
        "expected_normalized_value": "68.2",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": None, "column": None, "bbox": None},
        "provenance_required": True,
        "tolerance": 0.05,
        "notes": "Coal Seam II proved reserves on Rajmahal geological section."
    },
    {
        "golden_id": "GOLD-30",
        "source_id": "VAL-DOC-06",
        "document_name": "wcl_pench_operations_brief.docx",
        "expected_type": "TABLE",
        "entity_name": "Seam I",
        "metric_name": "ash_content",
        "expected_value": "24.5%",
        "expected_normalized_value": "24.5",
        "expected_location": {"page": 1, "sheet": None, "cell": None, "row": 1, "column": "Ash Content (%)", "bbox": None},
        "provenance_required": True,
        "tolerance": 0.1,
        "notes": "DOCX Table row 1 ash content."
    }
]

golden_path = os.path.join(DATA_DIR, "golden_evidence_set.json")
with open(golden_path, "w", encoding="utf-8") as f:
    json.dump(golden_evidence, f, indent=2)

print(f"Saved golden evidence set to {golden_path} ({len(golden_evidence)} items).")

# ----------------------------------------------------------------------
# 4. GENERATE MULTIMODAL QUESTION BANK (data/question_bank.json)
# ----------------------------------------------------------------------
question_bank = [
    {
        "question_id": "Q-CAT-A-01",
        "category": "CATEGORY_A_DIRECT_LOOKUP",
        "query": "What was the total raw coal production reported by Coal India Limited in FY 2023-24?",
        "target_documents": ["cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["773.6 MT", "10.0% growth"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cil_annual_report_2023_24_extract.pdf"]
    },
    {
        "question_id": "Q-CAT-A-02",
        "category": "CATEGORY_A_DIRECT_LOOKUP",
        "query": "What was the total exploration drilling meterage completed by CMPDI in 2023?",
        "target_documents": ["cmpdi_exploration_bulletin_2023.pdf"],
        "expected_answer_elements": ["13.82 Lakh meters"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cmpdi_exploration_bulletin_2023.pdf"]
    },
    {
        "question_id": "Q-CAT-B-01",
        "category": "CATEGORY_B_TABLE_REASONING",
        "query": "What was the actual production of SECL compared to its target in FY 2023-24?",
        "target_documents": ["cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["Target: 185.0 MT", "Actual: 187.0 MT", "+1.08%"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cil_annual_report_2023_24_extract.pdf"]
    },
    {
        "question_id": "Q-CAT-B-02",
        "category": "CATEGORY_B_TABLE_REASONING",
        "query": "What were the raw coal production figures for Gevra OC in April and May 2023?",
        "target_documents": ["secl_gevra_production_fy24.xlsx"],
        "expected_answer_elements": ["April 2023: 82,450 MT", "May 2023: 86,210 MT"],
        "expected_status": "SUPPORTED",
        "required_citations": ["secl_gevra_production_fy24.xlsx"]
    },
    {
        "question_id": "Q-CAT-C-01",
        "category": "CATEGORY_C_CALCULATION",
        "query": "What was the percentage increase in Gevra OC production from April 2023 to May 2023?",
        "target_documents": ["secl_gevra_production_fy24.xlsx"],
        "expected_answer_elements": ["+4.56%", "82,450", "86,210", "increased by +3,760"],
        "expected_status": "SUPPORTED",
        "required_citations": ["secl_gevra_production_fy24.xlsx"]
    },
    {
        "question_id": "Q-CAT-D-01",
        "category": "CATEGORY_D_VISUAL_QUESTION",
        "query": "What type of geological diagram is Figure 1 in the CIL operational report?",
        "target_documents": ["cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["MAP", "CMPDI Regional Exploration Grid", "Barakar Coal Measures"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cil_annual_report_2023_24_extract.pdf"]
    },
    {
        "question_id": "Q-CAT-E-01",
        "category": "CATEGORY_E_VISUAL_OCR",
        "query": "Which coal seam thicknesses and proved reserves are visible in the CMPDI stratigraphic section?",
        "target_documents": ["cmpdi_exploration_bulletin_2023.pdf"],
        "expected_answer_elements": ["Coal Seam I (8.5 m)", "Coal Seam II (14.2 m, 52.5 MT)"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cmpdi_exploration_bulletin_2023.pdf"]
    },
    {
        "question_id": "Q-CAT-F-01",
        "category": "CATEGORY_F_TEXT_AND_TABLE",
        "query": "Does the narrative production claim for WCL Pench area agree with the reported table?",
        "target_documents": ["wcl_pench_operations_brief.docx"],
        "expected_answer_elements": ["66.8 MT", "target of 65.0 MT", "Seam I Grade G-8", "Seam II Grade G-9"],
        "expected_status": "SUPPORTED",
        "required_citations": ["wcl_pench_operations_brief.docx"]
    },
    {
        "question_id": "Q-CAT-G-01",
        "category": "CATEGORY_G_TEXT_AND_VISUAL",
        "query": "What geological condition is described for Rajmahal OCP and where is it represented in the section diagram?",
        "target_documents": ["ecl_rajmahal_geological_section.png", "cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["Barakar formation", "Seam II", "Seam III", "Interburden Shale Parting"],
        "expected_status": "SUPPORTED",
        "required_citations": ["ecl_rajmahal_geological_section.png"]
    },
    {
        "question_id": "Q-CAT-H-01",
        "category": "CATEGORY_H_TABLE_AND_VISUAL",
        "query": "Compare the reported Upper Gevra Seam reserves with the CMPDI stratigraphic cross section.",
        "target_documents": ["secl_gevra_production_fy24.xlsx", "cmpdi_exploration_bulletin_2023.pdf"],
        "expected_answer_elements": ["124.5 MT", "Seam II (52.5 MT)", "Barakar Formation"],
        "expected_status": "SUPPORTED",
        "required_citations": ["secl_gevra_production_fy24.xlsx", "cmpdi_exploration_bulletin_2023.pdf"]
    },
    {
        "question_id": "Q-CAT-I-01",
        "category": "CATEGORY_I_PRIMARY_FULL_MULTIMODAL_GOLDEN_DEMO",
        "query": "Compare Gevra OC's production change between reporting periods and explain what geological evidence in the available records is relevant to the mine's condition.",
        "target_documents": ["secl_gevra_production_fy24.xlsx", "cil_annual_report_2023_24_extract.pdf", "cmpdi_exploration_bulletin_2023.pdf"],
        "expected_answer_elements": [
            "production increased from 82,450 MT (April 2023) to 86,210 MT (May 2023) (+4.56%)",
            "annual production reached 59.5 MT",
            "geological evidence confirms thick seam development in Barakar Formation with composite thickness up to 35 meters",
            "proved geological reserves of 335.3 MT"
        ],
        "expected_status": "SUPPORTED",
        "required_modalities": ["TEXT", "TABLE", "VISUAL"]
    },
    {
        "question_id": "Q-CAT-J-01",
        "category": "CATEGORY_J_ADVERSARIAL_REFUSAL",
        "query": "What was Gevra OC's raw coal production in January 2015?",
        "target_documents": [],
        "expected_answer_elements": ["Insufficient verified evidence found in the selected knowledge base."],
        "expected_status": "REFUSED",
        "notes": "Query asks about a historical period completely absent from the FY2023-24 corpus."
    },
    {
        "question_id": "Q-CAT-J-02",
        "category": "CATEGORY_J_ADVERSARIAL_REFUSAL",
        "query": "What is the exact methane gas drainage volume at Moonidih colliery in cubic meters per hour?",
        "target_documents": [],
        "expected_answer_elements": ["Insufficient verified evidence found in the selected knowledge base."],
        "expected_status": "REFUSED",
        "notes": "Query asks about an unrecorded gas drainage metric."
    },
    {
        "question_id": "Q-CAT-K-01",
        "category": "CATEGORY_K_CONFLICT_DETECTION",
        "query": "What was the raw coal production of Gevra OC according to the conflicting Q1 audit reports?",
        "target_documents": ["conflict_source_alpha.pdf", "conflict_source_beta.pdf"],
        "expected_answer_elements": [
            "Conflicting evidence detected",
            "Source Alpha: 82,450 MT",
            "Source Beta: 84,250 MT",
            "Verification required"
        ],
        "expected_status": "CONFLICT_REQUIRES_REVIEW",
    },
    {
        "question_id": "Q-CAT-A-03",
        "category": "CATEGORY_A_DIRECT_LOOKUP",
        "query": "What was the capital expenditure of Coal India Limited in FY 2023-24?",
        "target_documents": ["cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["19,840 Crore INR"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cil_annual_report_2023_24_extract.pdf"]
    },
    {
        "question_id": "Q-CAT-B-03",
        "category": "CATEGORY_B_TABLE_REASONING",
        "query": "What was the raw coal production and variance of CCL compared to its target in FY 2023-24?",
        "target_documents": ["cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["Target: 84.0 MT", "Actual: 86.0 MT", "+2.38%"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cil_annual_report_2023_24_extract.pdf"]
    },
    {
        "question_id": "Q-CAT-C-02",
        "category": "CATEGORY_C_CALCULATION",
        "query": "What was the total CIL production variance in MT between the target of 755.0 MT and actual 773.6 MT?",
        "target_documents": ["cil_annual_report_2023_24_extract.pdf"],
        "expected_answer_elements": ["+18.6 MT", "+2.46%"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cil_annual_report_2023_24_extract.pdf"]
    },
    {
        "question_id": "Q-CAT-D-02",
        "category": "CATEGORY_D_VISUAL_QUESTION",
        "query": "What type of visual figure is the Rajmahal OCP exploration diagram?",
        "target_documents": ["ecl_rajmahal_geological_section.png"],
        "expected_answer_elements": ["GEOLOGICAL_SECTION", "Rajmahal OCP", "Seam II & III"],
        "expected_status": "SUPPORTED",
        "required_citations": ["ecl_rajmahal_geological_section.png"]
    },
    {
        "question_id": "Q-CAT-E-02",
        "category": "CATEGORY_E_VISUAL_OCR",
        "query": "What is the thickness and ash content of Coal Seam I shown in the CMPDI litholog?",
        "target_documents": ["cmpdi_exploration_bulletin_2023.pdf"],
        "expected_answer_elements": ["8.5 m", "24.5%"],
        "expected_status": "SUPPORTED",
        "required_citations": ["cmpdi_exploration_bulletin_2023.pdf"]
    },
    {
        "question_id": "Q-CAT-F-02",
        "category": "CATEGORY_F_TEXT_AND_TABLE",
        "query": "Does the North Karanpura geological reserve statement in the technical note state proved coal resources?",
        "target_documents": ["ccl_geological_technical_note.txt"],
        "expected_answer_elements": ["86.0 MT", "Barakar Formation"],
        "expected_status": "SUPPORTED",
        "required_citations": ["ccl_geological_technical_note.txt"]
    },
    {
        "question_id": "Q-CAT-G-02",
        "category": "CATEGORY_G_TEXT_AND_VISUAL",
        "query": "What is the proved reserve of Coal Seam II shown in the Rajmahal geological cross section?",
        "target_documents": ["ecl_rajmahal_geological_section.png"],
        "expected_answer_elements": ["68.2 MT", "Thickness: 16.8 m"],
        "expected_status": "SUPPORTED",
        "required_citations": ["ecl_rajmahal_geological_section.png"]
    },
    {
        "question_id": "Q-CAT-H-02",
        "category": "CATEGORY_H_TABLE_AND_VISUAL",
        "query": "Compare the proved reserves of Lower Gevra Seam from the spreadsheet with CMPDI geological section Seam II.",
        "target_documents": ["secl_gevra_production_fy24.xlsx", "cmpdi_exploration_bulletin_2023.pdf"],
        "expected_answer_elements": ["210.8 MT", "52.5 MT"],
        "expected_status": "SUPPORTED",
        "required_citations": ["secl_gevra_production_fy24.xlsx", "cmpdi_exploration_bulletin_2023.pdf"]
    },
    {
        "question_id": "Q-CAT-J-03",
        "category": "CATEGORY_J_ADVERSARIAL_REFUSAL",
        "query": "What was the lithium extraction rate at Korba Coalfield in FY 2023-24?",
        "target_documents": [],
        "expected_answer_elements": ["Insufficient verified evidence found in the selected knowledge base."],
        "expected_status": "REFUSED",
        "notes": "Query asks about a non-coal mineral extraction metric not present in CIL coal records."
    },
    {
        "question_id": "Q-CAT-K-02",
        "category": "CATEGORY_K_CONFLICT_DETECTION",
        "query": "Is there a conflict between Source Alpha and Source Beta on Gevra OC quarterly production?",
        "target_documents": ["conflict_source_alpha.pdf", "conflict_source_beta.pdf"],
        "expected_answer_elements": ["82,450 MT", "84,250 MT", "conflict"],
        "expected_status": "CONFLICT_REQUIRES_REVIEW",
        "notes": "Conflict confirmation query."
    }
]

qbank_path = os.path.join(DATA_DIR, "question_bank.json")
with open(qbank_path, "w", encoding="utf-8") as f:
    json.dump(question_bank, f, indent=2)

print(f"Saved question bank to {qbank_path} ({len(question_bank)} questions).")
