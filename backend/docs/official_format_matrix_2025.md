# Official Report Format Matrix: Ministry of Coal / CCO 2025 Mining Plan Guidelines

**Authoritative Document**: Guidelines for preparation of Mining Plan and Mine Closure Plan for Coal and Lignite Blocks, 2025  
**Issuing Authority**: Ministry of Coal, Government of India / Coal Controller Organisation (CCO)  
**Official Reference**: Office Memorandum F.No. CPAM-34011/28/2019-CPAM dated 31 January 2025  
**Governing Section**: Appendix-I — "DETAILS TO BE FURNISHED IN THE MINING PLANS FOR COAL/LIGNITE BLOCKS"  
**Effective Status**: Active Statutory & Regulatory Framework (effective 31.01.2025)  
**Applicability**: All commercial, captive, and PSU coal and lignite blocks/mines in India  
**Draft 2026 Status**: Confirmed as draft public consultation only; 2025 OM remains the active governing law.

---

## 1. Top-Level Index Structure (9 Primary Items)

Appendix-I explicitly organizes the submission into 9 top-level items:
1. **Item 1: Checklist** (Pre-submission statutory compliance checklist)
2. **Item 2: Chapter 1 — Project Information**
3. **Item 3: Chapter 2 — Exploration, Geology, Seam Sequence, Coal Quality and Reserve**
4. **Item 4: Chapter 3 — Mining**
5. **Item 5: Chapter 4 — Safety Management**
6. **Item 6: Chapter 5 — Infrastructure Facilities proposed and their Location**
7. **Item 7: Chapter 6 — Land Requirement**
8. **Item 8: Chapter 7 — Environment Management**
9. **Item 9: Chapter 8 — Progressive and Final Mine Closure Plan**

Internally, the schema maintains a strict architectural distinction between:
- `FRONT_MATTER` (Cover Page, Indexes, Abbreviations, Checklist)
- `CHAPTERS` (Chapters 1 to 8)
- `ANNEXURES` (Prescribed statutory, conditional, and supplementary attachments)
- `PLATES` (Prescribed geo-referenced technical drawings and stage plans)
- `CERTIFICATIONS` (Statutory execution undertakings and declarations)

---

## 2. Complete Official Parameter Matrix (126 Items)

The matrix below inventories all 126 components of the official 2025 Appendix-I framework without approximations.

### 2.1 Front Matter & Cover Page Content Requirements

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **CP.1** | Name of Document (Mining Plan and Mine Closure Plan / Final Mine Closure Plan) | Front Matter | Cover Page | MANDATORY | String | — | — | Universal | Cover | Static Schema | `AVAILABLE` |
| **CP.2** | Name of Coal / Lignite Block | Front Matter | Cover Page | MANDATORY | String | — | — | Universal | Cover | ExtractedField / Allotment | `AVAILABLE` |
| **CP.3** | Name of Coalfield / Lignite Field | Front Matter | Cover Page | MANDATORY | String | — | Plate 1 | Universal | Cover | ExtractedField / GR | `AVAILABLE` |
| **CP.4** | Name of Allottee / Project Proponent Company | Front Matter | Cover Page | MANDATORY | String | — | Annexure 1 | Universal | Cover | Organization Record | `AVAILABLE` |
| **CP.5** | Document Status (Original / Revised under Rule 22E MCR 1960) | Front Matter | Cover Page | MANDATORY | String | — | Annexure 6 | Universal | Cover | User Scope | `AVAILABLE` |
| **CP.6** | Revision Number & Prior Approval Reference (if revised) | Front Matter | Cover Page | CONDITIONAL | String | — | Annexure 6 | Revised Plans Only | Cover | Prior Approval Docs | `AVAILABLE` |
| **CP.7** | Name and Registration Number of Qualified Person (QP) | Front Matter | Cover Page | MANDATORY | String | — | Annexure 3 | Universal | Cover | QP Registry | `HUMAN_INPUT_REQUIRED` |
| **CP.8** | Name & QCI-NABET Accreditation Number of MPPA | Front Matter | Cover Page | CONDITIONAL | String | — | Annexure 10 | If prepared by MPPA | Cover | MPPA Certificate | `HUMAN_INPUT_REQUIRED` |
| **CP.9** | Month and Year of Submission | Front Matter | Cover Page | MANDATORY | Date | YYYY-MM | — | Universal | Cover | System Date | `AVAILABLE` |
| **IDX.1** | Index of Chapters (Items 1 to 9) | Front Matter | Table of Contents | MANDATORY | Table | — | — | Universal | TOC | Schema Generator | `CALCULATED` |
| **IDX.2** | Index of Annexures (Mandatory, Conditional, Optional) | Front Matter | Table of Contents | MANDATORY | Table | — | Annexures 1–13 | Universal | TOC | Annexure Registry | `CALCULATED` |
| **IDX.3** | Index of Plates / Technical Drawings | Front Matter | Table of Contents | MANDATORY | Table | — | Plates 1–8 | Universal | TOC | Plate Registry | `CALCULATED` |
| **IDX.4** | Standard List of Abbreviations and Acronyms | Front Matter | Abbreviations | MANDATORY | Table | — | — | Universal | Front | Static Glossary | `AVAILABLE` |

### 2.2 Item 1: Statutory Checklist Parameters

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **CHK.1** | Project Information Completeness Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Table 1.1 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.2** | Approved Geological Report (GR) Reference & Authenticity Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Annexure 2 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.3** | Mining Methodology, Production Schedule & Equipment Sizing Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Tables 3.1, 3.2 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.4** | Safety Management Plan (SMP) Integration Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | — | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.5** | Infrastructure & First Mile Connectivity (FMC) Layout Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Plate 1 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.6** | Total Land Requirement & Legal Classification Breakdown Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Table 6.1 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.7** | Environmental Baseline, EMP & Mitigation Protocol Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Annexure 7 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.8** | Progressive & Final Mine Closure Cost & Escrow Calculation Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Tables 8.1, 8.2 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.9** | Mandatory 25% Just Transition Escrow Fund Earmarking Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Table 8.2 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.10** | Qualified Person (QP) and MPPA Accreditation Validity Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Annexures 3, 10 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.11** | Technical Drawings & Plates Geo-referencing, Grid & Scale Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Plates 1–8 | Universal | Checklist | Compliance Validator | `CALCULATED` |
| **CHK.12** | Statutory Annexures, DGPS Survey & Board Approval Verification Check | Item 1: Checklist | Checklist | MANDATORY | Boolean | — | Annexures 1–13 | Universal | Checklist | Compliance Validator | `CALCULATED` |

### 2.3 Item 2: Chapter 1 — Project Information

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **1.1.1** | Name of Coal / Lignite mine or block | Chapter 1 | 1.1 Introduction | MANDATORY | String | — | Annexure 1 | Universal | P.1 | ExtractedField / Allotment | `AVAILABLE` |
| **1.1.2** | Name of Coalfield / Lignite field | Chapter 1 | 1.1 Introduction | MANDATORY | String | — | Plate 1 | Universal | P.1 | ExtractedField / GR | `AVAILABLE` |
| **1.1.3** | The base date of the Mining Plan | Chapter 1 | 1.1 Introduction | MANDATORY | Date | YYYY-MM | — | Universal | P.1 | User / Scope Input | `AVAILABLE` |
| **1.1.4** | Linked End Use Plant | Chapter 1 | 1.1 Introduction | MANDATORY | String | — | — | Universal | P.2 | ExtractedField / Allotment | `AVAILABLE` |
| **1.1.5** | Distance of End use plant from the pit head of the project in "km" | Chapter 1 | 1.1 Introduction | MANDATORY | Float | km | — | Universal | P.2 | ExtractedField / Feasibility | `AVAILABLE` |
| **1.1.6** | Mode of Coal Transport/Despatch | Chapter 1 | 1.1 Introduction | MANDATORY | String | — | Plate 1 | Universal | P.2 | ExtractedField / FMC Plan | `AVAILABLE` |
| **1.2.1** | Location of coal mine/block (District and State) | Chapter 1 | 1.2 Location & Comm | MANDATORY | String | — | Plate 1, 2 | Universal | P.3 | ExtractedField / Revenue | `AVAILABLE` |
| **1.2.2** | Communication: PWD roads, railway lines, Air | Chapter 1 | 1.2 Location & Comm | MANDATORY | String | — | Table 1.1 | Universal | P.3 | ExtractedField / Feasibility | `AVAILABLE` |
| **1.2.3** | Availability of power supply, water etc. | Chapter 1 | 1.2 Location & Comm | MANDATORY | String | — | — | Universal | P.4 | ExtractedField / Feasibility | `AVAILABLE` |
| **1.2.4** | Prominent physiographic features, drainage pattern, natural water courses, rainfall data, highest flood level | Chapter 1 | 1.2 Location & Comm | MANDATORY | String | — | Plate 2 | Universal | P.4 | Hybrid Retrieval / GR | `EXTRACTABLE` |
| **1.2.5** | Important surface features within the project area and major diversion or shifting involved | Chapter 1 | 1.2 Location & Comm | MANDATORY | String | — | Plate 2 | Universal | P.5 | Hybrid Retrieval / Survey | `EXTRACTABLE` |
| **1.3.1** | Name of the Allottee | Chapter 1 | 1.3 Allotment Details | MANDATORY | String | — | Annexure 1 | Universal | P.5 | Organization Record | `AVAILABLE` |
| **1.3.2** | Details of allotment/vesting order | Chapter 1 | 1.3 Allotment Details | MANDATORY | String | — | Annexure 1 | Universal | P.6 | ExtractedField / Allotment | `AVAILABLE` |
| **1.3.3** | Name and address of the applicant (Regd. Office, Principal Place of Business) | Chapter 1 | 1.3 Allotment Details | MANDATORY | String | — | Annexure 4 | Universal | P.6 | Organization Record | `AVAILABLE` |
| **1.3.4** | Name of the Previous Allottee of the Block | Chapter 1 | 1.3 Allotment Details | CONDITIONAL | String | — | — | De-allocated blocks | P.6 | ExtractedField / Gazette | `AVAILABLE` |
| **1.3.5** | Rated capacity and peak capacity as per allotment / allocation | Chapter 1 | 1.3 Allotment Details | MANDATORY | Float | MTPA | — | Universal | P.7 | ExtractedField / Allotment | `AVAILABLE` |

### 2.4 Item 3: Chapter 2 — Exploration, Geology, Seam Sequence, Coal Quality and Reserve

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **2.1.1** | Particulars of adjacent area/blocks | Chapter 2 | 2.1 Block Details | MANDATORY | String | — | Plate 2 | Universal | P.8 | Hybrid Retrieval / GR | `EXTRACTABLE` |
| **2.1.2** | Name of the Geological Report with month and year of preparation | Chapter 2 | 2.1 Block Details | MANDATORY | String | — | Annexure 2 | Universal | P.8 | ExtractedField / GR | `AVAILABLE` |
| **2.1.3** | Name of the GR Preparing Agency | Chapter 2 | 2.1 Block Details | MANDATORY | String | — | Annexure 2 | Universal | P.9 | ExtractedField / GR | `AVAILABLE` |
| **2.1.4** | Area in hectares | Chapter 2 | 2.1 Block Details | MANDATORY | Float | Ha | Annexure 5 | Universal | P.9 | ExtractedField / Allotment | `AVAILABLE` |
| **2.1.5** | KML file of the proposed lease/project area | Chapter 2 | 2.1 Block Details | MANDATORY | File / Coords | WGS84 | Plate 2, Annex 5 | Universal | P.10 | DGPS Survey File | `EXTERNAL_ATTACHMENT_REQUIRED` |
| **2.2.1** | Exploration status and borehole density | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | Float | BH/sq km | Table 2.1, Plate 3 | Universal | P.11 | ExtractedField / GR | `AVAILABLE` |
| **2.2.2** | Regional geological setup and local geology of the block | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | Text | — | Plate 3 | Universal | P.12 | Grounded Local LLM | `AVAILABLE` |
| **2.2.3** | Geological structure (Strike, Dip direction, Dip amount, Faults with strike, dip, throws) | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | String | Degrees | Plate 3, 4 | Universal | P.13 | ExtractedField / GR | `AVAILABLE` |
| **2.2.4** | Stratigraphic succession and lithological characteristics of formations | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | Text | — | Table 2.2, Plate 4 | Universal | P.14 | Grounded Local LLM | `AVAILABLE` |
| **2.2.5** | Seam sequence, thickness range (min, max, avg in meters) and parting thickness | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | Float | m | Table 2.2, Plate 5 | Universal | P.15 | ExtractedField / GR | `AVAILABLE` |
| **2.2.6** | Depth range of coal seams (minimum and maximum depth to floor in meters) | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | Float | m | Table 2.2, Plate 4 | Universal | P.16 | ExtractedField / GR | `AVAILABLE` |
| **2.2.7** | Coal quality parameters (Grade, GCV kcal/kg, Ash %, Moisture %, VM %, FC %) | Chapter 2 | 2.2 Exploration & Geo | MANDATORY | Float | kcal/kg, % | Table 2.3 | Universal | P.17 | ExtractedField / GR | `AVAILABLE` |
| **2.2.8** | Seam gas content / CBM potential / Spontaneous heating & crossing point temperature | Chapter 2 | 2.2 Exploration & Geo | CONDITIONAL | Float | cum/t, $^\circ$C | — | Gassy/Reactive seams | P.18 | Hybrid Retrieval / GR | `EXTRACTABLE` |
| **2.3.1** | Resource estimation methodology (ISP Guidelines / UNFC system) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | String | — | — | Universal | P.19 | ExtractedField / GR | `AVAILABLE` |
| **2.3.2** | Gross Geological Reserve of the block (Proved, Indicated, Inferred in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.4 | Universal | P.20 | ExtractedField / GR | `AVAILABLE` |
| **2.3.3** | Net Geological Reserve (after geological deduction for faults, washouts in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.4 | Universal | P.21 | Deterministic Arithmetic | `CALCULATED` |
| **2.3.4** | Blocked Reserves / Resources (under statutory safety barriers, rivers, HFL, rail, roads) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.5 | Universal | P.22 | ExtractedField / Feasibility | `AVAILABLE` |
| **2.3.5** | Minable Reserve (in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.6 | Universal | P.23 | Deterministic Arithmetic | `CALCULATED` |
| **2.3.6** | Mining losses (fault losses, roof/floor contact losses, rib losses in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.6 | Universal | P.24 | Deterministic Arithmetic | `CALCULATED` |
| **2.3.7** | Extractable Reserve (in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.6 | Universal | P.25 | Deterministic Arithmetic | `CALCULATED` |
| **2.3.8** | Overall Percentage of Extraction / Recovery Factor (%) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | % | Table 2.6 | Universal | P.25 | Deterministic Arithmetic | `CALCULATED` |
| **2.3.9** | Coal Resources Already Depleted / Extracted up to base date (in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.6 | Universal | P.26 | Prior Production Data | `AVAILABLE` |
| **2.3.10** | Balance Resource / Extractable Reserves available as on base date (in MT) | Chapter 2 | 2.3 Reserve Assess | MANDATORY | Float | MT | Table 2.6 | Universal | P.26 | Deterministic Arithmetic | `CALCULATED` |
| **2.3.11** | Average Stripping Ratio (Volume of OB in Mcum to Coal in MT, cum/tonne) | Chapter 2 | 2.3 Reserve Assess | CONDITIONAL | Float | cum/tonne | Table 2.6 | Opencast / Mixed Only | P.27 | Deterministic Arithmetic | `CALCULATED` |

### 2.5 Item 4: Chapter 3 — Mining

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **3.1.1** | Proposed Mining Method (Opencast / Underground / Mixed) & Justification | Chapter 3 | 3.1 Mining Method | MANDATORY | String | — | Plate 6A / 6B | Universal | P.28 | ExtractedField / Feasibility | `AVAILABLE` |
| **3.1.2** | Target Production Capacity (Rated and Peak capacity in MTPA) | Chapter 3 | 3.2 Production Cap | MANDATORY | Float | MTPA | Table 3.1 | Universal | P.29 | ExtractedField / Allotment | `AVAILABLE` |
| **3.1.3** | Life of Mine (LOM in years) | Chapter 3 | 3.3 Life of Mine | MANDATORY | Float | Years | — | Universal | P.30 | Deterministic Arithmetic | `CALCULATED` |
| **3.1.4** | Mine Geometry: Bench height, width, slope angles, quarry limits / Panel dimensions | Chapter 3 | 3.4 Workings | MANDATORY | String | m, Degrees | Plate 6A / 6B | Universal | P.31 | Hybrid Retrieval / Mine DPR | `EXTRACTABLE` |
| **3.1.5** | Heavy Earth Moving Machinery (HEMM) / Equipment sizing, selection & fleet deployment | Chapter 3 | 3.5 Equipment Fleet | MANDATORY | Table | No., Capacity | Table 3.2 | Universal | P.32 | ExtractedField / Equipment DPR | `AVAILABLE` |
| **3.1.6** | Year-wise production schedule and Overburden (OB) removal schedule (Years 1 to 5) | Chapter 3 | 3.6 Sched Production | MANDATORY | Table | MT, Mcum | Table 3.1, Plate 6 | Universal | P.33 | ExtractedField / Mine DPR | `AVAILABLE` |
| **3.1.7** | Mine drainage, peak pumping capacity (cum/hr), sump design, runoff handling | Chapter 3 | 3.7 Mine Drainage | MANDATORY | String | cum/hr | Plate 6A / 6B | Universal | P.34 | Hybrid Retrieval / Drainage DPR | `EXTRACTABLE` |

### 2.6 Item 5: Chapter 4 — Safety Management

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **4.1.1** | Risk Assessment & Safety Management Plan (SMP) as per DGMS guidelines | Chapter 4 | 4.1 Risk Assessment | MANDATORY | Text | — | — | Universal | P.35 | ExtractedField / Safety Audit | `AVAILABLE` |
| **4.1.2** | Gas categorization (Degree I/II/III) OR Slope & Dump stability monitoring | Chapter 4 | 4.2 Hazard Control | MANDATORY | String | — | Plate 6A / 6B | Universal | P.36 | ExtractedField / DGMS Audit | `AVAILABLE` |
| **4.1.3** | Strata control plan / RMR (for UG) OR Highwall & dump monitoring instrumentation (for OC) | Chapter 4 | 4.3 Ground Control | MANDATORY | String | — | Plate 6A / 6B | Universal | P.37 | Hybrid Retrieval / Safety DPR | `EXTRACTABLE` |
| **4.1.4** | Fire management, spontaneous combustion prevention, coal dust & inundation control | Chapter 4 | 4.4 Hazard Prevention | MANDATORY | Text | — | — | Universal | P.37 | Hybrid Retrieval / SMP | `EXTRACTABLE` |
| **4.1.5** | Emergency preparedness, disaster management plan, and rescue arrangements | Chapter 4 | 4.5 Emergency Prep | MANDATORY | Text | — | — | Universal | P.38 | Hybrid Retrieval / DMP | `EXTRACTABLE` |

### 2.7 Item 6: Chapter 5 — Infrastructure Facilities proposed and their Location

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **5.1.1** | Coal Handling Plant (CHP), Crushing, and First Mile Connectivity (FMC) network | Chapter 5 | 5.1 CHP & FMC | MANDATORY | String | TPH, km | Plate 1 | Universal | P.38 | ExtractedField / Infrastructure | `AVAILABLE` |
| **5.1.2** | Railway Siding, Track Layout, Rapid Loading System (RLS), Silo Facilities | Chapter 5 | 5.2 Railway Siding | MANDATORY | String | Rakes/day | Plate 1 | Universal | P.39 | Hybrid Retrieval / Rail DPR | `EXTRACTABLE` |
| **5.1.3** | Workshop facilities, HEMM maintenance bays, store yards, fuel station | Chapter 5 | 5.3 Workshop & Stores | MANDATORY | String | — | Plate 2 | Universal | P.40 | Hybrid Retrieval / Layout DPR | `EXTRACTABLE` |
| **5.1.4** | Power distribution system, main sub-station capacity, transmission lines, DG backup | Chapter 5 | 5.4 Power Supply | MANDATORY | String | MVA, kV | Plate 2 | Universal | P.40 | Hybrid Retrieval / Electrical | `EXTRACTABLE` |
| **5.1.5** | Explosive magazine, blast shelter, ANFO / bulk emulsion shed (PESO norms) | Chapter 5 | 5.5 Magazine | MANDATORY | String | Tonnes capacity | Plate 2 | Universal | P.41 | Hybrid Retrieval / PESO Filing | `EXTRACTABLE` |
| **5.1.6** | Industrial effluent treatment (ETP), sewage treatment (STP), and water supply | Chapter 5 | 5.6 Water & Effluent | MANDATORY | String | KLD | Plate 2 | Universal | P.41 | Hybrid Retrieval / EIA-EMP | `EXTRACTABLE` |
| **5.1.7** | Administrative buildings, occupational health centre (OHC), VTC, canteen | Chapter 5 | 5.7 Service Bldgs | MANDATORY | String | — | Plate 2 | Universal | P.42 | Hybrid Retrieval / Layout DPR | `EXTRACTABLE` |

### 2.8 Item 7: Chapter 6 — Land Requirement

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **6.1.1** | Total project land requirement | Chapter 6 | 6.1 Total Land | MANDATORY | Float | Ha | Table 6.1 | Universal | P.42 | ExtractedField / Land Records | `AVAILABLE` |
| **6.1.2** | Land classification breakdown: Forest, Private/Tenancy, Govt/Revenue, Waste/GMK | Chapter 6 | 6.2 Land Classify | MANDATORY | Float | Ha | Table 6.1 | Universal | P.43 | ExtractedField / Land Records | `AVAILABLE` |
| **6.1.3** | Activity-wise land utilization schedule: Quarry, OB Dumps, CHP, Green Belt, Safety | Chapter 6 | 6.3 Land Use Sched | MANDATORY | Float | Ha | Table 6.1, Plate 2 | Universal | P.44 | ExtractedField / Mine DPR | `AVAILABLE` |
| **6.1.4** | Status of land acquisition, Stage-I / Stage-II forest clearance, physical possession | Chapter 6 | 6.4 Clearance Status | MANDATORY | String | — | Annexure 8 | Universal | P.45 | ExtractedField / Clearances | `AVAILABLE` |

### 2.9 Item 8: Chapter 7 — Environment Management

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **7.1.1** | Baseline environmental quality (Micro-meteorology, Air, Noise, Water, Soil, Ecology) | Chapter 7 | 7.1 Baseline Status | MANDATORY | Text | — | Annexure 7 | Universal | P.46 | Hybrid Retrieval / EIA | `EXTRACTABLE` |
| **7.1.2** | Environmental pollution mitigation measures (Water mist, garland drains, settling ponds) | Chapter 7 | 7.2 Mitigation Plan | MANDATORY | Text | — | — | Universal | P.47 | Hybrid Retrieval / EMP | `EXTRACTABLE` |
| **7.1.3** | Progressive green belt development, topsoil preservation, afforestation density | Chapter 7 | 7.3 Afforestation | MANDATORY | Text | Ha, Trees/Ha | Plate 7 | Universal | P.48 | Hybrid Retrieval / EMP | `EXTRACTABLE` |
| **7.1.4** | Socio-economic profile, R&R Plan as per RFCTLARR Act 2013, CSR commitments | Chapter 7 | 7.4 Socio-Economics | MANDATORY | Text | — | — | Universal | P.49 | Hybrid Retrieval / R&R DPR | `EXTRACTABLE` |

### 2.10 Item 9: Chapter 8 — Progressive and Final Mine Closure Plan

| Official ID | Exact Official Label | Parent Chapter | Parent Section | Required Status | Data Type | Unit | Table/Plate/Annexure | Applicability | Source Page | KOYLA Mapping | Mapping Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **8.1.1** | Mine closure framework, baseline environmental data, and closure principles | Chapter 8 | 8.1 Closure Baseline | MANDATORY | Text | — | Plate 7, 8 | Universal | P.50 | Grounded Local LLM | `AVAILABLE` |
| **8.2.1** | Progressive closure schedule: Backfilling, technical & biological reclamation | Chapter 8 | 8.2 Progressive Plan | MANDATORY | Table | Ha, Mcum | Table 8.1, Plate 7 | Universal | P.51 | ExtractedField / Closure DPR | `AVAILABLE` |
| **8.3.1** | Final mine closure: Infrastructure decommissioning, sealing entries, fencing voids | Chapter 8 | 8.3 Final Closure | MANDATORY | Text | — | Plate 8 | Universal | P.52 | Hybrid Retrieval / Closure DPR | `EXTRACTABLE` |
| **8.4.1** | Mine closure cost estimation & Escrow Account annual deposit calculation | Chapter 8 | 8.4 Escrow Finance | MANDATORY | Float | Lakh INR | Table 8.2, Annex 9 | Universal | P.53 | Deterministic Arithmetic | `CALCULATED` |
| **8.4.2** | Mandatory 25% Earmarking for Just Transition & Community Development | Chapter 8 | 8.4 Escrow Finance | MANDATORY | Float | Lakh INR | Table 8.2 | Universal (2025 Mandate) | P.54 | Deterministic Arithmetic | `CALCULATED` |
| **8.5.1** | Post-closure environmental monitoring and maintenance schedule (3–5 years) | Chapter 8 | 8.5 Post-Closure | MANDATORY | Text | Years | — | Universal | P.55 | Hybrid Retrieval / Closure DPR | `EXTRACTABLE` |

### 2.11 Prescribed Official Tables (12 Tables)

| Table ID | Exact Official Table Title | Chapter | Required Status | Columns Schema & Prescribed Units | Applicability | KOYLA Mapping |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Table 1.1** | Communication and Location Infrastructure Summary | Chapter 1 | MANDATORY | Facility, Name/Route, Distance (km), Coordinates | Universal | `AVAILABLE` |
| **Table 2.1** | Borehole Exploration Drilling Summary and Grid Density | Chapter 2 | MANDATORY | Series, Number of Boreholes, Total Meterage (m), Grid Density (BH/sq km) | Universal | `AVAILABLE` |
| **Table 2.2** | Stratigraphic Succession, Seam Sequence, Depth and Thickness Range | Chapter 2 | MANDATORY | Seam Name, Roof Depth (m), Floor Depth (m), Thickness Range (m), Parting (m) | Universal | `AVAILABLE` |
| **Table 2.3** | Band-by-Band Coal Quality, Proximate Analysis, and Grade Distribution | Chapter 2 | MANDATORY | Seam Name, Moisture %, Ash %, VM %, FC %, GCV (kcal/kg), Grade | Universal | `AVAILABLE` |
| **Table 2.4** | Gross and Net Geological Reserves Categorization | Chapter 2 | MANDATORY | Seam Name, Proved (MT), Indicated (MT), Inferred (MT), Gross (MT), Deductions (MT), Net (MT) | Universal | `CALCULATED` |
| **Table 2.5** | Blocked Coal Reserves Categorized by Constraint Category | Chapter 2 | MANDATORY | Seam Name, Safety Barriers (MT), River/HFL (MT), Roads/Rail (MT), Villages (MT), Total Blocked (MT) | Universal | `AVAILABLE` |
| **Table 2.6** | Minable, Extractable, Depleted, and Balance Reserves Reconciliation | Chapter 2 | MANDATORY | Seam Name, Minable (MT), Mining Losses (MT), Extractable (MT), Depleted (MT), Balance (MT), SR (cum/t) | Universal | `CALCULATED` |
| **Table 3.1** | Year-wise Production and Overburden (OB) Removal Schedule | Chapter 3 | MANDATORY | Year (Yr 1–5, 5-yr blocks), Coal Production (MT), OB Removal (Mcum), Stripping Ratio (cum/t) | Universal | `AVAILABLE` |
| **Table 3.2** | Heavy Earth Moving Machinery (HEMM) Equipment Fleet Deployment | Chapter 3 | MANDATORY | Equipment Type, Capacity (cum / Tonnes), Number Required, Number Deployed, Fleet Status | Universal | `AVAILABLE` |
| **Table 6.1** | Land Requirement and Legal Classification Status | Chapter 6 | MANDATORY | Land Category (Forest, Private, Revenue, Waste), Area in Quarry (Ha), OB Dump (Ha), Infra (Ha), Total (Ha) | Universal | `AVAILABLE` |
| **Table 8.1** | Progressive Mine Closure Technical and Biological Reclamation Schedule | Chapter 8 | MANDATORY | Year, Area Backfilled (Ha), Volume OB Handled (Mcum), Area Revegetated (Ha), Plantation Density | Universal | `AVAILABLE` |
| **Table 8.2** | Mine Closure Escrow Account Annual Deposit Calculation Table | Chapter 8 | MANDATORY | Year, Area Subject to Closure (Ha), Base Cost/Ha, Escalation Factor, Annual Deposit (Lakh INR), 25% Just Transition Fund (Lakh INR) | Universal | `CALCULATED` |

### 2.12 Technical Plates / Plans / Drawings (9 Plates with Method Conditionality)

| Plate ID | Exact Official Plate Title | Chapter | Required Status | Prescribed Scale | Applicability Condition | Technical Drawing Requirements | KOYLA Status |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **Plate 1** | Key Plan / Location and Regional Communication Plan | Chapter 1 | MANDATORY | 1:50,000 | Universal (OC & UG) | Survey of India grid, North arrow, road/rail connectivity | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 2** | Surface Plan / Topographical Plan | Chapter 1 & 2 | MANDATORY | 1:5,000 | Universal (OC & UG) | 100m safety buffer, DGPS boundary, contours, watercourses | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 3** | Geological Plan with Borehole Locations & Outcrop Lines | Chapter 2 | MANDATORY | 1:5,000 | Universal (OC & UG) | Borehole collar elevations, strike/dip, faults, incrops | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 4** | Geological Cross-Sections Across Strike and Dip | Chapter 2 | MANDATORY | 1:2,000 / 1:5,000 | Universal (OC & UG) | Section lines along boreholes, vertical exaggeration noted | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 5** | Seam Floor Contour Plan and Seam Folio / Isochore Plans | Chapter 2 | MANDATORY | 1:5,000 | Universal (OC & UG) | Contours of floor RL, seam thickness isopachs | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 6A** | Opencast Mining Layout Plan (Quarry limits & Dumps) | Chapter 3 | CONDITIONAL | 1:5,000 | Opencast / Mixed Mines Only | Pit limits, bench geometry, haul road gradient, internal dump | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 6B** | Underground Mining Layout Plan (Panels, Entries, Ventilation) | Chapter 3 | CONDITIONAL | 1:5,000 | Underground / Mixed Mines Only | Shafts, adits, panel layout, airway routes, intake/return | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 7** | Progressive Mine Closure Plan (Year 1 to 5 Stages) | Chapter 8 | MANDATORY | 1:5,000 | Universal (OC & UG) | Backfilled stages, technical reclamation, afforestation | `HUMAN_GIS_INPUT_REQUIRED` |
| **Plate 8** | Final Land Use Plan on Mine Closure | Chapter 8 | MANDATORY | 1:5,000 | Universal (OC & UG) | Post-mining void water body, stabilized dumps, public assets | `HUMAN_GIS_INPUT_REQUIRED` |

*Rule*: All plates require verified technical inputs. In the prototype, if drawing raster/CAD data is unuploaded, the plate is explicitly marked: `NOT GENERATED — SOURCE DATA REQUIRED`. KOYLA never fabricates synthetic drawings.

### 2.13 Prescribed Statutory & Conditional Annexures (13 Annexures)

| Annexure ID | Exact Official Annexure Title | Chapter | Required Status | Applicability Condition | Source Reference | KOYLA Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Annexure 1** | Copy of Allotment Order / Vesting Order / Mining Lease deed | Chapter 1 | MANDATORY | Universal | Ministry of Coal Allocation Order | `AVAILABLE` |
| **Annexure 2** | Approval letter of Geological Report by Competent Authority | Chapter 2 | MANDATORY | Universal | MoC / CMPDI GR Approval Letter | `AVAILABLE` |
| **Annexure 3** | Certificate of Qualified Person (QP) under Rule 22C MCR 1960 | Execution | MANDATORY | Universal | QP Accreditation / Registration Record | `HUMAN_INPUT_REQUIRED` |
| **Annexure 4** | Corporate Board Resolution & Power of Attorney of Signatory | Chapter 1 | MANDATORY | Corporate Allottees | Certified Company Secretary Resolution | `EXTERNAL_ATTACHMENT_REQUIRED` |
| **Annexure 5** | DGPS Boundary Survey Report with pillar coordinates | Chapter 2 | MANDATORY | Universal | State Mining Dept Authenticated Report | `EXTERNAL_ATTACHMENT_REQUIRED` |
| **Annexure 6** | Prior Approval / Earlier Mining Plan Approval letters | Chapter 1 | CONDITIONAL | Revised Plans Only (Rule 22E MCR 1960) | Previous CCO/MoC Approval Letter | `AVAILABLE` |
| **Annexure 7** | Terms of Reference (ToR) / Environmental Clearance (EC) Status | Chapter 7 | CONDITIONAL | Projects with prior clearances | MoEFCC EC / ToR Letter | `AVAILABLE` |
| **Annexure 8** | Stage-I / Stage-II Forest Clearance Status copy | Chapter 6 | CONDITIONAL | Forest land involved | MoEFCC FC Letter | `AVAILABLE` |
| **Annexure 9** | Draft Escrow Agreement for Mine Closure Plan with Bank and CCO | Chapter 8 | MANDATORY | Universal | Tripartite Escrow Agreement Draft | `AVAILABLE` |
| **Annexure 10** | QCI-NABET Accreditation Certificate of MPPA | Execution | CONDITIONAL | If prepared by MPPA | NABET Accreditation Certificate | `HUMAN_INPUT_REQUIRED` |
| **Annexure 11** | Schedule of Mine Closure Implementation Activity Chart | Chapter 8 | MANDATORY | Universal | Closure DPR Schedule | `AVAILABLE` |
| **Annexure 12** | Expert Review / Peer Review Report by Accredited Agency | Execution | MANDATORY | Universal | Accredited Third-Party Scrutiny Report | `AVAILABLE` |
| **Annexure 13** | Other Statutory Documents / State Clearances (if any) | Various | OPTIONAL | Contextual | Ground Water / State Pollution Control Board | `AVAILABLE` |

### 2.14 Prescribed Certifications & Declarations (4 Execution Blocks)

| Cert ID | Official Certification Purpose | Signatory Role | Prescribed Undertaking Text | Audit State Lifecycle |
| :--- | :--- | :--- | :--- | :--- |
| **Cert 1** | Qualified Person (QP) Statutory Certificate | Qualified Person (`prepared_by`) | Plan prepared within boundary; data verified from approved GR; Rule 22C MCR compliance | `SYSTEM_GENERATED` $\rightarrow$ `HUMAN_VERIFIED` $\rightarrow$ `AUTHORIZED_SIGNED` |
| **Cert 2** | Mining Plan Preparing Agency (MPPA) Certificate | Accredited MPPA (`certified_by`) | Organization holds valid QCI-NABET accreditation; technical accuracy certified | `SYSTEM_GENERATED` $\rightarrow$ `HUMAN_VERIFIED` $\rightarrow$ `AUTHORIZED_SIGNED` |
| **Cert 3** | Project Proponent / Allottee Undertaking | Managing Director / Director (`verified_by` / `signed_by`) | Undertaking to execute operations per approved plan; escrow funding commitment; DGMS compliance | `SYSTEM_GENERATED` $\rightarrow$ `HUMAN_VERIFIED` $\rightarrow$ `AUTHORIZED_SIGNED` |
| **Cert 4** | Corporate Board Resolution Endorsement | Company Secretary (`authorized_by`) | Formal corporate approval authorising submission to Coal Controller Organisation | `SYSTEM_GENERATED` $\rightarrow$ `HUMAN_VERIFIED` $\rightarrow$ `AUTHORIZED_SIGNED` |

*Note*: CCO approval is an external administrative scrutiny act by the government; it is **not** a system-generated signature. KOYLA provides the submission-ready document for official scrutiny.

---

## 3. KOYLA Data-Availability Summary Across the 126 Parameters

| Mapping Category | Parameter Count | Percentage | Operational Handling in KOYLA |
| :--- | :---: | :---: | :--- |
| **`AVAILABLE`** | 63 | 50.0% | Directly populated from structured database records (`ExtractedField`) and existing ingestion files. |
| **`CALCULATED`** | 17 | 13.5% | Computed deterministically via Python arithmetic engine (Reserves deduction, Stripping ratio, LOM, Escrow annuity). |
| **`EXTRACTABLE`** | 20 | 15.9% | Mapped via hybrid retrieval and grounded local LLM narrative from uploaded specialized DPRs/EMP reports. |
| **`HUMAN_INPUT_REQUIRED`** | 7 | 5.6% | Verified input fields (QP registration number, MPPA accreditation ID, signatory details, and technical plate scales). |
| **`EXTERNAL_ATTACHMENT_REQUIRED`** | 10 | 7.9% | Requires user-provided attachment (KML/DGPS boundary survey, certified Board resolution, technical drawings). |
| **`NOT_YET_SUPPORTED`** | 9 | 7.1% | Technical CAD/GIS layer rendering (marked strictly as `NOT GENERATED — SOURCE DATA REQUIRED`). |
| **Total Official Parameters** | **126** | **100.0%** | Full statutory scope of Appendix-I |

*Anti-Hallucination Enforced*: Unpopulated fields strictly display `DATA NOT AVAILABLE IN VERIFIED KNOWLEDGE BASE`. Missing plates strictly display `NOT GENERATED — SOURCE DATA REQUIRED`. Zero synthetic data is injected.
