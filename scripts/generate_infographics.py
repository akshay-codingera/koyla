"""
KOYLA — SIH 2026 System Architecture & Technical Approach Infographic Generator
Version: 2.0 (High-Legibility, Engineering Blueprint Aesthetic, SIH 16:9 PPT-Ready)

Generates:
1. koyla_architecture_diagram.svg (Standalone 4/5th diagram for PowerPoint insertion)
2. koyla_sih_presentation_slide.svg (Complete 16:9 SIH slide with left 1/5th technical summary panel)
3. Renders both to crisp 4K PNGs via Headless Chrome
4. Generates a native PowerPoint (.pptx) file with editable layout and slides
5. Copies images to artifact directory for instant viewing
"""

import os
import shutil
import subprocess
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_standalone_diagram_svg():
    # Width: 2600, Height: 1560
    # Clean, high-legibility, black/neutral grey engineering drawing with very restrained dark navy/slate headers
    
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2600 1560" width="2600" height="1560" style="background:#FFFFFF; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <!-- Technical arrowhead markers -->
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#1E293B"/>
    </marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#0F172A"/>
    </marker>
    <marker id="arrow-amber" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#B45309"/>
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#166534"/>
    </marker>

    <!-- Subtle drop shadows / borders -->
    <filter id="card-shadow" x="-2%" y="-1%" width="104%" height="103%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0F172A" flood-opacity="0.06"/>
    </filter>
    <filter id="fabric-shadow" x="-3%" y="-1%" width="106%" height="103%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#0F172A" flood-opacity="0.10"/>
    </filter>
  </defs>

  <!-- ==================== BACKGROUND GRID (ENGINEERING BLUEPRINT PATTERN) ==================== -->
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#F1F5F9" stroke-width="1"/>
  </pattern>
  <rect width="2600" height="1560" fill="#FFFFFF"/>
  <rect width="2600" height="1560" fill="url(#grid)"/>

  <!-- ==================== MAIN TOP BANNER ==================== -->
  <g transform="translate(40, 24)">
    <rect x="0" y="0" width="2520" height="96" rx="4" fill="#0F172A" stroke="#0F172A" stroke-width="1.5"/>
    <text x="32" y="42" fill="#FFFFFF" font-size="28" font-weight="700" letter-spacing="1">TECHNICAL APPROACH — KOYLA EVIDENCE INTELLIGENCE ARCHITECTURE</text>
    <text x="32" y="74" fill="#94A3B8" font-size="16" font-weight="500">From heterogeneous geological records to traceable, evidence-backed intelligence | CIL &amp; CMPDI — Problem Statement 26023</text>
    
    <rect x="1840" y="24" width="648" height="48" rx="3" fill="#1E293B" stroke="#334155" stroke-width="1"/>
    <text x="2164" y="54" fill="#E2E8F0" font-size="13" font-weight="600" text-anchor="middle" letter-spacing="0.5">PARADIGM: EVIDENCE-CENTRIC (NOT GENERIC RAG)</text>
  </g>

  <!-- ==================== FLOW SEQUENCE BAR (STAGE CHEVRONS) ==================== -->
  <g transform="translate(40, 132)">
    <!-- Stage 1 -->
    <rect x="0" y="0" width="280" height="28" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1" rx="2"/>
    <text x="140" y="19" fill="#0F172A" font-size="12" font-weight="700" text-anchor="middle">STAGE 01 : SOURCES</text>
    
    <!-- Stage 2 -->
    <rect x="310" y="0" width="310" height="28" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1" rx="2"/>
    <text x="465" y="19" fill="#0F172A" font-size="12" font-weight="700" text-anchor="middle">STAGE 02 : INGESTION &amp; OCR</text>
    
    <!-- Stage 3 (Highlighted as central) -->
    <rect x="650" y="0" width="410" height="28" fill="#1E293B" stroke="#0F172A" stroke-width="1" rx="2"/>
    <text x="855" y="19" fill="#FFFFFF" font-size="12" font-weight="700" text-anchor="middle">STAGE 03 : EVIDENCE FABRIC (CORE)</text>
    
    <!-- Stage 4 -->
    <rect x="1090" y="0" width="270" height="28" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1" rx="2"/>
    <text x="1225" y="19" fill="#0F172A" font-size="12" font-weight="700" text-anchor="middle">STAGE 04 : RETRIEVAL</text>
    
    <!-- Stage 5 (Highlighted as key differentiator) -->
    <rect x="1390" y="0" width="390" height="28" fill="#334155" stroke="#1E293B" stroke-width="1" rx="2"/>
    <text x="1585" y="19" fill="#FFFFFF" font-size="12" font-weight="700" text-anchor="middle">STAGE 05 : RESOLUTION &amp; RECONCILIATION</text>
    
    <!-- Stage 6 -->
    <rect x="1810" y="0" width="390" height="28" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1" rx="2"/>
    <text x="2005" y="19" fill="#0F172A" font-size="12" font-weight="700" text-anchor="middle">STAGE 06 : DUAL COMPUTATION</text>
    
    <!-- Stage 7 -->
    <rect x="2230" y="0" width="290" height="28" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1" rx="2"/>
    <text x="2375" y="19" fill="#0F172A" font-size="12" font-weight="700" text-anchor="middle">STAGE 07 : TRACEABLE OUTPUT</text>
  </g>

  <!-- ========================================================================= -->
  <!-- STAGE 01 — SOURCE RECORDS -->
  <!-- ========================================================================= -->
  <g transform="translate(40, 172)">
    <rect x="0" y="0" width="280" height="1060" rx="4" fill="#FFFFFF" stroke="#334155" stroke-width="1.5" filter="url(#card-shadow)"/>
    
    <!-- Header -->
    <rect x="0" y="0" width="280" height="52" fill="#0F172A" rx="4 4 0 0"/>
    <text x="14" y="33" fill="#FFFFFF" font-size="15" font-weight="700">01. SOURCE RECORDS</text>
    <rect x="204" y="14" width="62" height="24" rx="2" fill="#334155"/>
    <text x="235" y="30" fill="#E2E8F0" font-size="11" font-weight="600" text-anchor="middle">INPUTS</text>

    <text x="14" y="78" fill="#64748B" font-size="12" font-weight="600">HETEROGENEOUS INPUTS</text>

    <!-- 7 Source Items -->
    <g transform="translate(14, 92)">
      <!-- Item 1 -->
      <rect x="0" y="0" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="14" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="28" fill="#0F172A" font-size="14" font-weight="700">Geological Reports</text>
      <text x="26" y="48" fill="#475569" font-size="12">Borehole logs, lithology, reserves</text>

      <!-- Item 2 -->
      <rect x="0" y="76" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="90" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="104" fill="#0F172A" font-size="14" font-weight="700">Mining &amp; Project Reports</text>
      <text x="26" y="124" fill="#475569" font-size="12">Mine plans, feasibility, statutory</text>

      <!-- Item 3 -->
      <rect x="0" y="152" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="166" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="180" fill="#0F172A" font-size="14" font-weight="700">Production Data</text>
      <text x="26" y="200" fill="#475569" font-size="12">Monthly coal offtake, dispatch</text>

      <!-- Item 4 -->
      <rect x="0" y="228" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="242" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="256" fill="#0F172A" font-size="14" font-weight="700">Historical Archives</text>
      <text x="26" y="276" fill="#475569" font-size="12">Colliery survey records (1975–)</text>

      <!-- Item 5 -->
      <rect x="0" y="304" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="318" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="332" fill="#0F172A" font-size="14" font-weight="700">Spreadsheets</text>
      <text x="26" y="352" fill="#475569" font-size="12">Multi-sheet seam tables &amp; annexures</text>

      <!-- Item 6 -->
      <rect x="0" y="380" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="394" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="408" fill="#0F172A" font-size="14" font-weight="700">Scanned Documents</text>
      <text x="26" y="428" fill="#475569" font-size="12">Photocopied typed exploration files</text>

      <!-- Item 7 -->
      <rect x="0" y="456" width="252" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <rect x="10" y="470" width="6" height="38" fill="#0F172A" rx="1"/>
      <text x="26" y="484" fill="#0F172A" font-size="14" font-weight="700">Geological Figures / Maps</text>
      <text x="26" y="504" fill="#475569" font-size="12">Stratigraphic columns, seam folios</text>
    </g>

    <!-- Technical label box -->
    <g transform="translate(14, 650)">
      <rect x="0" y="0" width="252" height="96" rx="3" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1"/>
      <text x="14" y="24" fill="#0F172A" font-size="12" font-weight="700">SUPPORTED FORMATS</text>
      <text x="14" y="50" fill="#334155" font-size="13" font-weight="600">PDF / DOCX / XLSX / CSV /</text>
      <text x="14" y="72" fill="#334155" font-size="13" font-weight="600">TXT / Images (PNG, JPG, TIFF)</text>
      <rect x="14" y="82" width="224" height="2" fill="#CBD5E1"/>
    </g>

    <!-- Verification / Ingestion Tag -->
    <g transform="translate(14, 766)">
      <rect x="0" y="0" width="252" height="84" rx="3" fill="#FFFFFF" stroke="#0F172A" stroke-width="1" stroke-dasharray="3,3"/>
      <text x="14" y="24" fill="#0F172A" font-size="12" font-weight="700">INGESTION PROTOCOL</text>
      <text x="14" y="46" fill="#475569" font-size="12">• MIME Type Sniffing</text>
      <text x="14" y="66" fill="#475569" font-size="12">• SHA-256 Cryptographic Hash</text>
    </g>
  </g>

  <!-- Connectors: Stage 1 -> Stage 2 -->
  <line x1="320" y1="520" x2="350" y2="520" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- ========================================================================= -->
  <!-- STAGE 02 — INGESTION & EXTRACTION -->
  <!-- ========================================================================= -->
  <g transform="translate(350, 172)">
    <rect x="0" y="0" width="310" height="1060" rx="4" fill="#FFFFFF" stroke="#334155" stroke-width="1.5" filter="url(#card-shadow)"/>
    
    <!-- Stage Header (Fixed layout: title & badge perfectly spaced) -->
    <rect x="0" y="0" width="310" height="52" fill="#0F172A" rx="4 4 0 0"/>
    <text x="12" y="33" fill="#FFFFFF" font-size="14.5" font-weight="700">02. INGESTION &amp; EXTRACTION</text>
    <rect x="236" y="14" width="62" height="24" rx="2" fill="#334155"/>
    <text x="267" y="30" fill="#E2E8F0" font-size="11" font-weight="600" text-anchor="middle">PARSER</text>

    <!-- Processing Submodules -->
    <g transform="translate(14, 70)">
      <text x="0" y="14" fill="#64748B" font-size="12" font-weight="600">MULTIMODAL PARSERS</text>

      <!-- Box 1 -->
      <rect x="0" y="26" width="282" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="14" y="50" fill="#0F172A" font-size="14" font-weight="700">Document Parsing</text>
      <text x="14" y="72" fill="#475569" font-size="12">PyMuPDF, pdfplumber, python-docx</text>

      <!-- Box 2 -->
      <rect x="0" y="100" width="282" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="14" y="124" fill="#0F172A" font-size="14" font-weight="700">OCR (Optical Character Rec.)</text>
      <text x="14" y="146" fill="#475569" font-size="12">Tesseract (eng+hin), OpenCV deskew</text>

      <!-- Box 3 -->
      <rect x="0" y="174" width="282" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="14" y="198" fill="#0F172A" font-size="14" font-weight="700">Table Extraction</text>
      <text x="14" y="220" fill="#475569" font-size="12">Cell borders, merged headers, openpyxl</text>

      <!-- Box 4 -->
      <rect x="0" y="248" width="282" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="14" y="272" fill="#0F172A" font-size="14" font-weight="700">Visual / Figure Extraction</text>
      <text x="14" y="294" fill="#475569" font-size="12">Isolate diagrams, maps, borehole plots</text>

      <!-- Box 5 -->
      <rect x="0" y="322" width="282" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="14" y="346" fill="#0F172A" font-size="14" font-weight="700">Metadata Extraction</text>
      <text x="14" y="368" fill="#475569" font-size="12">Doc ID, org, fiscal year, author, date</text>

      <!-- Box 6 -->
      <rect x="0" y="396" width="282" height="66" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="14" y="420" fill="#0F172A" font-size="14" font-weight="700">Geological Attribute Extraction</text>
      <text x="14" y="442" fill="#475569" font-size="12">Seam, thickness, ash %, grade, depth</text>
    </g>

    <!-- Visual Split Box: 4 Structured Channels -->
    <g transform="translate(14, 560)">
      <rect x="0" y="0" width="282" height="220" rx="3" fill="#F1F5F9" stroke="#0F172A" stroke-width="1.5"/>
      <text x="14" y="24" fill="#0F172A" font-size="12" font-weight="700">STRUCTURED OUTPUT SPLIT</text>
      <text x="14" y="42" fill="#64748B" font-size="11">Separated physical data modalities:</text>

      <!-- Channel 1: Text -->
      <g transform="translate(14, 52)">
        <rect x="0" y="0" width="254" height="32" rx="2" fill="#FFFFFF" stroke="#64748B" stroke-width="1"/>
        <text x="10" y="21" fill="#0F172A" font-size="12" font-weight="700">TEXT</text>
        <text x="70" y="21" fill="#475569" font-size="11">Paragraphs, sections, headers</text>
      </g>

      <!-- Channel 2: Tables -->
      <g transform="translate(14, 90)">
        <rect x="0" y="0" width="254" height="32" rx="2" fill="#FFFFFF" stroke="#64748B" stroke-width="1"/>
        <text x="10" y="21" fill="#0F172A" font-size="12" font-weight="700">TABLES</text>
        <text x="70" y="21" fill="#475569" font-size="11">Row/col hierarchy, cell units</text>
      </g>

      <!-- Channel 3: Visuals -->
      <g transform="translate(14, 128)">
        <rect x="0" y="0" width="254" height="32" rx="2" fill="#FFFFFF" stroke="#64748B" stroke-width="1"/>
        <text x="10" y="21" fill="#0F172A" font-size="12" font-weight="700">VISUALS</text>
        <text x="70" y="21" fill="#475569" font-size="11">Bounding boxes, lithology folios</text>
      </g>

      <!-- Channel 4: Structured Fields -->
      <g transform="translate(14, 166)">
        <rect x="0" y="0" width="254" height="38" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.2"/>
        <text x="10" y="18" fill="#0F172A" font-size="12" font-weight="700">STRUCTURED FIELDS</text>
        <text x="10" y="32" fill="#475569" font-size="10">Typed tuples (entity, metric, value, unit)</text>
      </g>
    </g>

    <!-- Ingestion Principle -->
    <g transform="translate(14, 800)">
      <rect x="0" y="0" width="282" height="50" rx="3" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1"/>
      <text x="10" y="20" fill="#0F172A" font-size="11" font-weight="700">Ingestion Principle:</text>
      <text x="10" y="36" fill="#475569" font-size="11">Native digital parsing first; OCR only on scans.</text>
    </g>
  </g>

  <!-- Connectors: Stage 2 (4 pipes) -> Stage 3 -->
  <path d="M 660 626 L 700 626" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>
  <path d="M 660 664 L 700 664" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>
  <path d="M 660 702 L 700 702" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>
  <path d="M 660 742 L 700 742" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- ========================================================================= -->
  <!-- STAGE 03 — EVIDENCE FABRIC (CENTRAL & LARGEST COMPONENT) -->
  <!-- ========================================================================= -->
  <g transform="translate(700, 172)">
    <rect x="0" y="0" width="410" height="1060" rx="4" fill="#FFFFFF" stroke="#0F172A" stroke-width="2.5" filter="url(#fabric-shadow)"/>
    
    <!-- Stage Header (Darkest authoritative) -->
    <rect x="0" y="0" width="410" height="56" fill="#0F172A" rx="4 4 0 0"/>
    <text x="16" y="32" fill="#FFFFFF" font-size="18" font-weight="800" letter-spacing="0.5">03. KOYLA EVIDENCE FABRIC</text>
    <rect x="312" y="14" width="84" height="26" rx="2" fill="#334155"/>
    <text x="354" y="31" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">CORE HUB</text>
    <text x="16" y="48" fill="#94A3B8" font-size="10.5" font-weight="500">CENTRAL MULTIMODAL EVIDENCE REPOSITORY</text>

    <!-- Structured Evidence Objects Section -->
    <g transform="translate(16, 72)">
      <text x="0" y="14" fill="#0F172A" font-size="13" font-weight="700">STRUCTURED EVIDENCE OBJECTS</text>
      <text x="0" y="30" fill="#64748B" font-size="11">Relational entities stored with immutable physical provenance:</text>

      <!-- 2-Column Grid of 8 Evidence Objects -->
      <g transform="translate(0, 40)">
        <!-- Col 1 -->
        <rect x="0" y="0" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="12" y="20" fill="#0F172A" font-size="13" font-weight="700">Documents</text>
        <text x="12" y="36" fill="#64748B" font-size="11">Hash, metadata, tier</text>

        <rect x="0" y="56" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="12" y="76" fill="#0F172A" font-size="13" font-weight="700">Pages</text>
        <text x="12" y="92" fill="#64748B" font-size="11">Page index, dimensions</text>

        <rect x="0" y="112" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="12" y="132" fill="#0F172A" font-size="13" font-weight="700">Chunks</text>
        <text x="12" y="148" fill="#64748B" font-size="11">Section-aware text</text>

        <rect x="0" y="168" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="12" y="188" fill="#0F172A" font-size="13" font-weight="700">Tables</text>
        <text x="12" y="204" fill="#64748B" font-size="11">Grid schema, headers</text>

        <!-- Col 2 -->
        <rect x="196" y="0" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="208" y="20" fill="#0F172A" font-size="13" font-weight="700">Table Rows</text>
        <text x="208" y="36" fill="#64748B" font-size="11">Row values, cell units</text>

        <rect x="196" y="56" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="208" y="76" fill="#0F172A" font-size="13" font-weight="700">Structured Fields</text>
        <text x="208" y="92" fill="#64748B" font-size="11">Key-value metrics</text>

        <rect x="196" y="112" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="208" y="132" fill="#0F172A" font-size="13" font-weight="700">Visual Assets</text>
        <text x="208" y="148" fill="#64748B" font-size="11">BBox, images, maps</text>

        <rect x="196" y="168" width="180" height="48" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="208" y="188" fill="#0F172A" font-size="13" font-weight="700">Evidence Metadata</text>
        <text x="208" y="204" fill="#64748B" font-size="11">Doc/Page/Table refs</text>
      </g>
    </g>

    <!-- Example Evidence Tuple Box -->
    <g transform="translate(16, 350)">
      <rect x="0" y="0" width="378" height="236" rx="3" fill="#F1F5F9" stroke="#0F172A" stroke-width="1.5"/>
      <rect x="0" y="0" width="378" height="32" fill="#334155" rx="3 3 0 0"/>
      <text x="14" y="22" fill="#FFFFFF" font-size="12" font-weight="700" letter-spacing="0.5">CANONICAL EVIDENCE TUPLE (SCHEMA)</text>

      <!-- Tuple Fields -->
      <g transform="translate(16, 46)">
        <text x="0" y="20" fill="#64748B" font-size="13" font-weight="600">Subject:</text>
        <rect x="80" y="4" width="260" height="24" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="92" y="21" fill="#0F172A" font-size="13" font-weight="700">Seam IV (Upper Horizon)</text>

        <text x="0" y="52" fill="#64748B" font-size="13" font-weight="600">Metric:</text>
        <rect x="80" y="36" width="260" height="24" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="92" y="53" fill="#0F172A" font-size="13" font-weight="700">Thickness</text>

        <text x="0" y="84" fill="#64748B" font-size="13" font-weight="600">Value / Unit:</text>
        <rect x="80" y="68" width="130" height="24" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="92" y="85" fill="#0F172A" font-size="13" font-weight="700">2.8</text>
        <rect x="220" y="68" width="120" height="24" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="232" y="85" fill="#0F172A" font-size="13" font-weight="700">Unit: m (Meters)</text>

        <text x="0" y="116" fill="#64748B" font-size="13" font-weight="600">Period:</text>
        <rect x="80" y="100" width="260" height="24" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="92" y="117" fill="#0F172A" font-size="13" font-weight="700">FY 2023–2024</text>

        <text x="0" y="148" fill="#64748B" font-size="13" font-weight="600">Source:</text>
        <rect x="80" y="132" width="260" height="38" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1"/>
        <text x="92" y="147" fill="#0F172A" font-size="11" font-weight="700">Doc: GR-SECL-2024-08.pdf</text>
        <text x="92" y="162" fill="#475569" font-size="11">Page: 42 | Table 3.2 | Row 8 | Cell D8</text>
      </g>
    </g>

    <!-- Source Provenance Invariant Banner -->
    <g transform="translate(16, 606)">
      <rect x="0" y="0" width="378" height="66" rx="3" fill="#0F172A" stroke="#0F172A" stroke-width="1"/>
      <text x="189" y="28" fill="#F8FAFC" font-size="13" font-weight="700" text-anchor="middle">PHYSICAL PROVENANCE INVARIANT</text>
      <text x="189" y="50" fill="#94A3B8" font-size="12" text-anchor="middle">“Every evidence object retains physical source provenance”</text>
    </g>

    <!-- Relational & Vector Storage Layer -->
    <g transform="translate(16, 694)">
      <rect x="0" y="0" width="378" height="150" rx="3" fill="#F8FAFC" stroke="#334155" stroke-width="1.2"/>
      <text x="16" y="26" fill="#0F172A" font-size="13" font-weight="700">DATABASE &amp; STORAGE SPECIFICATION</text>
      <rect x="16" y="38" width="346" height="1.5" fill="#E2E8F0"/>
      
      <text x="16" y="62" fill="#334155" font-size="12" font-weight="700">• PostgreSQL 16</text>
      <text x="150" y="62" fill="#64748B" font-size="12">Normalized relational tables (23 entities)</text>
      
      <text x="16" y="88" fill="#334155" font-size="12" font-weight="700">• pgvector HNSW</text>
      <text x="150" y="88" fill="#64748B" font-size="12">Dense embeddings with cosine indexing</text>

      <text x="16" y="114" fill="#334155" font-size="12" font-weight="700">• Multi-Tenancy</text>
      <text x="150" y="114" fill="#64748B" font-size="12">Organization scope (CIL / CMPDI / Subs)</text>

      <text x="16" y="136" fill="#0F172A" font-size="11" font-weight="700" letter-spacing="0.5">ENGINEERING LABEL: PostgreSQL 16 + pgvector</text>
    </g>
  </g>

  <!-- Connectors: Stage 3 -> Stage 4 -->
  <line x1="1110" y1="520" x2="1140" y2="520" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- ========================================================================= -->
  <!-- STAGE 04 — HYBRID RETRIEVAL (SUPPORTING LAYER) -->
  <!-- ========================================================================= -->
  <g transform="translate(1140, 172)">
    <rect x="0" y="0" width="270" height="1060" rx="4" fill="#FFFFFF" stroke="#334155" stroke-width="1.5" filter="url(#card-shadow)"/>
    
    <!-- Stage Header -->
    <rect x="0" y="0" width="270" height="52" fill="#0F172A" rx="4 4 0 0"/>
    <text x="14" y="33" fill="#FFFFFF" font-size="15" font-weight="700">04. HYBRID RETRIEVAL</text>
    <rect x="200" y="14" width="56" height="24" rx="2" fill="#334155"/>
    <text x="228" y="30" fill="#E2E8F0" font-size="11" font-weight="600" text-anchor="middle">RRF</text>

    <text x="14" y="78" fill="#64748B" font-size="12" font-weight="600">DUAL SEARCH &amp; FUSION</text>

    <!-- Component 1: BM25 Lexical -->
    <g transform="translate(14, 94)">
      <rect x="0" y="0" width="242" height="84" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="12" y="24" fill="#0F172A" font-size="14" font-weight="700">BM25 / Lexical Search</text>
      <text x="12" y="46" fill="#475569" font-size="12">• Exact Seam identifiers</text>
      <text x="12" y="66" fill="#475569" font-size="12">• Colliery &amp; borehole tags</text>
    </g>

    <text x="135" y="206" fill="#0F172A" font-size="22" font-weight="700" text-anchor="middle">+</text>

    <!-- Component 2: Vector Search -->
    <g transform="translate(14, 222)">
      <rect x="0" y="0" width="242" height="96" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="12" y="24" fill="#0F172A" font-size="14" font-weight="700">Vector Search</text>
      <text x="12" y="46" fill="#475569" font-size="12">• Semantic geological queries</text>
      <text x="12" y="66" fill="#475569" font-size="12">• BAAI/bge-small-en-v1.5</text>
      <text x="12" y="84" fill="#64748B" font-size="10">Local CPU/GPU inference</text>
    </g>

    <text x="135" y="346" fill="#0F172A" font-size="22" font-weight="700" text-anchor="middle">+</text>

    <!-- Component 3: RRF + Cross-Encoder Re-ranking -->
    <g transform="translate(14, 362)">
      <rect x="0" y="0" width="242" height="110" rx="3" fill="#F1F5F9" stroke="#0F172A" stroke-width="1.5"/>
      <text x="12" y="24" fill="#0F172A" font-size="13" font-weight="700">RRF + Cross-Encoder</text>
      <text x="12" y="44" fill="#0F172A" font-size="13" font-weight="700">Re-ranking</text>
      <text x="12" y="68" fill="#475569" font-size="12">• Reciprocal Rank Fusion (k=60)</text>
      <text x="12" y="88" fill="#475569" font-size="12">• TinyBERT Cross-Encoder</text>
      <text x="12" y="104" fill="#64748B" font-size="10">Filters ungrounded matches</text>
    </g>

    <line x1="135" y1="488" x2="135" y2="518" stroke="#0F172A" stroke-width="2" marker-end="url(#arrow-blue)"/>

    <!-- Ranked Result Box: Relevant Evidence -->
    <g transform="translate(14, 528)">
      <rect x="0" y="0" width="242" height="110" rx="3" fill="#0F172A" stroke="#0F172A" stroke-width="1"/>
      <text x="121" y="28" fill="#FFFFFF" font-size="14" font-weight="700" text-anchor="middle">Relevant Evidence</text>
      <text x="121" y="48" fill="#E2E8F0" font-size="11" text-anchor="middle">Top-k Verified Evidence Items</text>
      <line x1="20" y1="58" x2="222" y2="58" stroke="#334155" stroke-width="1"/>
      <text x="16" y="78" fill="#94A3B8" font-size="11">• Doc ID + Page Number</text>
      <text x="16" y="96" fill="#94A3B8" font-size="11">• Table ID + Row/Col Cell</text>
    </g>

    <!-- Supporting Layer Callout Note -->
    <g transform="translate(14, 696)">
      <rect x="0" y="0" width="242" height="130" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
      <text x="12" y="22" fill="#0F172A" font-size="12" font-weight="700">RETRIEVAL ROLE</text>
      <text x="12" y="42" fill="#475569" font-size="11" font-style="italic">“Retrieval is only the beginning.”</text>
      <text x="12" y="62" fill="#475569" font-size="11">It fetches candidate records.</text>
      <text x="12" y="78" fill="#475569" font-size="11">It DOES NOT answer questions</text>
      <text x="12" y="94" fill="#475569" font-size="11">directly without Stage 05</text>
      <text x="12" y="110" fill="#475569" font-size="11">reconciliation.</text>
    </g>
  </g>

  <!-- Connectors: Stage 4 -> Stage 5 -->
  <line x1="1410" y1="582" x2="1440" y2="582" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- ========================================================================= -->
  <!-- STAGE 05 — EVIDENCE RESOLUTION (SECOND MAJOR DIFFERENTIATOR) -->
  <!-- ========================================================================= -->
  <g transform="translate(1440, 172)">
    <rect x="0" y="0" width="370" height="1060" rx="4" fill="#FFFFFF" stroke="#0F172A" stroke-width="2" filter="url(#fabric-shadow)"/>
    
    <!-- Stage Header -->
    <rect x="0" y="0" width="370" height="52" fill="#1E293B" rx="4 4 0 0"/>
    <text x="14" y="33" fill="#FFFFFF" font-size="15" font-weight="700">05. EVIDENCE RESOLUTION</text>
    <rect x="252" y="14" width="104" height="24" rx="2" fill="#B45309"/>
    <text x="304" y="30" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">DIFFERENTIATOR</text>

    <!-- Pipeline Stages -->
    <g transform="translate(16, 68)">
      <text x="0" y="14" fill="#0F172A" font-size="13" font-weight="700">RESOLUTION &amp; CONFLICT PIPELINE</text>

      <!-- Step 1: Query -->
      <rect x="0" y="24" width="338" height="32" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1"/>
      <text x="12" y="45" fill="#0F172A" font-size="12" font-weight="700">QUERY</text>
      <text x="76" y="45" fill="#64748B" font-size="11">User question parsed into target entities</text>

      <line x1="169" y1="56" x2="169" y2="66" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Step 2: Entity/Context Matching -->
      <rect x="0" y="66" width="338" height="32" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1"/>
      <text x="12" y="87" fill="#0F172A" font-size="12" font-weight="700">ENTITY / CONTEXT MATCHING</text>
      <text x="210" y="87" fill="#64748B" font-size="11">Seam, Mine, Subsidiary</text>

      <line x1="169" y1="98" x2="169" y2="108" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Step 3: Attribute Linking -->
      <rect x="0" y="108" width="338" height="32" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1"/>
      <text x="12" y="129" fill="#0F172A" font-size="12" font-weight="700">ATTRIBUTE LINKING</text>
      <text x="156" y="129" fill="#64748B" font-size="11">Depth, thickness, extractable reserves</text>

      <line x1="169" y1="140" x2="169" y2="150" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Step 4: Temporal / Unit Checks -->
      <rect x="0" y="150" width="338" height="32" rx="2" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1"/>
      <text x="12" y="171" fill="#0F172A" font-size="12" font-weight="700">TEMPORAL / UNIT CHECKS</text>
      <text x="194" y="171" fill="#64748B" font-size="11">FY alignment, m vs ft, MT vs t</text>
    </g>

    <!-- Discrepancy & Conflict Detection Callout Node -->
    <g transform="translate(16, 282)">
      <rect x="0" y="0" width="338" height="364" rx="3" fill="#FFFBEB" stroke="#B45309" stroke-width="1.5"/>
      <rect x="0" y="0" width="338" height="32" fill="#B45309" rx="3 3 0 0"/>
      <text x="14" y="22" fill="#FFFFFF" font-size="12" font-weight="700" letter-spacing="0.5">DISCREPANCY DETECTION NODE</text>

      <!-- Two Source Records Entering Node -->
      <g transform="translate(14, 46)">
        <text x="0" y="14" fill="#78350F" font-size="11" font-weight="700">PARALLEL EVIDENCE SOURCES DETECTED:</text>
        
        <!-- Source Record A -->
        <rect x="0" y="24" width="150" height="54" rx="2" fill="#FFFFFF" stroke="#D97706" stroke-width="1"/>
        <text x="10" y="44" fill="#0F172A" font-size="12" font-weight="700">Report A</text>
        <text x="10" y="64" fill="#B45309" font-size="14" font-weight="800">12.4 MT</text>
        <text x="70" y="64" fill="#64748B" font-size="10">(CMPDI 2023)</text>

        <!-- Source Record B -->
        <rect x="160" y="24" width="150" height="54" rx="2" fill="#FFFFFF" stroke="#D97706" stroke-width="1"/>
        <text x="170" y="44" fill="#0F172A" font-size="12" font-weight="700">Report B</text>
        <text x="170" y="64" fill="#B45309" font-size="14" font-weight="800">11.8 MT</text>
        <text x="230" y="64" fill="#64748B" font-size="10">(Subsidiary 2024)</text>

        <!-- Convergence Arrows -->
        <line x1="75" y1="80" x2="140" y2="108" stroke="#B45309" stroke-width="1.5" marker-end="url(#arrow-amber)"/>
        <line x1="235" y1="80" x2="170" y2="108" stroke="#B45309" stroke-width="1.5" marker-end="url(#arrow-amber)"/>

        <!-- Conflict Detected Box -->
        <rect x="35" y="112" width="240" height="44" rx="3" fill="#FEF2F2" stroke="#DC2626" stroke-width="1.5"/>
        <text x="155" y="132" fill="#991B1B" font-size="13" font-weight="800" text-anchor="middle">⚠️ CONFLICT DETECTED</text>
        <text x="155" y="148" fill="#7F1D1D" font-size="10.5" text-anchor="middle">Δ = 0.6 MT variance between sources</text>

        <!-- Arrow Down to Expert Review -->
        <line x1="155" y1="158" x2="155" y2="180" stroke="#B45309" stroke-width="1.5" marker-end="url(#arrow-amber)"/>

        <!-- Expert Review / Reconciliation Box -->
        <rect x="15" y="182" width="280" height="56" rx="3" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.5"/>
        <text x="155" y="204" fill="#0F172A" font-size="13" font-weight="800" text-anchor="middle">EXPERT REVIEW / RECONCILIATION</text>
        <text x="155" y="224" fill="#334155" font-size="11" text-anchor="middle">Surfaced to Verification Queue (4-Eyes Check)</text>

        <!-- Reconciled / Handled State -->
        <rect x="15" y="250" width="280" height="44" rx="2" fill="#F1F5F9" stroke="#64748B" stroke-width="1"/>
        <text x="26" y="268" fill="#0F172A" font-size="11" font-weight="700">Deterministic Rule:</text>
        <text x="26" y="284" fill="#475569" font-size="10">Does NOT silently guess or overwrite values.</text>
      </g>
    </g>

    <!-- Technical label banner -->
    <g transform="translate(16, 674)">
      <rect x="0" y="0" width="338" height="66" rx="3" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1"/>
      <text x="169" y="28" fill="#0F172A" font-size="12" font-weight="700" text-anchor="middle">GOVERNANCE INVARIANT</text>
      <text x="169" y="48" fill="#334155" font-size="11" text-anchor="middle">“Conflicting evidence is surfaced for verification”</text>
    </g>

    <!-- Verification Queue Integration -->
    <g transform="translate(16, 762)">
      <rect x="0" y="0" width="338" height="110" rx="3" fill="#FFFFFF" stroke="#334155" stroke-width="1"/>
      <text x="14" y="24" fill="#0F172A" font-size="12" font-weight="700">HUMAN-IN-THE-LOOP CONTROLS</text>
      <text x="14" y="46" fill="#475569" font-size="11">• Status: PENDING_RECONCILIATION</text>
      <text x="14" y="66" fill="#475569" font-size="11">• Action: CMPDI Geologist approves / annotates</text>
      <text x="14" y="86" fill="#475569" font-size="11">• Immutable audit record committed</text>
    </g>
  </g>

  <!-- Connectors: Stage 5 -> Stage 6 -->
  <line x1="1810" y1="520" x2="1840" y2="520" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- ========================================================================= -->
  <!-- STAGE 06 — TRUSTED COMPUTATION & REASONING (THIRD STRONGEST) -->
  <!-- ========================================================================= -->
  <g transform="translate(1840, 172)">
    <rect x="0" y="0" width="370" height="1060" rx="4" fill="#FFFFFF" stroke="#0F172A" stroke-width="2" filter="url(#card-shadow)"/>
    
    <!-- Stage Header -->
    <rect x="0" y="0" width="370" height="52" fill="#0F172A" rx="4 4 0 0"/>
    <text x="14" y="33" fill="#FFFFFF" font-size="15" font-weight="700">06. TRUSTED COMPUTATION</text>
    <rect x="264" y="14" width="92" height="24" rx="2" fill="#334155"/>
    <text x="310" y="30" fill="#E2E8F0" font-size="11" font-weight="600" text-anchor="middle">DUAL PATH</text>

    <text x="14" y="78" fill="#64748B" font-size="12" font-weight="600">STRICT ARITHMETIC VS LANGUAGE SEPARATION</text>

    <!-- PATH A — DETERMINISTIC (SQL & Python Arithmetic) -->
    <g transform="translate(16, 94)">
      <rect x="0" y="0" width="338" height="280" rx="3" fill="#F8FAFC" stroke="#0F172A" stroke-width="1.8"/>
      <rect x="0" y="0" width="338" height="34" fill="#0F172A" rx="3 3 0 0"/>
      <text x="14" y="23" fill="#FFFFFF" font-size="13" font-weight="700" letter-spacing="0.5">PATH A — DETERMINISTIC ENGINE</text>

      <g transform="translate(14, 46)">
        <text x="0" y="18" fill="#0F172A" font-size="13" font-weight="700">PostgreSQL SQL &amp; Python Arithmetic</text>
        <text x="0" y="36" fill="#475569" font-size="11">Exact mathematical aggregation &amp; calculation:</text>

        <!-- Operation Badges -->
        <g transform="translate(0, 48)">
          <rect x="0" y="0" width="68" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="34" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">SUM</text>

          <rect x="76" y="0" width="68" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="110" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">AVG</text>

          <rect x="152" y="0" width="68" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="186" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">MIN / MAX</text>

          <rect x="228" y="0" width="76" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="266" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">YoY CHANGE</text>
        </g>

        <!-- Additional operations -->
        <g transform="translate(0, 82)">
          <rect x="0" y="0" width="94" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="47" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">RATIOS</text>

          <rect x="102" y="0" width="100" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="152" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">% CHANGE</text>

          <rect x="210" y="0" width="94" height="26" rx="2" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1"/>
          <text x="257" y="17" fill="#0F172A" font-size="11" font-weight="700" text-anchor="middle">RESERVES</text>
        </g>

        <!-- Strict Lineage Box -->
        <rect x="0" y="120" width="310" height="54" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1"/>
        <text x="10" y="140" fill="#0F172A" font-size="11" font-weight="700">Strict Mathematical Lineage:</text>
        <text x="10" y="158" fill="#475569" font-size="11">Formula + Operands + Physical Sources</text>

        <!-- Principle callout -->
        <text x="0" y="196" fill="#166534" font-size="11" font-weight="700">✓ “SQL / Python performs deterministic computation”</text>
      </g>
    </g>

    <!-- PATH B — LANGUAGE (Local LLM Explanation) -->
    <g transform="translate(16, 396)">
      <rect x="0" y="0" width="338" height="200" rx="3" fill="#F8FAFC" stroke="#64748B" stroke-width="1.5"/>
      <rect x="0" y="0" width="338" height="34" fill="#334155" rx="3 3 0 0"/>
      <text x="14" y="23" fill="#FFFFFF" font-size="13" font-weight="700" letter-spacing="0.5">PATH B — LANGUAGE REASONING</text>

      <g transform="translate(14, 46)">
        <text x="0" y="18" fill="#0F172A" font-size="13" font-weight="700">Local LLM (SmolLM2-135M / Ollama / vLLM)</text>
        <text x="0" y="38" fill="#475569" font-size="12">• Evidence-grounded explanation</text>
        <text x="0" y="58" fill="#475569" font-size="12">• Answer synthesis from structured facts</text>
        <text x="0" y="78" fill="#475569" font-size="12">• Never computes numbers inside tokens</text>

        <!-- Principle callout -->
        <rect x="0" y="94" width="310" height="38" rx="2" fill="#FFFFFF" stroke="#334155" stroke-width="1"/>
        <text x="10" y="112" fill="#0F172A" font-size="11" font-weight="700">Principle: “LLM explains evidence”</text>
        <text x="10" y="126" fill="#64748B" font-size="10">DO NOT portray LLM as the source of truth</text>
      </g>
    </g>

    <!-- Distinct Converging Arrows to Answer Assembler -->
    <!-- From Path A -->
    <path d="M 330 374 L 330 636" stroke="#0F172A" stroke-width="1.8" stroke-dasharray="4,2"/>
    <!-- From Path B -->
    <line x1="185" y1="596" x2="185" y2="636" stroke="#0F172A" stroke-width="2" marker-end="url(#arrow)"/>

    <!-- Answer Assembler Box -->
    <g transform="translate(16, 640)">
      <rect x="0" y="0" width="338" height="110" rx="3" fill="#0F172A" stroke="#0F172A" stroke-width="1"/>
      <text x="169" y="30" fill="#FFFFFF" font-size="15" font-weight="800" text-anchor="middle">ANSWER ASSEMBLER</text>
      <text x="169" y="52" fill="#E2E8F0" font-size="12" text-anchor="middle">Merges Deterministic Math + Language Context</text>
      <line x1="20" y1="64" x2="318" y2="64" stroke="#334155" stroke-width="1"/>
      <text x="169" y="84" fill="#94A3B8" font-size="11" text-anchor="middle">Enforces schema-constrained grounding checks</text>
      <text x="169" y="100" fill="#94A3B8" font-size="11" text-anchor="middle">Refuses if evidence insufficient (Anti-Hallucination)</text>
    </g>

    <!-- Anti-Hallucination Guardrail Note -->
    <g transform="translate(16, 768)">
      <rect x="0" y="0" width="338" height="92" rx="3" fill="#FEF2F2" stroke="#EF4444" stroke-width="1"/>
      <text x="12" y="24" fill="#991B1B" font-size="11" font-weight="700">HALLUCINATION DEFENCE INVARIANT</text>
      <text x="12" y="44" fill="#7F1D1D" font-size="11">If evidence cannot be verified from physical records:</text>
      <text x="12" y="62" fill="#7F1D1D" font-size="11" font-weight="700">System returns refusal: “Evidence not found”</text>
      <text x="12" y="80" fill="#7F1D1D" font-size="10">Zero statistical extrapolation without source data.</text>
    </g>
  </g>

  <!-- Connectors: Stage 6 -> Stage 7 -->
  <line x1="2210" y1="695" x2="2240" y2="695" stroke="#1E293B" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- ========================================================================= -->
  <!-- STAGE 07 — TRACEABLE OUTPUT -->
  <!-- ========================================================================= -->
  <g transform="translate(2240, 172)">
    <rect x="0" y="0" width="280" height="1060" rx="4" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.8" filter="url(#card-shadow)"/>
    
    <!-- Stage Header -->
    <rect x="0" y="0" width="280" height="52" fill="#0F172A" rx="4 4 0 0"/>
    <text x="14" y="33" fill="#FFFFFF" font-size="15" font-weight="700">07. TRACEABLE OUTPUT</text>
    <rect x="210" y="14" width="56" height="24" rx="2" fill="#166534"/>
    <text x="238" y="30" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">VERIFIED</text>

    <!-- Main Output Box -->
    <g transform="translate(14, 72)">
      <rect x="0" y="0" width="252" height="74" rx="3" fill="#F1F5F9" stroke="#0F172A" stroke-width="1.5"/>
      <text x="126" y="28" fill="#0F172A" font-size="13" font-weight="800" text-anchor="middle">EVIDENCE-BACKED</text>
      <text x="126" y="48" fill="#0F172A" font-size="13" font-weight="800" text-anchor="middle">ANSWER / REPORT</text>
      <text x="126" y="66" fill="#475569" font-size="11" text-anchor="middle">Parliamentary / Mine Briefs</text>
    </g>

    <!-- Provenance Drill-Down Tree -->
    <g transform="translate(14, 164)">
      <text x="0" y="14" fill="#64748B" font-size="11" font-weight="700">PROVENANCE DRILL-DOWN:</text>

      <!-- Level 1: Answer -->
      <g transform="translate(0, 26)">
        <rect x="0" y="0" width="252" height="42" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.2"/>
        <text x="12" y="26" fill="#0F172A" font-size="13" font-weight="700">1. Answer</text>
        <text x="120" y="26" fill="#64748B" font-size="11">Textual synthesis</text>
      </g>

      <line x1="126" y1="68" x2="126" y2="82" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Level 2: Supporting Evidence -->
      <g transform="translate(0, 82)">
        <rect x="0" y="0" width="252" height="42" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.2"/>
        <text x="12" y="26" fill="#0F172A" font-size="13" font-weight="700">2. Supporting Evidence</text>
        <text x="170" y="26" fill="#64748B" font-size="11">Tuple/Row</text>
      </g>

      <line x1="126" y1="124" x2="126" y2="138" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Level 3: Document -->
      <g transform="translate(0, 138)">
        <rect x="0" y="0" width="252" height="42" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.2"/>
        <text x="12" y="26" fill="#0F172A" font-size="13" font-weight="700">3. Document</text>
        <text x="110" y="26" fill="#64748B" font-size="11">Hash &amp; SHA-256</text>
      </g>

      <line x1="126" y1="180" x2="126" y2="194" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Level 4: Page / Table / Cell -->
      <g transform="translate(0, 194)">
        <rect x="0" y="0" width="252" height="54" rx="2" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.5"/>
        <text x="12" y="24" fill="#0F172A" font-size="12" font-weight="700">4. Page / Table / Cell / Visual</text>
        <text x="12" y="44" fill="#475569" font-size="11">Exact physical coordinate &amp; BBox</text>
      </g>

      <line x1="126" y1="248" x2="126" y2="262" stroke="#0F172A" stroke-width="1.5" marker-end="url(#arrow)"/>

      <!-- Level 5: Calculation / Formula -->
      <g transform="translate(0, 262)">
        <rect x="0" y="0" width="252" height="54" rx="2" fill="#F8FAFC" stroke="#0F172A" stroke-width="1.5"/>
        <text x="12" y="24" fill="#0F172A" font-size="12" font-weight="700">5. Calculation / Formula</text>
        <text x="12" y="44" fill="#475569" font-size="11">Operands &amp; SQL script traceable</text>
      </g>
    </g>

    <!-- Citation + Provenance + Audit Banner -->
    <g transform="translate(14, 520)">
      <rect x="0" y="0" width="252" height="74" rx="3" fill="#0F172A" stroke="#0F172A" stroke-width="1"/>
      <text x="126" y="26" fill="#F8FAFC" font-size="11" font-weight="700" text-anchor="middle">TRACEABILITY GUARANTEE</text>
      <text x="126" y="46" fill="#FFFFFF" font-size="11" font-weight="700" text-anchor="middle">CITATION + PROVENANCE</text>
      <text x="126" y="62" fill="#94A3B8" font-size="11" font-weight="600" text-anchor="middle">+ AUDIT TRAIL</text>
    </g>

    <!-- Engineering Shield / Badge Icon at Far Right -->
    <g transform="translate(14, 616)">
      <rect x="0" y="0" width="252" height="110" rx="4" fill="#F0FDF4" stroke="#166534" stroke-width="1.5"/>
      <!-- Technical Shield SVG Path -->
      <path d="M 126 20 L 150 30 L 150 50 Q 150 68 126 78 Q 102 68 102 50 L 102 30 Z" fill="#166534"/>
      <!-- Checkmark -->
      <path d="M 117 48 L 124 55 L 137 40" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/>
      <text x="126" y="98" fill="#166534" font-size="12" font-weight="800" text-anchor="middle" letter-spacing="0.5">TRACEABLE OUTPUT</text>
    </g>

    <!-- Formats Rendered -->
    <g transform="translate(14, 746)">
      <rect x="0" y="0" width="252" height="76" rx="3" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1"/>
      <text x="12" y="22" fill="#0F172A" font-size="11" font-weight="700">EXPORT FORMATS</text>
      <text x="12" y="42" fill="#475569" font-size="11">• DOCX (python-docx report brief)</text>
      <text x="12" y="60" fill="#475569" font-size="11">• JSON structured API response</text>
    </g>
  </g>

  <!-- ========================================================================= -->
  <!-- BOTTOM OF SLIDE — CROSS-CUTTING GOVERNANCE LAYER -->
  <!-- ========================================================================= -->
  <g transform="translate(40, 1260)">
    <rect x="0" y="0" width="2520" height="96" rx="4" fill="#F8FAFC" stroke="#0F172A" stroke-width="1.8" filter="url(#card-shadow)"/>
    
    <!-- Title Badge on the Left -->
    <rect x="0" y="0" width="380" height="96" rx="4 0 0 4" fill="#0F172A"/>
    <text x="24" y="40" fill="#FFFFFF" font-size="14" font-weight="800" letter-spacing="0.5">CROSS-CUTTING GOVERNANCE</text>
    <text x="24" y="66" fill="#94A3B8" font-size="13" font-weight="600">PROVENANCE + AUDIT + HUMAN VERIFICATION</text>

    <!-- 6 Governance Items Spanning Width -->
    <g transform="translate(400, 18)">
      <!-- Item 1 -->
      <g transform="translate(0, 0)">
        <rect x="0" y="0" width="310" height="60" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="14" y="24" fill="#0F172A" font-size="13" font-weight="700">Evidence Access</text>
        <text x="14" y="46" fill="#64748B" font-size="11">Actor, Role, Org-Scope, SHA-256</text>
      </g>

      <!-- Item 2 -->
      <g transform="translate(340, 0)">
        <rect x="0" y="0" width="310" height="60" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="14" y="24" fill="#0F172A" font-size="13" font-weight="700">Query Events</text>
        <text x="14" y="46" fill="#64748B" font-size="11">Search terms, retrieved candidate IDs</text>
      </g>

      <!-- Item 3 -->
      <g transform="translate(680, 0)">
        <rect x="0" y="0" width="310" height="60" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="14" y="24" fill="#0F172A" font-size="13" font-weight="700">Calculations Trace</text>
        <text x="14" y="46" fill="#64748B" font-size="11">Operands, formulas, SQL execution log</text>
      </g>

      <!-- Item 4 -->
      <g transform="translate(1020, 0)">
        <rect x="0" y="0" width="310" height="60" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="14" y="24" fill="#0F172A" font-size="13" font-weight="700">Reconciliation Log</text>
        <text x="14" y="46" fill="#64748B" font-size="11">Conflicts, candidate source deltas</text>
      </g>

      <!-- Item 5 -->
      <g transform="translate(1360, 0)">
        <rect x="0" y="0" width="310" height="60" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="14" y="24" fill="#0F172A" font-size="13" font-weight="700">Human Verification</text>
        <text x="14" y="46" fill="#64748B" font-size="11">4-Eyes statutory signoff &amp; remarks</text>
      </g>

      <!-- Item 6 -->
      <g transform="translate(1700, 0)">
        <rect x="0" y="0" width="380" height="60" rx="2" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>
        <text x="14" y="24" fill="#0F172A" font-size="13" font-weight="700">Report Generation Audit</text>
        <text x="14" y="46" fill="#64748B" font-size="11">Immutable DOCX versioning &amp; exports</text>
      </g>
    </g>
  </g>

  <!-- Vertical dashed connections from major stages to Governance layer -->
  <line x1="180" y1="1232" x2="180" y2="1260" stroke="#64748B" stroke-width="1.5" stroke-dasharray="3,3"/>
  <line x1="505" y1="1232" x2="505" y2="1260" stroke="#64748B" stroke-width="1.5" stroke-dasharray="3,3"/>
  <line x1="905" y1="1232" x2="905" y2="1260" stroke="#64748B" stroke-width="1.5" stroke-dasharray="3,3"/>
  <line x1="1625" y1="1232" x2="1625" y2="1260" stroke="#64748B" stroke-width="1.5" stroke-dasharray="3,3"/>
  <line x1="2025" y1="1232" x2="2025" y2="1260" stroke="#64748B" stroke-width="1.5" stroke-dasharray="3,3"/>
  <line x1="2380" y1="1232" x2="2380" y2="1260" stroke="#64748B" stroke-width="1.5" stroke-dasharray="3,3"/>

  <!-- ========================================================================= -->
  <!-- FOOTER: STATEMENT & IMPLEMENTATION STACK -->
  <!-- ========================================================================= -->
  <g transform="translate(40, 1376)">
    <!-- Professional Core Statement (Bottom Left/Center) -->
    <rect x="0" y="0" width="1680" height="66" rx="3" fill="#FFFFFF" stroke="#334155" stroke-width="1"/>
    <text x="24" y="28" fill="#0F172A" font-size="14" font-weight="800" letter-spacing="1">ARCHITECTURAL IMPERATIVE:</text>
    <text x="270" y="28" fill="#0F172A" font-size="14" font-weight="700">RETRIEVE → RESOLVE → RECONCILE → COMPUTE → TRACE → ANSWER</text>
    <text x="24" y="52" fill="#475569" font-size="13" font-style="italic">“Retrieval is only the beginning. Koyla resolves evidence before it answers.”</text>

    <!-- Implementation Stack (Bottom Right - unobtrusive) -->
    <rect x="1710" y="0" width="810" height="66" rx="3" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1"/>
    <text x="1730" y="26" fill="#64748B" font-size="11" font-weight="700">LOCAL-FIRST DEPLOYMENT STACK</text>
    <text x="1730" y="50" fill="#0F172A" font-size="13" font-weight="700">PostgreSQL 16 | pgvector | Python 3.11+ | SQL | Local Transformers | Docker Compose</text>
  </g>

</svg>'''
    return svg

def build_sih_slide_svg(diagram_svg_content):
    # Standard 16:9 Presentation Slide (3840 x 2160 px)
    # Left ~1/5th to 1/4th (approx 740 px wide) has the SIH template text box with Title & Content
    # Right ~4/5th (approx 2970 px wide) hosts the 7-stage architecture diagram!
    
    slide_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3840 2160" width="3840" height="2160" style="background:#FFFFFF; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <filter id="slide-card-shadow" x="-1%" y="-1%" width="102%" height="102%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0F172A" flood-opacity="0.08"/>
    </filter>
  </defs>

  <!-- Slide Canvas Background -->
  <rect width="3840" height="2160" fill="#FFFFFF"/>

  <!-- ==================== TOP SLIDE HEADER (SIH STANDARD TEMPLATE) ==================== -->
  <g transform="translate(60, 40)">
    <!-- Top Bar -->
    <rect x="0" y="0" width="3720" height="130" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.5" rx="4"/>
    
    <!-- Left: Team Logo / Organization Badge -->
    <rect x="24" y="20" width="220" height="90" rx="4" fill="#0F172A"/>
    <text x="134" y="62" fill="#FFFFFF" font-size="28" font-weight="800" text-anchor="middle" letter-spacing="2">KOYLA</text>
    <text x="134" y="90" fill="#94A3B8" font-size="13" font-weight="600" text-anchor="middle">CIL / CMPDI — 26023</text>

    <!-- Center: Main Slide Header -->
    <text x="1860" y="66" fill="#0F172A" font-size="44" font-weight="800" text-anchor="middle" letter-spacing="1">TECHNICAL APPROACH</text>
    <text x="1860" y="102" fill="#475569" font-size="20" font-weight="600" text-anchor="middle">SYSTEM ARCHITECTURE &amp; EVIDENCE-CENTRIC WORKFLOW</text>

    <!-- Right: Smart India Hackathon Badge -->
    <g transform="translate(3320, 16)">
      <rect x="0" y="0" width="376" height="98" rx="4" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1"/>
      <!-- Tricolor indicator -->
      <rect x="20" y="19" width="8" height="20" fill="#FF9933" rx="1"/>
      <rect x="20" y="39" width="8" height="20" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="0.5" rx="1"/>
      <rect x="20" y="59" width="8" height="20" fill="#138808" rx="1"/>
      <text x="44" y="50" fill="#0F172A" font-size="18" font-weight="800">SMART INDIA HACKATHON</text>
      <text x="44" y="74" fill="#1E3A8A" font-size="18" font-weight="800">2026</text>
    </g>
  </g>

  <!-- ==================== LEFT 1/5TH (SIH TEMPLATE CONTENT BOX) ==================== -->
  <!-- Width: 720 px (x: 60 to 780) -->
  <g transform="translate(60, 190)">
    <!-- Container Box styled like the official SIH template -->
    <rect x="0" y="0" width="720" height="1860" rx="4" fill="#FFFFFF" stroke="#2563EB" stroke-width="2.5" filter="url(#slide-card-shadow)"/>
    
    <!-- Title Header Box -->
    <rect x="0" y="0" width="720" height="70" fill="#1E3A8A" rx="4 4 0 0"/>
    <text x="24" y="44" fill="#FFFFFF" font-size="22" font-weight="800">System Architecture &amp; Workflow</text>

    <!-- Content Body -->
    <g transform="translate(30, 96)">
      <!-- Lead Statement -->
      <text x="0" y="24" fill="#0F172A" font-size="19" font-weight="800">Architectural Paradigm:</text>
      <text x="0" y="54" fill="#1E293B" font-size="16" font-weight="600">Strictly Non-Layered Evidence Fabric</text>
      <text x="0" y="80" fill="#64748B" font-size="14">Built for SIH Problem Statement 26023</text>

      <line x1="0" y1="104" x2="660" y2="104" stroke="#E2E8F0" stroke-width="1.5"/>

      <!-- Core Differentiator 1 -->
      <g transform="translate(0, 126)">
        <rect x="0" y="0" width="660" height="160" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <rect x="12" y="16" width="6" height="128" fill="#1E3A8A" rx="1"/>
        <text x="32" y="36" fill="#0F172A" font-size="17" font-weight="700">1. Evidence-Centric (Not Generic RAG)</text>
        <text x="32" y="64" fill="#334155" font-size="14">• Avoids generic PDF→Vector→LLM pipelines.</text>
        <text x="32" y="88" fill="#334155" font-size="14">• Normalizes heterogeneous records into a typed</text>
        <text x="32" y="112" fill="#334155" font-size="14">  central Evidence Fabric in PostgreSQL 16.</text>
        <text x="32" y="136" fill="#475569" font-size="13">• Physical bounding boxes &amp; cell coordinates.</text>
      </g>

      <!-- Core Differentiator 2 -->
      <g transform="translate(0, 310)">
        <rect x="0" y="0" width="660" height="174" rx="3" fill="#FFFBEB" stroke="#B45309" stroke-width="1.2"/>
        <rect x="12" y="16" width="6" height="142" fill="#B45309" rx="1"/>
        <text x="32" y="36" fill="#78350F" font-size="17" font-weight="700">2. Discrepancy &amp; Conflict Resolution</text>
        <text x="32" y="64" fill="#92400E" font-size="14">• Cross-document reconciliation node detects</text>
        <text x="32" y="88" fill="#92400E" font-size="14">  numerical &amp; date variances across reports.</text>
        <text x="32" y="112" fill="#92400E" font-size="14">• Surfaced to 4-Eyes Human Verification queue</text>
        <text x="32" y="136" fill="#92400E" font-size="14">  instead of hallucinating or silently guessing.</text>
        <text x="32" y="156" fill="#B45309" font-size="13" font-weight="600">✓ Invariant: Zero silent overwrites.</text>
      </g>

      <!-- Core Differentiator 3 -->
      <g transform="translate(0, 508)">
        <rect x="0" y="0" width="660" height="160" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <rect x="12" y="16" width="6" height="128" fill="#1E3A8A" rx="1"/>
        <text x="32" y="36" fill="#0F172A" font-size="17" font-weight="700">3. Deterministic Arithmetic Engine</text>
        <text x="32" y="64" fill="#334155" font-size="14">• Strict dual-path reasoning architecture.</text>
        <text x="32" y="88" fill="#334155" font-size="14">• SQL/Python handles SUM, AVG, YoY math.</text>
        <text x="32" y="112" fill="#334155" font-size="14">• Local LLM is restricted to language explanation.</text>
        <text x="32" y="136" fill="#166534" font-size="13" font-weight="600">✓ Invariant: LLM is never the source of truth.</text>
      </g>

      <!-- Core Differentiator 4 -->
      <g transform="translate(0, 692)">
        <rect x="0" y="0" width="660" height="150" rx="3" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="1.2"/>
        <rect x="12" y="16" width="6" height="118" fill="#1E3A8A" rx="1"/>
        <text x="32" y="36" fill="#0F172A" font-size="17" font-weight="700">4. Complete Audit Lineage</text>
        <text x="32" y="64" fill="#334155" font-size="14">• Every answer links directly down to physical</text>
        <text x="32" y="88" fill="#334155" font-size="14">  document, page, table, cell, and formula.</text>
        <text x="32" y="112" fill="#334155" font-size="14">• Immutable audit log (`audit_events` table).</text>
        <text x="32" y="132" fill="#475569" font-size="13">• Defensible for statutory coal reporting.</text>
      </g>

      <!-- Core Differentiator 5 -->
      <g transform="translate(0, 866)">
        <rect x="0" y="0" width="660" height="144" rx="3" fill="#F0FDF4" stroke="#166534" stroke-width="1.2"/>
        <rect x="12" y="16" width="6" height="112" fill="#166534" rx="1"/>
        <text x="32" y="36" fill="#166534" font-size="17" font-weight="700">5. 100% On-Premise Air-Gapped</text>
        <text x="32" y="64" fill="#14532D" font-size="14">• PostgreSQL 16 + pgvector containerized.</text>
        <text x="32" y="88" fill="#14532D" font-size="14">• Local HuggingFace transformers (BGE + TinyBERT).</text>
        <text x="32" y="112" fill="#14532D" font-size="14">• Zero runtime external cloud dependencies.</text>
        <text x="32" y="130" fill="#15803D" font-size="13" font-weight="600">✓ Meets sovereign CIL security criteria.</text>
      </g>

      <!-- Bottom Reference Box -->
      <g transform="translate(0, 1034)">
        <rect x="0" y="0" width="660" height="120" rx="3" fill="#0F172A"/>
        <text x="24" y="32" fill="#FFFFFF" font-size="15" font-weight="800">EXECUTION WORKFLOW SUMMARY</text>
        <text x="24" y="60" fill="#94A3B8" font-size="13">Ingest &amp; Hash → Multimodal Extraction →</text>
        <text x="24" y="82" fill="#94A3B8" font-size="13">Evidence Fabric → Hybrid Retrieval → Resolve &amp; </text>
        <text x="24" y="104" fill="#38BDF8" font-size="13" font-weight="700">Reconcile → Deterministic Compute → Traceable Answer</text>
      </g>
    </g>
  </g>

  <!-- ==================== RIGHT 4/5TH (ARCHITECTURE DIAGRAM CANVAS) ==================== -->
  <!-- Positioned from x: 800 to 3780 (Width: 2980, Height: 1860) -->
  <g transform="translate(800, 190)">
    <!-- Outer framing container for the technical diagram -->
    <rect x="0" y="0" width="2980" height="1860" rx="4" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#slide-card-shadow)"/>
    
    <!-- Technical Title Header -->
    <rect x="0" y="0" width="2980" height="52" fill="#F1F5F9" rx="4 4 0 0"/>
    <text x="28" y="34" fill="#0F172A" font-size="17" font-weight="800" letter-spacing="0.5">PROCESS FLOW ARCHITECTURE — 7-STAGE EVIDENCE LIFECYCLE</text>
    <rect x="2680" y="12" width="260" height="28" rx="2" fill="#0F172A"/>
    <text x="2810" y="31" fill="#FFFFFF" font-size="12" font-weight="700" text-anchor="middle">HIGH-VISIBILITY VIEW</text>

    <!-- Embedded Scaled Diagram -->
    <g transform="translate(24, 76) scale(1.125, 1.125)">
      {diagram_svg_content}
    </g>
  </g>

  <!-- ==================== BOTTOM SLIDE FOOTER ==================== -->
  <g transform="translate(60, 2080)">
    <rect x="0" y="0" width="3720" height="46" fill="#1E3A8A" rx="2"/>
    <text x="32" y="30" fill="#FFFFFF" font-size="15" font-weight="600">@SIH Idea submission- Template | Ministry of Coal &amp; Coal India Limited | Problem Statement 26023</text>
    <text x="3688" y="30" fill="#93C5FD" font-size="15" font-weight="700" text-anchor="end">KOYLA — AI-POWERED GEOLOGICAL, MINING &amp; REPORTING INTELLIGENCE PLATFORM</text>
  </g>
</svg>'''
    return slide_svg

def create_presentation_pptx(standalone_png_path, slide_png_path, output_pptx_path):
    prs = pptx.Presentation()
    # 16:9 Widescreen dimensions: 13.333 x 7.5 inches
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ==================== SLIDE 1: Complete SIH Technical Approach Slide ====================
    slide1 = prs.slides.add_slide(blank_layout)
    if os.path.exists(slide_png_path):
        slide1.shapes.add_picture(slide_png_path, 0, 0, Inches(13.333), Inches(7.5))

    # ==================== SLIDE 2: Standalone Diagram on Right 4/5th with Left 1/5th Editable Box ====================
    slide2 = prs.slides.add_slide(blank_layout)
    
    # Add Top Header to Slide 2
    header_box = slide2.shapes.add_textbox(Inches(0.4), Inches(0.2), Inches(12.5), Inches(0.8))
    tf = header_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "TECHNICAL APPROACH — KOYLA EVIDENCE INTELLIGENCE ARCHITECTURE"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    p2 = tf.add_paragraph()
    p2.text = "CIL / CMPDI — Problem Statement 26023 | 7-Stage Left-to-Right Evidence Flow Architecture"
    p2.font.size = Pt(11)
    p2.font.color.rgb = RGBColor(71, 85, 105)

    # Left 1/5th: Editable SIH Template Text Box
    left_x = Inches(0.4)
    left_y = Inches(1.1)
    left_w = Inches(2.6)
    left_h = Inches(5.9)
    
    # Left Box Border Shape
    rect = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_x, left_y, left_w, left_h)
    rect.fill.solid()
    rect.fill.fore_color.rgb = RGBColor(248, 250, 252)
    rect.line.color.rgb = RGBColor(37, 99, 235)
    rect.line.width = Pt(1.5)

    # Left Box Text Frame
    tb = slide2.shapes.add_textbox(left_x + Inches(0.1), left_y + Inches(0.1), left_w - Inches(0.2), left_h - Inches(0.2))
    tf2 = tb.text_frame
    tf2.word_wrap = True
    
    p = tf2.paragraphs[0]
    p.text = "Title: System Architecture & Workflow"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(30, 58, 138)
    
    bullets = [
        ("Core Philosophy:", "Evidence-Centric Architecture (Not generic RAG)"),
        ("Stage 01-02:", "Multimodal Ingestion (PDF, Scans, Tables, Maps, Boreholes)"),
        ("Stage 03 (Core):", "Koyla Evidence Fabric in PostgreSQL 16 + pgvector"),
        ("Stage 04:", "Hybrid BM25 + Vector + Cross-Encoder Re-ranking"),
        ("Stage 05 (Diff):", "Discrepancy & Conflict Resolution Node with 4-Eyes Review"),
        ("Stage 06 (Math):", "Deterministic SQL/Python (SUM, AVG, YoY) vs Local LLM explanation"),
        ("Stage 07:", "Traceable Output down to Page, Table, Cell & Formula"),
        ("Governance:", "Immutable Audit Trail & Physical Source Provenance")
    ]
    
    for title, desc in bullets:
        p_b = tf2.add_paragraph()
        p_b.text = f"• {title} {desc}"
        p_b.font.size = Pt(9.5)
        p_b.font.color.rgb = RGBColor(15, 23, 42)
        p_b.space_before = Pt(3)

    # Right 4/5th: The Standalone Architecture Diagram Picture
    right_x = Inches(3.15)
    right_y = Inches(1.1)
    right_w = Inches(9.8)
    right_h = Inches(5.9)
    if os.path.exists(standalone_png_path):
        slide2.shapes.add_picture(standalone_png_path, right_x, right_y, right_w, right_h)

    # ==================== SLIDE 3: Deep Technical Defense & Architectural Justification ====================
    slide3 = prs.slides.add_slide(blank_layout)
    header_box3 = slide3.shapes.add_textbox(Inches(0.4), Inches(0.2), Inches(12.5), Inches(0.8))
    tf3 = header_box3.text_frame
    tf3.word_wrap = True
    p3 = tf3.paragraphs[0]
    p3.text = "ARCHITECTURAL JUSTIFICATION & DEFENSE — KOYLA EVIDENCE PRINCIPLES"
    p3.font.size = Pt(20)
    p3.font.bold = True
    p3.font.color.rgb = RGBColor(15, 23, 42)

    # 3 Summary Cards
    col_w = Inches(3.9)
    col_h = Inches(6.0)
    col_y = Inches(1.1)
    
    # Card 1: Evidence Fabric vs Generic Vector Store
    c1 = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.4), col_y, col_w, col_h)
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(248, 250, 252)
    c1.line.color.rgb = RGBColor(15, 23, 42)
    tb_c1 = slide3.shapes.add_textbox(Inches(0.5), col_y + Inches(0.1), col_w - Inches(0.2), col_h - Inches(0.2))
    tfc1 = tb_c1.text_frame
    tfc1.word_wrap = True
    p = tfc1.paragraphs[0]
    p.text = "1. Evidence Fabric vs Vector Store"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    points1 = [
        "Generic RAG splits documents into arbitrary text chunks, losing tabular structure and spatial bounding boxes.",
        "Koyla stores 8 distinct structured evidence objects in PostgreSQL 16 (Documents, Pages, Chunks, Tables, Rows, Fields, Visuals, Metadata).",
        "Every single metric retains physical coordinates: Document SHA-256, page number, table ID, row index, and bounding box.",
        "Result: Zero lost table geometry or ambiguous seam thicknesses."
    ]
    for pt in points1:
        p_sub = tfc1.add_paragraph()
        p_sub.text = f"• {pt}"
        p_sub.font.size = Pt(10)
        p_sub.space_before = Pt(8)

    # Card 2: Discrepancy & Conflict Resolution
    c2 = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(4.7), col_y, col_w, col_h)
    c2.fill.solid()
    c2.fill.fore_color.rgb = RGBColor(255, 251, 235)
    c2.line.color.rgb = RGBColor(180, 83, 9)
    tb_c2 = slide3.shapes.add_textbox(Inches(4.8), col_y + Inches(0.1), col_w - Inches(0.2), col_h - Inches(0.2))
    tfc2 = tb_c2.text_frame
    tfc2.word_wrap = True
    p = tfc2.paragraphs[0]
    p.text = "2. Discrepancy & Conflict Resolution"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = RGBColor(180, 83, 9)
    points2 = [
        "Government and geological reports often disagree across publication years, exploration phases, and subsidiary filings.",
        "Koyla's Resolution Node detects numerical, temporal, and unit discrepancies automatically (e.g., CMPDI 12.4 MT vs Subsidiary 11.8 MT).",
        "Instead of randomly picking or averaging values, the system flags 'CONFLICT DETECTED'.",
        "Pushed to the Human Verification Queue for 4-Eyes statutory review with immutable audit logging."
    ]
    for pt in points2:
        p_sub = tfc2.add_paragraph()
        p_sub.text = f"• {pt}"
        p_sub.font.size = Pt(10)
        p_sub.space_before = Pt(8)

    # Card 3: Deterministic Arithmetic vs LLM Hallucination
    c3 = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(9.0), col_y, col_w, col_h)
    c3.fill.solid()
    c3.fill.fore_color.rgb = RGBColor(240, 253, 244)
    c3.line.color.rgb = RGBColor(22, 101, 52)
    tb_c3 = slide3.shapes.add_textbox(Inches(9.1), col_y + Inches(0.1), col_w - Inches(0.2), col_h - Inches(0.2))
    tfc3 = tb_c3.text_frame
    tfc3.word_wrap = True
    p = tfc3.paragraphs[0]
    p.text = "3. Deterministic Arithmetic Engine"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = RGBColor(22, 101, 52)
    points3 = [
        "LLMs are notorious for probabilistic token math errors in production, sum, and reserve calculations.",
        "Koyla enforces strict path separation: SQL & Python execute all SUM, AVG, MIN/MAX, YoY change, and reserve ratios.",
        "The Local LLM (SmolLM2-135M / Ollama) is used solely to generate readable linguistic explanations of the verified math.",
        "Complete traceability: Formula + Operands + Physical Evidence Sources recorded in the immutable audit trail."
    ]
    for pt in points3:
        p_sub = tfc3.add_paragraph()
        p_sub.text = f"• {pt}"
        p_sub.font.size = Pt(10)
        p_sub.space_before = Pt(8)

    # Save PPTX
    prs.save(output_pptx_path)
    print(f"PowerPoint presentation generated at: {output_pptx_path}")

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "docs", "infographics")
    os.makedirs(output_dir, exist_ok=True)

    # Also target the brain artifact directory so it's directly accessible
    artifact_dir = r"C:\Users\aksha\.gemini\antigravity\brain\b33bd920-4cff-4ebe-9ba3-00c945d48902"

    # 1. Generate standalone diagram SVG
    print("Generating standalone diagram SVG...")
    standalone_svg = build_standalone_diagram_svg()
    standalone_svg_path = os.path.join(output_dir, "koyla_architecture_diagram.svg")
    with open(standalone_svg_path, "w", encoding="utf-8") as f:
        f.write(standalone_svg)
    print(f"Saved: {standalone_svg_path}")

    # Extract inner content for embedding into presentation slide
    inner_svg_start = standalone_svg.find("<defs>")
    inner_svg_end = standalone_svg.rfind("</svg>")
    inner_content = standalone_svg[inner_svg_start:inner_svg_end]

    # 2. Generate complete SIH presentation slide SVG
    print("Generating complete SIH 16:9 presentation slide SVG...")
    slide_svg = build_sih_slide_svg(inner_content)
    slide_svg_path = os.path.join(output_dir, "koyla_sih_presentation_slide.svg")
    with open(slide_svg_path, "w", encoding="utf-8") as f:
        f.write(slide_svg)
    print(f"Saved: {slide_svg_path}")

    # 3. Render SVGs to ultra-high-resolution PNGs via Headless Chrome
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    # Render Standalone Diagram (2600 x 1560 -> high-res 4K)
    standalone_html_path = os.path.join(output_dir, "view_diagram.html")
    with open(standalone_html_path, "w", encoding="utf-8") as f:
        f.write(f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{margin:0;padding:0;background:#FFFFFF;display:flex;justify-content:center;align-items:center;}}svg{{width:2600px;height:1560px;display:block;}}</style></head><body>{standalone_svg}</body></html>''')

    standalone_png_path = os.path.join(output_dir, "koyla_architecture_diagram_4k.png")
    print("Rendering standalone diagram to 4K PNG...")
    cmd1 = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        f"--screenshot={standalone_png_path}",
        "--window-size=2600,1560",
        standalone_html_path
    ]
    subprocess.run(cmd1, check=True)
    print(f"Rendered: {standalone_png_path} ({os.path.getsize(standalone_png_path)} bytes)")

    # Render SIH Presentation Slide (3840 x 2160 -> true 4K 16:9 slide)
    slide_html_path = os.path.join(output_dir, "view_slide.html")
    with open(slide_html_path, "w", encoding="utf-8") as f:
        f.write(f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{margin:0;padding:0;background:#FFFFFF;display:flex;justify-content:center;align-items:center;}}svg{{width:3840px;height:2160px;display:block;}}</style></head><body>{slide_svg}</body></html>''')

    slide_png_path = os.path.join(output_dir, "koyla_sih_presentation_slide_4k.png")
    print("Rendering SIH slide to 4K PNG...")
    cmd2 = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        f"--screenshot={slide_png_path}",
        "--window-size=3840,2160",
        slide_html_path
    ]
    subprocess.run(cmd2, check=True)
    print(f"Rendered: {slide_png_path} ({os.path.getsize(slide_png_path)} bytes)")

    # 4. Generate native PowerPoint presentation
    pptx_path = os.path.join(output_dir, "KOYLA_SIH2026_Technical_Approach.pptx")
    create_presentation_pptx(standalone_png_path, slide_png_path, pptx_path)

    # 5. Copy artifacts to brain conversation directory for embedding
    shutil.copy2(standalone_png_path, os.path.join(artifact_dir, "koyla_architecture_diagram_4k.png"))
    shutil.copy2(slide_png_path, os.path.join(artifact_dir, "koyla_sih_presentation_slide_4k.png"))
    shutil.copy2(pptx_path, os.path.join(artifact_dir, "KOYLA_SIH2026_Technical_Approach.pptx"))
    print(f"Copied artifacts to {artifact_dir}")

    print("ALL ARTIFACTS GENERATED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
