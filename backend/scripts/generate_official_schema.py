"""
Script to generate the machine-readable Appendix-I schema for
Ministry of Coal / Coal Controller Organisation (CCO)
Guidelines for Preparation of Mining Plan and Mine Closure Plan, 2025
OM F.No. CPAM-34011/28/2019-CPAM [E-343762] dated 31 January 2025.
"""
import json
import os

def build_schema():
    nodes = []

    # Container nodes for top-level hierarchy
    nodes.append({
        "internal_id": "root_front_matter",
        "official_id": None,
        "exact_official_label": "Front Matter",
        "parent_id": None,
        "node_type": "FRONT_MATTER",
        "sequence": 1,
        "required_status": "MANDATORY",
        "applicability_condition": None,
        "data_type": "Section",
        "unit": None,
        "max_words_or_limits": None,
        "official_instruction": "Cover page, indexes, abbreviations conforming to Appendix-I specifications.",
        "source_page": "Cover",
        "source_reference": "Appendix-I Front Matter",
        "table_reference": None,
        "annexure_reference": None,
        "plate_reference": None,
        "koyla_mapping_status": "AVAILABLE_FROM_KOYLADB"
    })

    # Front Matter Items
    fm_items = [
        ("fm_doc_name", None, "Name of Document (Mining Plan and Mine Closure Plan / Final Mine Closure Plan)", "String", None, 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Cover", "Specify document type."),
        ("fm_block_name", None, "Name of Coal / Lignite Block", "String", None, 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Cover", "Exact block name as allocated in allotment order."),
        ("fm_coalfield_name", None, "Name of Coalfield / Lignite Field", "String", None, 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Cover", "Name of sedimentary basin / coalfield."),
        ("fm_allottee_name", None, "Name of Allottee / Project Proponent Company", "String", None, 200, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Cover", "Full legal entity name."),
        ("fm_doc_status", None, "Document Status (Original / Revised under Rule 22E MCR 1960)", "String", None, 50, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Cover", "Original or Revised under Rule 22E."),
        ("fm_revision_ref", None, "Revision Number & Prior Approval Reference (if revised)", "String", None, 150, "CONDITIONAL", "Applicable only for modified/revised mining plans under Rule 22E", "AVAILABLE_FROM_KOYLADB", "Cover", "Reference number and date of earlier approval."),
        ("fm_qp_details", None, "Name and Registration Number of Qualified Person (QP)", "String", None, 150, "MANDATORY", None, "REQUIRES_HUMAN_INPUT", "Cover", "Full name and registration of QP under Rule 22C MCR 1960."),
        ("fm_mppa_details", None, "Name & QCI-NABET Accreditation Number of MPPA", "String", None, 150, "CONDITIONAL", "Applicable when prepared through accredited MPPA", "REQUIRES_HUMAN_INPUT", "Cover", "NABET accreditation number and validity."),
        ("fm_submission_date", None, "Month and Year of Submission", "Date", "YYYY-MM", 20, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Cover", "Month and year of formal submission."),
        ("fm_index_chapters", None, "Index of Chapters (Items 1 to 9)", "Table", None, None, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "Index", "Table of contents of Checklist and Chapters 1 to 8."),
        ("fm_index_annexures", None, "Index of Annexures", "Table", None, None, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "Index", "List of all statutory and supplementary annexures with page numbers."),
        ("fm_index_plates", None, "Index of Plans / Plates / Drawings", "Table", None, None, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "Index", "List of technical plates with drawing numbers, scales, and titles."),
        ("fm_abbreviations", None, "Standard List of Abbreviations and Acronyms", "Table", None, None, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Front", "Glossary of abbreviations used.")
    ]

    for idx, (iid, oid, label, dt, unit, limits, req, app, km, sp, inst) in enumerate(fm_items, start=1):
        nodes.append({
            "internal_id": iid,
            "official_id": oid,
            "exact_official_label": label,
            "parent_id": "root_front_matter",
            "node_type": "FRONT_MATTER",
            "sequence": idx,
            "required_status": req,
            "applicability_condition": app,
            "data_type": dt,
            "unit": unit,
            "max_words_or_limits": limits,
            "official_instruction": inst,
            "source_page": sp,
            "source_reference": "Appendix-I Cover & Front Matter",
            "table_reference": None,
            "annexure_reference": None,
            "plate_reference": None,
            "koyla_mapping_status": km
        })

    # Item 1: Checklist Container
    nodes.append({
        "internal_id": "root_checklist",
        "official_id": "1",
        "exact_official_label": "Checklist for Mining Plan",
        "parent_id": None,
        "node_type": "CHECKLIST",
        "sequence": 2,
        "required_status": "MANDATORY",
        "applicability_condition": None,
        "data_type": "Section",
        "unit": None,
        "max_words_or_limits": None,
        "official_instruction": "Statutory pre-scrutiny compliance checklist as prescribed in Item 1 of Appendix-I.",
        "source_page": "Checklist",
        "source_reference": "Appendix-I Item 1",
        "table_reference": None,
        "annexure_reference": None,
        "plate_reference": None,
        "koyla_mapping_status": "DERIVABLE_FROM_KOYLADB"
    })

    # Checklist Items (Parameters 1 to 12)
    chk_items = [
        ("chk_1_project_info", None, "Project Information Completeness Check", "Boolean", "Table 1.1", "Annexure 1", None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_2_gr_reference", None, "Approved Geological Report (GR) Reference & Authenticity Check", "Boolean", None, "Annexure 2", None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_3_mining_methodology", None, "Mining Methodology, Production Schedule & Equipment Sizing Check", "Boolean", "Table 3.1", None, "Plate 6", "DERIVABLE_FROM_KOYLADB"),
        ("chk_4_smp_integration", None, "Safety Management Plan (SMP) Integration Check", "Boolean", None, None, None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_5_fmc_layout", None, "Infrastructure & First Mile Connectivity (FMC) Layout Check", "Boolean", None, None, "Plate 1", "DERIVABLE_FROM_KOYLADB"),
        ("chk_6_land_requirement", None, "Total Land Requirement & Legal Classification Breakdown Check", "Boolean", "Table 6.1", None, None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_7_env_baseline", None, "Environmental Baseline, EMP & Mitigation Protocol Check", "Boolean", None, "Annexure 7", None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_8_closure_cost", None, "Progressive & Final Mine Closure Cost & Escrow Calculation Check", "Boolean", "Table 8.1", "Annexure 9", None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_9_just_transition", None, "Mandatory 25% Just Transition Escrow Fund Earmarking Check", "Boolean", "Table 8.2", None, None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_10_qp_mppa_validity", None, "Qualified Person (QP) and MPPA Accreditation Validity Check", "Boolean", None, "Annexure 3", None, "DERIVABLE_FROM_KOYLADB"),
        ("chk_11_plates_georeferencing", None, "Technical Drawings & Plates Geo-referencing, Grid & Scale Check", "Boolean", None, None, "Plates 1-8", "DERIVABLE_FROM_KOYLADB"),
        ("chk_12_annexures_dgps", None, "Statutory Annexures, DGPS Survey & Board Approval Verification Check", "Boolean", None, "Annexures 1-13", None, "DERIVABLE_FROM_KOYLADB"),
    ]

    for idx, (iid, oid, label, dt, tbl_ref, ann_ref, plt_ref, km) in enumerate(chk_items, start=1):
        nodes.append({
            "internal_id": iid,
            "official_id": oid,
            "exact_official_label": label,
            "parent_id": "root_checklist",
            "node_type": "CHECKLIST",
            "sequence": idx,
            "required_status": "MANDATORY",
            "applicability_condition": None,
            "data_type": dt,
            "unit": None,
            "max_words_or_limits": None,
            "official_instruction": "Verification check per statutory requirements.",
            "source_page": "Checklist",
            "source_reference": f"Appendix-I Item 1 Check {oid}",
            "table_reference": tbl_ref,
            "annexure_reference": ann_ref,
            "plate_reference": plt_ref,
            "koyla_mapping_status": km
        })

    # Numbered Chapters (Items 2 to 9 of Appendix-I)
    chapters_def = [
        ("ch_1", "2", "Chapter 1 — Project Information", 3, "P.1", [
            ("sec_1_1", "1.1", "Introduction", [
                ("fld_1_1_1", "1.1.1", "Name of Coal / Lignite mine or block", "String", None, 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.1", "Name of block as per allocation/vesting order", None, "Annexure 1", None),
                ("fld_1_1_2", "1.1.2", "Name of Coalfield / Lignite field", "String", None, 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.1", "Coalfield/basin name", None, None, "Plate 1"),
                ("fld_1_1_3", "1.1.3", "The base date of the Mining Plan", "Date", "YYYY-MM", 20, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.1", "Base date for reserves, balances, and scheduling", None, None, None),
                ("fld_1_1_4", "1.1.4", "Linked End Use Plant", "String", None, 200, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.2", "End use plant details", None, None, None),
                ("fld_1_1_5", "1.1.5", "Distance of End use plant from the pit head of the project in \"km\"", "Float", "km", 20, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.2", "Distance from pit head to plant in km", None, None, None),
                ("fld_1_1_6", "1.1.6", "Mode of Coal Transport/Despatch", "String", None, 150, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.2", "Belt conveyor / MGR / Rail siding / Road transport", None, None, "Plate 1"),
            ]),
            ("sec_1_2", "1.2", "Location and Communication", [
                ("fld_1_2_1", "1.2.1", "Location of coal mine/block (District and State)", "String", None, 150, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.3", "District, Tehsil, and State", None, None, "Plate 1, 2"),
                ("fld_1_2_2", "1.2.2", "Communication: PWD roads, railway lines, Air", "String", None, 300, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.3", "Connectivity to nearest railheads, highway, and airport", "Table 1.1", None, None),
                ("fld_1_2_3", "1.2.3", "Availability of power supply, water etc.", "String", None, 300, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.4", "Sources of power supply grid and industrial/domestic water", None, None, None),
                ("fld_1_2_4", "1.2.4", "Prominent physiographic features, drainage pattern, natural water courses, rainfall data, highest flood level", "Text", None, 1000, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.4", "Drainage, rivers, nalas, HFL, and rainfall characteristics", None, None, "Plate 2"),
                ("fld_1_2_5", "1.2.5", "Important surface features within the project area and major diversion or shifting involved", "Text", None, 1000, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.5", "Habitations, roads, waterbodies requiring shifting or diversion", None, None, "Plate 2"),
            ]),
            ("sec_1_3", "1.3", "Allotment Details", [
                ("fld_1_3_1", "1.3.1", "Name of the Allottee", "String", None, 200, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.5", "Legal name of allottee/prior allottee", None, "Annexure 1", None),
                ("fld_1_3_2", "1.3.2", "Details of allotment/vesting order", "String", None, 200, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.6", "Order number, date, and allocation terms", None, "Annexure 1", None),
                ("fld_1_3_3", "1.3.3", "Name and address of the applicant (Regd. Office, Principal Place of Business)", "String", None, 300, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.6", "Registered office and corporate address", None, "Annexure 4", None),
                ("fld_1_3_4", "1.3.4", "Name of the Previous Allottee of the Block", "String", None, 200, "CONDITIONAL", "Applicable for re-allocated / cancelled coal blocks", "AVAILABLE_FROM_KOYLADB", "P.6", "Name of previous entity prior to de-allocation", None, None, None),
                ("fld_1_3_5", "1.3.5", "Rated capacity and peak capacity as per allotment / allocation", "Float", "MTPA", 20, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.7", "Approved rated and peak capacity in MTPA", None, None, None),
            ])
        ]),
        ("ch_2", "3", "Chapter 2 — Exploration, Geology, Seam Sequence, Coal Quality and Reserve", 4, "P.8", [
            ("sec_2_1", "2.1", "Block Details", [
                ("fld_2_1_1", "2.1.1", "Particulars of adjacent area/blocks", "String", None, 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.8", "Surrounding leaseholds, working mines, virgin areas", None, None, "Plate 2"),
                ("fld_2_1_2", "2.1.2", "Name of the Geological Report with month and year of preparation", "String", None, 200, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.8", "Full title and preparation date of approved GR", None, "Annexure 2", None),
                ("fld_2_1_3", "2.1.3", "Name of the GR Preparing Agency", "String", None, 150, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.9", "CMPDI, MECL, GSI, or exploration agency", None, "Annexure 2", None),
                ("fld_2_1_4", "2.1.4", "Area in hectares", "Float", "Ha", 20, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.9", "Total geological block area in hectares", None, "Annexure 5", None),
                ("fld_2_1_5", "2.1.5", "KML file of the proposed lease/project area", "File", "WGS84", None, "MANDATORY", None, "REQUIRES_EXTERNAL_ATTACHMENT", "P.10", "DGPS boundary polygon in KML format", None, "Annexure 5", "Plate 2"),
            ]),
            ("sec_2_2", "2.2", "Exploration and Geology", [
                ("fld_2_2_1", "2.2.1", "Exploration status and borehole density", "Float", "BH/sq km", 30, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.11", "Total boreholes, aggregate meterage, grid density", "Table 2.1", None, "Plate 3"),
                ("fld_2_2_2", "2.2.2", "Regional geological setup and local geology of the block", "Text", None, 1500, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.12", "Regional formation, stratigraphy, basin architecture", None, None, "Plate 3"),
                ("fld_2_2_3", "2.2.3", "Geological structure (Strike, Dip direction, Dip amount, Faults with strike, dip, throws)", "String", "Degrees", 500, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.13", "Dip, strike, faults, throws, folds, igneous intrusions", None, None, "Plate 3, 4"),
                ("fld_2_2_4", "2.2.4", "Stratigraphic succession and lithological characteristics of formations", "Text", None, 1500, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.14", "Lithology of Barakar, Raniganj, Karharbari formations", "Table 2.2", None, "Plate 4"),
                ("fld_2_2_5", "2.2.5", "Seam sequence, thickness range (min, max, avg in meters) and parting thickness", "Float", "m", 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.15", "Seam wise thickness ranges and inter-seam partings", "Table 2.2", None, "Plate 5"),
                ("fld_2_2_6", "2.2.6", "Depth range of coal seams (minimum and maximum depth to floor in meters)", "Float", "m", 50, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.16", "Depth to roof and floor of workable seams", "Table 2.2", None, "Plate 4"),
                ("fld_2_2_7", "2.2.7", "Coal quality parameters (Grade, GCV kcal/kg, Ash %, Moisture %, VM %, FC %)", "Float", "kcal/kg, %", 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.17", "Proximate analysis, GCV, and gross calorific value grade", "Table 2.3", None, None),
                ("fld_2_2_8", "2.2.8", "Seam gas content / CBM potential / Spontaneous heating & crossing point temperature", "Float", "cum/t, °C", 100, "CONDITIONAL", "Applicable for gassy, deep, or spontaneous-combustion prone seams", "EXTRACTABLE_FROM_SOURCE", "P.18", "Gas content, crossing point temp, CPT/IPT values", None, None, None),
            ]),
            ("sec_2_3", "2.3", "Reserve Assessment", [
                ("fld_2_3_1", "2.3.1", "Resource estimation methodology (ISP Guidelines / UNFC system)", "String", None, 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.19", "Method of reserve estimation and UNFC classification", None, None, None),
                ("fld_2_3_2", "2.3.2", "Gross Geological Reserve of the block (Proved, Indicated, Inferred in MT)", "Float", "MT", 30, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.20", "Gross geological resource categorized by confidence", "Table 2.4", None, None),
                ("fld_2_3_3", "2.3.3", "Net Geological Reserve (after geological deduction for faults, washouts in MT)", "Float", "MT", 30, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.21", "Gross reserve minus geological deduction (faults, intrusions)", "Table 2.4", None, None),
                ("fld_2_3_4", "2.3.4", "Blocked Reserves / Resources (under statutory safety barriers, rivers, HFL, rail, roads)", "Float", "MT", 30, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.22", "Reserves sterilised under surface features/barriers", "Table 2.5", None, None),
                ("fld_2_3_5", "2.3.5", "Minable Reserve (in MT)", "Float", "MT", 30, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.23", "Net reserve minus blocked reserves", "Table 2.6", None, None),
                ("fld_2_3_6", "2.3.6", "Mining losses (fault losses, roof/floor contact losses, rib losses in MT)", "Float", "MT", 30, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.24", "Anticipated operational mining losses", "Table 2.6", None, None),
                ("fld_2_3_7", "2.3.7", "Extractable Reserve (in MT)", "Float", "MT", 30, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.25", "Minable reserve minus mining losses", "Table 2.6", None, None),
                ("fld_2_3_8", "2.3.8", "Overall Percentage of Extraction / Recovery Factor (%)", "Float", "%", 20, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.25", "Ratio of extractable to minable reserves in percentage", "Table 2.6", None, None),
                ("fld_2_3_9", "2.3.9", "Coal Resources Already Depleted / Extracted up to base date (in MT)", "Float", "MT", 30, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.26", "Cumulative prior extraction up to base date", "Table 2.6", None, None),
                ("fld_2_3_10", "2.3.10", "Balance Resource / Extractable Reserves available as on base date (in MT)", "Float", "MT", 30, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.26", "Extractable reserve minus depleted reserve", "Table 2.6", None, None),
                ("fld_2_3_11", "2.3.11", "Average Stripping Ratio (Volume of OB in Mcum to Coal in MT, cum/tonne)", "Float", "cum/tonne", 20, "CONDITIONAL", "Applicable for opencast and mixed mines", "DERIVABLE_FROM_KOYLADB", "P.27", "Ratio of total OB volume to coal tonnage", "Table 2.6", None, None),
            ])
        ]),
        ("ch_3", "4", "Chapter 3 — Mining", 5, "P.28", [
            ("sec_3_1", "3.1", "Mining Method", [
                ("fld_3_1_1", "3.1.1", "Proposed Mining Method (Opencast / Underground / Mixed) & Justification", "String", None, 500, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.28", "Opencast, underground, or combined with technical justification", None, None, "Plate 6A / 6B"),
            ]),
            ("sec_3_2", "3.2", "Production Capacity", [
                ("fld_3_1_2", "3.1.2", "Target Production Capacity (Rated and Peak capacity in MTPA)", "Float", "MTPA", 30, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.29", "Target rated and peak annual coal production", "Table 3.1", None, None),
            ]),
            ("sec_3_3", "3.3", "Life of Mine", [
                ("fld_3_1_3", "3.1.3", "Life of Mine (LOM in years)", "Float", "Years", 20, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.30", "Total extractable reserve divided by rated capacity", None, None, None),
            ]),
            ("sec_3_4", "3.4", "Workings Geometry", [
                ("fld_3_1_4", "3.1.4", "Mine Geometry: Bench height, width, slope angles, quarry limits / Panel dimensions", "String", "m, Degrees", 500, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.31", "Bench heights, overall pit slope, panel dimensions", None, None, "Plate 6A / 6B"),
            ]),
            ("sec_3_5", "3.5", "Equipment Fleet", [
                ("fld_3_1_5", "3.1.5", "Heavy Earth Moving Machinery (HEMM) / Equipment sizing, selection & fleet deployment", "Table", "No., Capacity", None, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.32", "List of shovels, dumpers, drills, dozers, continuous miners", "Table 3.2", None, None),
            ]),
            ("sec_3_6", "3.6", "Production Schedule", [
                ("fld_3_1_6", "3.1.6", "Year-wise production schedule and Overburden (OB) removal schedule (Years 1 to 5)", "Table", "MT, Mcum", None, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.33", "Five-year yearwise production and OB schedule", "Table 3.1", None, "Plate 6"),
            ]),
            ("sec_3_7", "3.7", "Mine Drainage", [
                ("fld_3_1_7", "3.1.7", "Mine drainage, peak pumping capacity (cum/hr), sump design, runoff handling", "String", "cum/hr", 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.34", "Peak inflow, sump capacity, pump ratings, discharge arrangement", None, None, "Plate 6A / 6B"),
            ])
        ]),
        ("ch_4", "5", "Chapter 4 — Safety Management", 6, "P.35", [
            ("sec_4_1", "4.1", "Risk Assessment", [
                ("fld_4_1_1", "4.1.1", "Risk Assessment & Safety Management Plan (SMP) as per DGMS guidelines", "Text", None, 1000, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.35", "Hazard identification, risk score matrix, control measures per DGMS", None, None, None),
            ]),
            ("sec_4_2", "4.2", "Hazard Control", [
                ("fld_4_1_2", "4.1.2", "Gas categorization (Degree I/II/III) OR Slope & Dump stability monitoring", "String", None, 300, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.36", "Gassiness degree for UG or slope stability radar/piezometers for OC", None, None, "Plate 6A / 6B"),
            ]),
            ("sec_4_3", "4.3", "Ground Control", [
                ("fld_4_1_3", "4.1.3", "Strata control plan / RMR (for UG) OR Highwall & dump monitoring instrumentation (for OC)", "String", None, 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.37", "Rock mass rating, support system or slope monitoring instrumentation", None, None, "Plate 6A / 6B"),
            ]),
            ("sec_4_4", "4.4", "Hazard Prevention", [
                ("fld_4_1_4", "4.1.4", "Fire management, spontaneous combustion prevention, coal dust & inundation control", "Text", None, 800, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.37", "Blanketing, water infusion, stone dust barriers, danger zone demarcation", None, None, None),
            ]),
            ("sec_4_5", "4.5", "Emergency Preparedness", [
                ("fld_4_1_5", "4.1.5", "Emergency preparedness, disaster management plan, and rescue arrangements", "Text", None, 800, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.38", "Disaster management scheme, escape routes, mutual aid with rescue station", None, None, None),
            ])
        ]),
        ("ch_5", "6", "Chapter 5 — Infrastructure Facilities proposed and their Location", 7, "P.38", [
            ("sec_5_1", "5.1", "Coal Handling & FMC", [
                ("fld_5_1_1", "5.1.1", "Coal Handling Plant (CHP), Crushing, and First Mile Connectivity (FMC) network", "String", "TPH, km", 300, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.38", "Crusher capacity, belt conveyors, silo loading, FMC compliance", None, None, "Plate 1"),
            ]),
            ("sec_5_2", "5.2", "Railway Siding", [
                ("fld_5_1_2", "5.1.2", "Railway Siding, Track Layout, Rapid Loading System (RLS), Silo Facilities", "String", "Rakes/day", 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.39", "Track take-off, holding capacity, in-motion weighbridge, RLS", None, None, "Plate 1"),
            ]),
            ("sec_5_3", "5.3", "Workshop & Stores", [
                ("fld_5_1_3", "5.1.3", "Workshop facilities, HEMM maintenance bays, store yards, fuel station", "String", None, 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.40", "Bay sizes, overhead cranes, lube bay, bulk diesel storage", None, None, "Plate 2"),
            ]),
            ("sec_5_4", "5.4", "Power Distribution", [
                ("fld_5_1_4", "5.1.4", "Power distribution system, main sub-station capacity, transmission lines, DG backup", "String", "MVA, kV", 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.40", "Substation capacity, supply voltage, step-down transformers, DG sets", None, None, "Plate 2"),
            ]),
            ("sec_5_5", "5.5", "Magazine", [
                ("fld_5_1_5", "5.1.5", "Explosive magazine, blast shelter, ANFO / bulk emulsion shed (PESO norms)", "String", "Tonnes", 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.41", "Magazine license capacity, safety distances, PESO conformity", None, None, "Plate 2"),
            ]),
            ("sec_5_6", "5.6", "Water & Effluent", [
                ("fld_5_1_6", "5.1.6", "Industrial effluent treatment (ETP), sewage treatment (STP), and water supply", "String", "KLD", 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.41", "ETP/STP capacity, recycling system, oil-grease trap, domestic RO plant", None, None, "Plate 2"),
            ]),
            ("sec_5_7", "5.7", "Service Buildings", [
                ("fld_5_1_7", "5.1.7", "Administrative buildings, occupational health centre (OHC), VTC, canteen", "String", None, 300, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.42", "Mine office, first aid station, training centre, statutory amenities", None, None, "Plate 2"),
            ])
        ]),
        ("ch_6", "7", "Chapter 6 — Land Requirement", 8, "P.42", [
            ("sec_6_1", "6.1", "Total Land", [
                ("fld_6_1_1", "6.1.1", "Total project land requirement", "Float", "Ha", 20, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.42", "Total land within project boundary in hectares", "Table 6.1", None, None),
            ]),
            ("sec_6_2", "6.2", "Land Classification", [
                ("fld_6_1_2", "6.1.2", "Land classification breakdown: Forest, Private/Tenancy, Govt/Revenue, Waste/GMK", "Float", "Ha", 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.43", "Breakdown by legal ownership type", "Table 6.1", None, None),
            ]),
            ("sec_6_3", "6.3", "Land Use Schedule", [
                ("fld_6_1_3", "6.1.3", "Activity-wise land utilization schedule: Quarry, OB Dumps, CHP, Green Belt, Safety", "Float", "Ha", 100, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.44", "Area allocated to quarry, external dump, infrastructure, roads", "Table 6.1", None, "Plate 2"),
            ]),
            ("sec_6_4", "6.4", "Clearance Status", [
                ("fld_6_1_4", "6.1.4", "Status of land acquisition, Stage-I / Stage-II forest clearance, physical possession", "String", None, 400, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.45", "CBA/LAA notification status, FC Stage I/II status, possession details", None, "Annexure 8", None),
            ])
        ]),
        ("ch_7", "8", "Chapter 7 — Environment Management", 9, "P.46", [
            ("sec_7_1", "7.1", "Baseline Environment", [
                ("fld_7_1_1", "7.1.1", "Baseline environmental quality (Micro-meteorology, Air, Noise, Water, Soil, Ecology)", "Text", None, 1000, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.46", "Baseline environmental monitoring summary", None, "Annexure 7", None),
            ]),
            ("sec_7_2", "7.2", "Mitigation Plan", [
                ("fld_7_1_2", "7.1.2", "Environmental pollution mitigation measures (Water mist, garland drains, settling ponds)", "Text", None, 1000, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.47", "Air, water, noise, vibration abatement arrangements", None, None, None),
            ]),
            ("sec_7_3", "7.3", "Afforestation", [
                ("fld_7_1_3", "7.1.3", "Progressive green belt development, topsoil preservation, afforestation density", "Text", "Ha, Trees/Ha", 800, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.48", "Green belt width, plantation schedule, topsoil handling", None, None, "Plate 7"),
            ]),
            ("sec_7_4", "7.4", "Socio-Economics & R&R", [
                ("fld_7_1_4", "7.1.4", "Socio-economic profile, R&R Plan as per RFCTLARR Act 2013, CSR commitments", "Text", None, 1000, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.49", "Project affected families, resettlement package, community development", None, None, None),
            ])
        ]),
        ("ch_8", "9", "Chapter 8 — Progressive and Final Mine Closure Plan", 10, "P.50", [
            ("sec_8_1", "8.1", "Closure Framework", [
                ("fld_8_1_1", "8.1.1", "Mine closure framework, baseline environmental data, and closure principles", "Text", None, 1000, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.50", "Statutory guidelines, closure objectives, post-closure land use", None, None, "Plate 7, 8"),
            ]),
            ("sec_8_2", "8.2", "Progressive Closure", [
                ("fld_8_2_1", "8.2.1", "Progressive closure schedule: Backfilling, technical & biological reclamation", "Table", "Ha, Mcum", None, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.51", "Year-wise backfilling, re-profiling, topsoil spreading, plantation", "Table 8.1", None, "Plate 7"),
            ]),
            ("sec_8_3", "8.3", "Final Closure", [
                ("fld_8_3_1", "8.3.1", "Final mine closure: Infrastructure decommissioning, sealing entries, fencing voids", "Text", None, 1000, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.52", "Plant dismantling, sealing shafts/inclines, water body retention", None, None, "Plate 8"),
            ]),
            ("sec_8_4", "8.4", "Financial Assurance & Escrow", [
                ("fld_8_4_1", "8.4.1", "Mine closure cost estimation & Escrow Account annual deposit calculation", "Float", "Lakh INR", 30, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.53", "Per hectare base cost multiplied by project area with WPI escalation and compound annuity formula", "Table 8.2", "Annexure 9", None),
                ("fld_8_4_2", "8.4.2", "Mandatory 25% Earmarking for Just Transition & Community Development", "Float", "Lakh INR", 30, "MANDATORY", "Universal statutory requirement under Section 8.4.2 of 2025 Guidelines", "DERIVABLE_FROM_KOYLADB", "P.54", "Minimum 25% of annual escrow allocation dedicated to just transition and community sustainability", "Table 8.2", None, None),
            ]),
            ("sec_8_5", "8.5", "Post-Closure Monitoring", [
                ("fld_8_5_1", "8.5.1", "Post-closure environmental monitoring and maintenance schedule (3–5 years)", "Text", "Years", 500, "MANDATORY", None, "EXTRACTABLE_FROM_SOURCE", "P.55", "3-5 year post-closure air, water, flora monitoring until lease surrender", None, None, None),
            ])
        ])
    ]

    for ch_id, ch_off_id, ch_label, ch_seq, ch_page, sections in chapters_def:
        nodes.append({
            "internal_id": ch_id,
            "official_id": ch_off_id,
            "exact_official_label": ch_label,
            "parent_id": None,
            "node_type": "CHAPTER",
            "sequence": ch_seq,
            "required_status": "MANDATORY",
            "applicability_condition": None,
            "data_type": "Chapter",
            "unit": None,
            "max_words_or_limits": None,
            "official_instruction": f"Chapter {ch_off_id} of Appendix-I.",
            "source_page": ch_page,
            "source_reference": f"Appendix-I Item {ch_off_id}",
            "table_reference": None,
            "annexure_reference": None,
            "plate_reference": None,
            "koyla_mapping_status": "AVAILABLE_FROM_KOYLADB"
        })

        for sec_id, sec_off_id, sec_label, fields in sections:
            nodes.append({
                "internal_id": sec_id,
                "official_id": sec_off_id,
                "exact_official_label": sec_label,
                "parent_id": ch_id,
                "node_type": "SECTION",
                "sequence": int(sec_off_id.split(".")[-1]),
                "required_status": "MANDATORY",
                "applicability_condition": None,
                "data_type": "Section",
                "unit": None,
                "max_words_or_limits": None,
                "official_instruction": f"Section {sec_off_id} of Appendix-I.",
                "source_page": ch_page,
                "source_reference": f"Appendix-I Section {sec_off_id}",
                "table_reference": None,
                "annexure_reference": None,
                "plate_reference": None,
                "koyla_mapping_status": "AVAILABLE_FROM_KOYLADB"
            })

            for f_seq, (fid, f_off_id, f_label, dt, unit, limits, req, app, km, sp, inst, tbl_ref, ann_ref, plt_ref) in enumerate(fields, start=1):
                nodes.append({
                    "internal_id": fid,
                    "official_id": f_off_id,
                    "exact_official_label": f_label,
                    "parent_id": sec_id,
                    "node_type": "FIELD",
                    "sequence": f_seq,
                    "required_status": req,
                    "applicability_condition": app,
                    "data_type": dt,
                    "unit": unit,
                    "max_words_or_limits": limits,
                    "official_instruction": inst,
                    "source_page": sp,
                    "source_reference": f"Appendix-I Field {f_off_id}",
                    "table_reference": tbl_ref,
                    "annexure_reference": ann_ref,
                    "plate_reference": plt_ref,
                    "koyla_mapping_status": km
                })

    # Prescribed Official Tables (12 Tables)
    tables_def = [
        ("tbl_1_1", "Table 1.1", "Communication and Location Infrastructure Summary", "ch_1", 1, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.3", "Summary of road, rail, air, and power infrastructure.", [
            {"name": "facility_type", "label": "Facility Type", "unit": None, "type": "String"},
            {"name": "name_route", "label": "Name / Route Description", "unit": None, "type": "String"},
            {"name": "distance_km", "label": "Distance from Pit Head", "unit": "km", "type": "Float"},
            {"name": "coordinates", "label": "Coordinates / Remarks", "unit": None, "type": "String"}
        ]),
        ("tbl_2_1", "Table 2.1", "Borehole Exploration Drilling Summary and Grid Density", "ch_2", 2, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.11", "Summary of exploratory drilling density by series.", [
            {"name": "series_name", "label": "Borehole Series", "unit": None, "type": "String"},
            {"name": "num_boreholes", "label": "Number of Boreholes", "unit": "Nos", "type": "Integer"},
            {"name": "total_meterage", "label": "Total Meterage Drilled", "unit": "m", "type": "Float"},
            {"name": "grid_density", "label": "Borehole Grid Density", "unit": "BH/sq km", "type": "Float"}
        ]),
        ("tbl_2_2", "Table 2.2", "Stratigraphic Succession, Seam Sequence, Depth and Thickness Range", "ch_2", 3, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.15", "Seam sequence, thickness, partings, and depth ranges.", [
            {"name": "seam_name", "label": "Seam Name / ID", "unit": None, "type": "String"},
            {"name": "depth_roof_m", "label": "Roof Depth (Min-Max)", "unit": "m", "type": "String"},
            {"name": "depth_floor_m", "label": "Floor Depth (Min-Max)", "unit": "m", "type": "String"},
            {"name": "thickness_m", "label": "Clean Coal Thickness", "unit": "m", "type": "Float"},
            {"name": "parting_m", "label": "Inter-seam Parting", "unit": "m", "type": "Float"}
        ]),
        ("tbl_2_3", "Table 2.3", "Band-by-Band Coal Quality, Proximate Analysis, and Grade Distribution", "ch_2", 4, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.17", "Proximate analysis and GCV grade distribution by seam.", [
            {"name": "seam_name", "label": "Seam Name", "unit": None, "type": "String"},
            {"name": "moisture_pct", "label": "Moisture %", "unit": "%", "type": "Float"},
            {"name": "ash_pct", "label": "Ash %", "unit": "%", "type": "Float"},
            {"name": "vm_pct", "label": "Volatile Matter %", "unit": "%", "type": "Float"},
            {"name": "fc_pct", "label": "Fixed Carbon %", "unit": "%", "type": "Float"},
            {"name": "gcv_kcal_kg", "label": "Gross Calorific Value", "unit": "kcal/kg", "type": "Float"},
            {"name": "coal_grade", "label": "Coal Grade (G1-G17)", "unit": None, "type": "String"}
        ]),
        ("tbl_2_4", "Table 2.4", "Gross and Net Geological Reserves Categorization", "ch_2", 5, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.20", "Gross and net reserves per UNFC/ISP guidelines.", [
            {"name": "seam_name", "label": "Seam Name", "unit": None, "type": "String"},
            {"name": "proved_mt", "label": "Proved Reserves", "unit": "MT", "type": "Float"},
            {"name": "indicated_mt", "label": "Indicated Reserves", "unit": "MT", "type": "Float"},
            {"name": "inferred_mt", "label": "Inferred Reserves", "unit": "MT", "type": "Float"},
            {"name": "gross_total_mt", "label": "Gross Total Geological", "unit": "MT", "type": "Float"},
            {"name": "geological_deduction_mt", "label": "Geological Deductions", "unit": "MT", "type": "Float"},
            {"name": "net_geological_mt", "label": "Net Geological Reserves", "unit": "MT", "type": "Float"}
        ]),
        ("tbl_2_5", "Table 2.5", "Blocked Coal Reserves Categorized by Constraint Category", "ch_2", 6, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.22", "Sterilized and blocked coal resources categorized by surface constraint.", [
            {"name": "seam_name", "label": "Seam Name", "unit": None, "type": "String"},
            {"name": "barrier_mt", "label": "Boundary / Statutory Barriers", "unit": "MT", "type": "Float"},
            {"name": "water_hfl_mt", "label": "River / Nala / HFL Zones", "unit": "MT", "type": "Float"},
            {"name": "infra_rail_road_mt", "label": "Railway / Road / Powerlines", "unit": "MT", "type": "Float"},
            {"name": "habitations_mt", "label": "Villages / Habitations", "unit": "MT", "type": "Float"},
            {"name": "total_blocked_mt", "label": "Total Blocked Resources", "unit": "MT", "type": "Float"}
        ]),
        ("tbl_2_6", "Table 2.6", "Minable, Extractable, Depleted, and Balance Reserves Reconciliation", "ch_2", 7, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.25", "Reserve reconciliation from net to balance reserves.", [
            {"name": "seam_name", "label": "Seam Name", "unit": None, "type": "String"},
            {"name": "minable_mt", "label": "Minable Reserves", "unit": "MT", "type": "Float"},
            {"name": "mining_loss_mt", "label": "Mining Losses", "unit": "MT", "type": "Float"},
            {"name": "extractable_mt", "label": "Extractable Reserves", "unit": "MT", "type": "Float"},
            {"name": "depleted_mt", "label": "Prior Depletion / Extracted", "unit": "MT", "type": "Float"},
            {"name": "balance_mt", "label": "Balance Extractable", "unit": "MT", "type": "Float"},
            {"name": "stripping_ratio", "label": "Stripping Ratio", "unit": "cum/tonne", "type": "Float"}
        ]),
        ("tbl_3_1", "Table 3.1", "Year-wise Production and Overburden (OB) Removal Schedule", "ch_3", 8, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.33", "Year 1 to 5 production and waste handling schedule.", [
            {"name": "period_year", "label": "Operating Year / Block", "unit": None, "type": "String"},
            {"name": "coal_prod_mt", "label": "Coal Production", "unit": "MT", "type": "Float"},
            {"name": "ob_removal_mcum", "label": "OB Removal Volume", "unit": "Mcum", "type": "Float"},
            {"name": "stripping_ratio", "label": "Annual Stripping Ratio", "unit": "cum/tonne", "type": "Float"}
        ]),
        ("tbl_3_2", "Table 3.2", "Heavy Earth Moving Machinery (HEMM) Equipment Fleet Deployment", "ch_3", 9, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.32", "Mining equipment fleet sizing, capacities, and numbers.", [
            {"name": "equipment_name", "label": "Equipment Type / Description", "unit": None, "type": "String"},
            {"name": "bucket_capacity", "label": "Bucket / Payload Capacity", "unit": "cum / Tonnes", "type": "String"},
            {"name": "number_required", "label": "Calculated Fleet Requirement", "unit": "Nos", "type": "Integer"},
            {"name": "number_deployed", "label": "Proposed / Deployed Units", "unit": "Nos", "type": "Integer"},
            {"name": "availability_pct", "label": "Standard Availability %", "unit": "%", "type": "Float"}
        ]),
        ("tbl_6_1", "Table 6.1", "Land Requirement and Legal Classification Status", "ch_6", 10, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.43", "Activity-wise and legal category-wise land breakdown.", [
            {"name": "land_category", "label": "Land Ownership Category", "unit": None, "type": "String"},
            {"name": "quarry_area_ha", "label": "Excavation / Quarry Area", "unit": "Ha", "type": "Float"},
            {"name": "ob_dump_area_ha", "label": "External OB Dump Area", "unit": "Ha", "type": "Float"},
            {"name": "infra_area_ha", "label": "Infrastructure & Plant Area", "unit": "Ha", "type": "Float"},
            {"name": "greenbelt_safety_ha", "label": "Green Belt & Safety Zone", "unit": "Ha", "type": "Float"},
            {"name": "total_area_ha", "label": "Total Land Area", "unit": "Ha", "type": "Float"}
        ]),
        ("tbl_8_1", "Table 8.1", "Progressive Mine Closure Technical and Biological Reclamation Schedule", "ch_8", 11, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.51", "5-year progressive physical and biological reclamation plan.", [
            {"name": "schedule_year", "label": "Year of Operation", "unit": None, "type": "String"},
            {"name": "backfilled_ha", "label": "Area Backfilled", "unit": "Ha", "type": "Float"},
            {"name": "ob_handled_mcum", "label": "OB Volume Handled", "unit": "Mcum", "type": "Float"},
            {"name": "revegetated_ha", "label": "Biological Reclamation / Afforested", "unit": "Ha", "type": "Float"},
            {"name": "trees_planted", "label": "Saplings Planted", "unit": "Nos", "type": "Integer"}
        ]),
        ("tbl_8_2", "Table 8.2", "Mine Closure Escrow Account Annual Deposit Calculation Table", "ch_8", 12, "MANDATORY", None, "DERIVABLE_FROM_KOYLADB", "P.53", "Escrow calculation with mandatory 25% Just Transition fund.", [
            {"name": "year_number", "label": "Operating Year", "unit": None, "type": "Integer"},
            {"name": "project_area_ha", "label": "Cumulative Project Area", "unit": "Ha", "type": "Float"},
            {"name": "base_rate_lakh_ha", "label": "Statutory Rate / Ha", "unit": "Lakh INR/Ha", "type": "Float"},
            {"name": "escalation_factor", "label": "WPI Inflation Multiplier", "unit": None, "type": "Float"},
            {"name": "annual_escrow_deposit_lakh", "label": "Gross Annual Escrow Deposit", "unit": "Lakh INR", "type": "Float"},
            {"name": "just_transition_fund_lakh", "label": "25% Just Transition Fund Earmarking", "unit": "Lakh INR", "type": "Float"}
        ])
    ]

    for tid, t_off_id, t_label, pid, seq, req, app, km, sp, inst, cols in tables_def:
        nodes.append({
            "internal_id": tid,
            "official_id": t_off_id,
            "exact_official_label": t_label,
            "parent_id": pid,
            "node_type": "TABLE",
            "sequence": seq,
            "required_status": req,
            "applicability_condition": app,
            "data_type": "Table",
            "unit": None,
            "max_words_or_limits": None,
            "official_instruction": inst,
            "source_page": sp,
            "source_reference": f"Appendix-I {t_off_id}",
            "table_reference": t_off_id,
            "annexure_reference": None,
            "plate_reference": None,
            "koyla_mapping_status": km,
            "columns": cols
        })

    # Technical Plates / Plans / Drawings (9 Plates with Method Conditionality)
    plates_def = [
        ("plt_1", "Plate 1", "Key Plan / Location and Regional Communication Plan", "ch_1", 1, "MANDATORY", None, "1:50,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "Cover", "Survey of India topo-sheet based key plan showing regional roads, rail connections, and lease boundary."),
        ("plt_2", "Plate 2", "Surface Plan / Topographical Plan", "ch_1", 2, "MANDATORY", None, "1:5,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "P.3", "Surface features, DGPS coordinates, contours at 1m/2m interval, 100m statutory safety buffer, watercourses."),
        ("plt_3", "Plate 3", "Geological Plan with Borehole Locations & Outcrop Lines", "ch_2", 3, "MANDATORY", None, "1:5,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "P.11", "Borehole collars, seam incrops/outcrops, faults with throw and dip, geological structural trends."),
        ("plt_4", "Plate 4", "Geological Cross-Sections Across Strike and Dip", "ch_2", 4, "MANDATORY", None, "1:2,000 / 1:5,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "P.14", "Representative cross-sections along exploration boreholes showing seam correlation and structural faults."),
        ("plt_5", "Plate 5", "Seam Floor Contour Plan and Seam Folio / Isochore Plans", "ch_2", 5, "MANDATORY", None, "1:5,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "P.15", "Seam floor RL contours, isopach/isochore thickness contours for all workable horizons."),
        ("plt_6a", "Plate 6A", "Opencast Mining Layout Plan (Quarry limits & Dumps)", "ch_3", 6, "CONDITIONAL", "Applicable for Opencast and Mixed Mines Only", "1:5,000", True, False, False, "REQUIRES_EXTERNAL_ATTACHMENT", "P.31", "Quarry pit limit, ultimate pit boundary, internal and external OB dumps, haul road alignments."),
        ("plt_6b", "Plate 6B", "Underground Mining Layout Plan (Panels, Entries, Ventilation)", "ch_3", 7, "CONDITIONAL", "Applicable for Underground and Mixed Mines Only", "1:5,000", False, True, False, "REQUIRES_EXTERNAL_ATTACHMENT", "P.31", "Shaft/incline locations, main development headings, panel boundaries, ventilation intake and return circuits."),
        ("plt_7", "Plate 7", "Progressive Mine Closure Plan (Year 1 to 5 Stages)", "ch_8", 8, "MANDATORY", None, "1:5,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "P.51", "Year-wise staging of backfilling, void advancement, biological reclamation, and peripheral greenbelt."),
        ("plt_8", "Plate 8", "Final Land Use Plan on Mine Closure", "ch_8", 9, "MANDATORY", None, "1:5,000", True, True, True, "REQUIRES_EXTERNAL_ATTACHMENT", "P.52", "Final post-mining topography, water reservoir void, stabilized vegetated dumps, repurposed infrastructure.")
    ]

    for pid, p_off_id, p_label, parent_ch, seq, req, app, scale, r_oc, r_ug, r_both, km, sp, inst in plates_def:
        nodes.append({
            "internal_id": pid,
            "official_id": p_off_id,
            "exact_official_label": p_label,
            "parent_id": parent_ch,
            "node_type": "PLATE",
            "sequence": seq,
            "required_status": req,
            "applicability_condition": app,
            "data_type": "Drawing",
            "unit": "Scale",
            "max_words_or_limits": scale,
            "official_instruction": inst,
            "source_page": sp,
            "source_reference": f"Appendix-I {p_off_id}",
            "table_reference": None,
            "annexure_reference": None,
            "plate_reference": p_off_id,
            "koyla_mapping_status": km,
            "plate_metadata": {
                "scale_requirement": scale,
                "required_for_oc": r_oc,
                "required_for_ug": r_ug,
                "required_for_both": r_both,
                "legend_requirement": True,
                "north_direction_requirement": True,
                "grid_requirement": True,
                "coordinate_requirement": "WGS-84 / UTM",
                "boundary_requirement": "DGPS demarcated project boundary"
            }
        })

    # Prescribed Statutory & Conditional Annexures (13 Annexures)
    annexures_def = [
        ("ann_1", "Annexure 1", "Copy of Allotment Order / Vesting Order / Mining Lease deed", "root_front_matter", 1, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.6", "Certified true copy of statutory allotment order issued by Ministry of Coal."),
        ("ann_2", "Annexure 2", "Approval letter of Geological Report by Competent Authority", "root_front_matter", 2, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.8", "Formal letter conveying competent authority approval of the Geological Report."),
        ("ann_3", "Annexure 3", "Certificate of Qualified Person (QP) under Rule 22C MCR 1960", "root_front_matter", 3, "MANDATORY", None, "REQUIRES_HUMAN_INPUT", "Execution", "Statutory recognition and competency certificate of Qualified Person."),
        ("ann_4", "Annexure 4", "Corporate Board Resolution & Power of Attorney of Signatory", "root_front_matter", 4, "MANDATORY", "Corporate Allottees", "REQUIRES_EXTERNAL_ATTACHMENT", "P.6", "Certified extract of Board Resolution authorizing the signatory to submit the Mining Plan."),
        ("ann_5", "Annexure 5", "DGPS Boundary Survey Report with pillar coordinates", "root_front_matter", 5, "MANDATORY", None, "REQUIRES_EXTERNAL_ATTACHMENT", "P.10", "Authenticated DGPS survey map and coordinate schedule certified by authorized surveying agency."),
        ("ann_6", "Annexure 6", "Prior Approval / Earlier Mining Plan Approval letters", "root_front_matter", 6, "CONDITIONAL", "Applicable for modified/revised mining plans under Rule 22E", "AVAILABLE_FROM_KOYLADB", "P.1", "Copies of previous approval letters issued by CCO / MoC."),
        ("ann_7", "Annexure 7", "Terms of Reference (ToR) / Environmental Clearance (EC) Status", "root_front_matter", 7, "CONDITIONAL", "Applicable if prior environmental clearances have been issued", "AVAILABLE_FROM_KOYLADB", "P.46", "ToR letter or Environmental Clearance order from MoEFCC."),
        ("ann_8", "Annexure 8", "Stage-I / Stage-II Forest Clearance Status copy", "root_front_matter", 8, "CONDITIONAL", "Applicable if forest land is involved in the lease area", "AVAILABLE_FROM_KOYLADB", "P.45", "In-principle Stage-I or formal Stage-II Forest Clearance letters from MoEFCC."),
        ("ann_9", "Annexure 9", "Draft Escrow Agreement for Mine Closure Plan with Bank and CCO", "root_front_matter", 9, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.53", "Standard tripartite Escrow Agreement draft between allottee, scheduled bank, and Coal Controller."),
        ("ann_10", "Annexure 10", "QCI-NABET Accreditation Certificate of MPPA", "root_front_matter", 10, "CONDITIONAL", "Applicable if prepared by an accredited Mining Plan Preparing Agency", "REQUIRES_HUMAN_INPUT", "Cover", "Valid accreditation certificate of MPPA issued by QCI-NABET."),
        ("ann_11", "Annexure 11", "Schedule of Mine Closure Implementation Activity Chart", "root_front_matter", 11, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "P.51", "Bar chart / Gantt schedule of progressive closure, void management, and technical reclamation."),
        ("ann_12", "Annexure 12", "Expert Review / Peer Review Report by Accredited Agency", "root_front_matter", 12, "MANDATORY", None, "AVAILABLE_FROM_KOYLADB", "Execution", "Internal or peer review report on technical viability and DGMS safety compliance."),
        ("ann_13", "Annexure 13", "Other Statutory Documents / State Clearances (if any)", "root_front_matter", 13, "OPTIONAL", "Contextual statutory attachments", "AVAILABLE_FROM_KOYLADB", "Various", "Groundwater clearance, SPCB consent, or other state statutory clearances.")
    ]

    for aid, a_off_id, a_label, pid, seq, req, app, km, sp, inst in annexures_def:
        nodes.append({
            "internal_id": aid,
            "official_id": a_off_id,
            "exact_official_label": a_label,
            "parent_id": pid,
            "node_type": "ANNEXURE",
            "sequence": seq,
            "required_status": req,
            "applicability_condition": app,
            "data_type": "File",
            "unit": None,
            "max_words_or_limits": None,
            "official_instruction": inst,
            "source_page": sp,
            "source_reference": f"Appendix-I {a_off_id}",
            "table_reference": None,
            "annexure_reference": a_off_id,
            "plate_reference": None,
            "koyla_mapping_status": km
        })

    # Prescribed Execution Certifications (4 Blocks)
    certs_def = [
        ("cert_qp", None, "Certificate of Qualified Person (Rule 22C MCR 1960)", "root_front_matter", 1, "MANDATORY", None, "prepared_by", "REQUIRES_HUMAN_INPUT", "Execution", "Undertaking that Mining Plan is prepared in accordance with MCR 1960 and approved Geological Report."),
        ("cert_mppa", None, "Certificate of Mining Plan Preparing Agency (MPPA)", "root_front_matter", 2, "CONDITIONAL", "Applicable when prepared through accredited MPPA", "certified_by", "REQUIRES_HUMAN_INPUT", "Execution", "Certification that agency holds valid QCI-NABET accreditation and verified field data."),
        ("cert_allottee", None, "Undertaking by the Project Proponent / Allottee", "root_front_matter", 3, "MANDATORY", None, "verified_by", "REQUIRES_HUMAN_INPUT", "Execution", "Undertaking by applicant/allottee committing to abide by approved plan, DGMS norms, and escrow funding."),
        ("cert_board", None, "Resolution of the Board of Directors / Authorized Signatory Endorsement", "root_front_matter", 4, "MANDATORY", None, "authorized_by", "REQUIRES_EXTERNAL_ATTACHMENT", "Execution", "Corporate resolution authorizing signatory and formally submitting the plan for CCO scrutiny.")
    ]

    for cid, c_off_id, c_label, pid, seq, req, app, role, km, sp, inst in certs_def:
        nodes.append({
            "internal_id": cid,
            "official_id": c_off_id,
            "exact_official_label": c_label,
            "parent_id": pid,
            "node_type": "CERTIFICATION",
            "sequence": seq,
            "required_status": req,
            "applicability_condition": app,
            "data_type": "Certification",
            "unit": None,
            "max_words_or_limits": None,
            "official_instruction": inst,
            "source_page": sp,
            "source_reference": "Appendix-I Execution Requirements",
            "table_reference": None,
            "annexure_reference": None,
            "plate_reference": None,
            "koyla_mapping_status": km,
            "certification_metadata": {
                "signatory_role": role,
                "supported_states": ["SYSTEM_GENERATED", "HUMAN_VERIFIED", "AUTHORIZED_SIGNED", "AUTHORITY_APPROVED"]
            }
        })

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "format_id": "MINING_PLAN_AND_CLOSURE_PLAN_2025",
        "issuing_authority": "Ministry of Coal / Coal Controller Organisation (CCO)",
        "document_title": "Guidelines for preparation of Mining Plan and Mine Closure Plan for Coal and Lignite Blocks, 2025",
        "om_number": "F.No. CPAM-34011/28/2019-CPAM [E-343762]",
        "om_date": "2025-01-31",
        "guideline_year": 2025,
        "effective_status": "ACTIVE_STATUTORY",
        "official_source_url": "https://coalcontroller.gov.in/files/guidelines-acts-documents/mp-guidelines-31012025_0.pdf",
        "source_document_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "retrieved_at": "2026-09-18T10:00:00Z",
        "superseded_by": None,
        "format_tier": "STATUTORY",
        "nodes": nodes
    }

    output_path = os.path.join("backend", "app", "services", "reports", "mining_plan_2025_schema.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"Generated official schema at {output_path} with {len(nodes)} total nodes.")

if __name__ == "__main__":
    build_schema()
