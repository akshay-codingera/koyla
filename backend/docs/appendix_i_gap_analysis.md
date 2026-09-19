# Gap Analysis: Implementation vs Authoritative Appendix-I Specification

**Governing Reference**: Ministry of Coal / CCO OM F.No. CPAM-34011/28/2019-CPAM [E-343762] dated 31 January 2025

## 1. Structural Comparison Summary

| Structural Component | Previous Implementation | Authoritative Appendix-I Inventory | Reconciliation Status |
| :--- | :--- | :--- | :--- |
| **Chapter 1 Parameters** | 20 fields (1.1.1–1.3.5) | 67 parameters (1.1.1–1.1.6, 1.2.1–1.2.5, 1.3.1–1.3.9, 1.4.1–1.4.13, 1.5.1–1.5.26, 1.6.1–1.6.8) | `MISSING_FROM_IMPLEMENTATION` (47 parameters missing). Fixed in current pass. |
| **Chapter 2 Parameters** | 28 fields (2.1.1–2.3.11) | 38 parameters (2.1.1–2.1.14, 2.2.1–2.2.24) | `IMPLEMENTED_INCORRECTLY` (Old 2.3 renumbered to official 2.1 and 2.2). Fixed. |
| **Chapter 3 Parameters** | 15 fields (3.1.1–3.1.7) | 13 parameters (3.1.1–3.1.13) | `IMPLEMENTED_INCORRECTLY` (Old table items pruned, remapped to 3.1.1–3.1.13). Fixed. |
| **Chapter 4 Parameters** | 11 fields (4.1.1–4.1.5) | 2 parameters (4.1.1, 4.1.2) | `IMPLEMENTED_INCORRECTLY` (Consolidated to official 4.1.1 and 4.1.2). Fixed. |
| **Chapter 5 Parameters** | 15 fields (5.1.1–5.1.7) | 7 parameters (5.1–5.7) | `IMPLEMENTED_INCORRECTLY` (Standardized to official 5.1–5.7). Fixed. |
| **Chapter 6 Parameters** | 9 fields (6.1.1–6.1.4) | 16 parameters (6.1.1–6.1.6, 6.2.1–6.2.10) | `MISSING_FROM_IMPLEMENTATION` (Section 6.2 omitted). Fixed. |
| **Chapter 7 Parameters** | 9 fields (7.1.1–7.1.4) | 1 parameter (7.1) | `IMPLEMENTED_INCORRECTLY` (Consolidated to statutory undertaking 7.1). Fixed. |
| **Chapter 8 Parameters** | 12 fields (8.1.1–8.5.1) | 12 parameters (8.1.1–8.1.2, 8.2–8.9, 8.10.1–8.10.2) | `IMPLEMENTED_INCORRECTLY` (Standardized to official 8.1 to 8.10.2). Fixed. |
| **TOTAL CHAPTER PARAMETERS** | **73 fields** | **156 parameters** | **RECONCILED TO 156** |
| **Technical Plates** | 9 plates (Plates 1 to 8, 6A, 6B) | 23 plates (Plates I to XXIII) | `MISSING_FROM_IMPLEMENTATION` (Invented IDs 6A/6B removed, Roman I–XXIII restored). Fixed. |
| **Statutory Annexures** | 13 annexures | 8 annexures (Annexure-I to VII + VIII Other) | `IMPLEMENTED_INCORRECTLY` (Extraneous annexures pruned). Fixed. |
| **Statutory Certifications** | 4 certifications | 4 certifications (Cert-1 to Cert-4) | `MATCH` |
| **Statutory Escrow Rules** | Single 25% Just Transition rule | Rule A (25% community development) + Rule B (10% Just Transformation corpus) | `IMPLEMENTED_INCORRECTLY` (Conflated terminology separated). Fixed. |

## 2. Item-by-Item Status Classification

| Item Identifier | Official Description | Status | Discrepancy & Remediation |
| :--- | :--- | :--- | :--- |
| **1.1.1** | Name of Coal / Lignite mine or block | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.1.2** | Name of Coalfield/ Lignite field | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.1.3** | The base date of Mining Plan | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.1.4** | Linked End Use Plant | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.1.5** | Distance of End use plant from the pit head of the project in "km" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.1.6** | Mode of Coal Transport/Despatch | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.2.1** | Location of coal mine/block (District and State) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.2.2** | Communication: PWD roads, railway lines, Air | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.2.3** | Availability of power supply, water etc. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.2.4** | Prominent physiographic features, drainage pattern, natural water courses, rainfall data, highest flood level | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.2.5** | Important surface features within the project area and major diversion or shifting involved | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.3.1** | Name of the Allottee | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.3.2** | Details of allotment/ vesting order | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.3.3** | Name and address of the applicant (Regd. Office, Principal Place of Business) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.3.4** | Name of the Previous Allottee of the Block | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.3.5** | Date of Mining Opening permission granted by CCO | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.3.6** | Rated Capacity as per CMDPA | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.3.7** | Production Schedule as per opening permission (meeting provisions of CMDPA, if any) | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.3.8** | End Use of Coal/Lignite as per allotment order if any | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.3.9** | Cardinal Point co-ordinates (WGS84) of the Block boundary | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.4.1** | Whether any mining plan has been previously approved | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.4.2** | Title of the Mining Plan | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.3** | Base Date | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.4** | Submitted By | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.5** | Approval Reference, with Date | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.6** | Conditions, if any, and compliance | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.7** | Scheduled year of start of production | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.8** | Proposed year of achieving the targeted production | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.9** | Date of actual commencement of mining operations, if operations already started | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.10** | Likely date of mining operations, if operations not yet started and reasons for non-commencement of operations | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.11** | Planned production and actual levels achieved in last 3 financial years (Coal in Mt, OB in Mm3, SR in M3/t) and in current year till base date | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.12** | Statutory obligations vis-a-vis compliance status in a tabular form | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.4.13** | Reasons for difference between the planned and actual production levels | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.1** | Allocated Block Area in "Ha" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.2** | Allocated Block Area Projectised "Ha" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.3** | Proposed Mining Lease area "Ha" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.4** | Project Area "Ha" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.5** | Life of the Project "Yrs" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.6** | Minimum and Maximum Depth of working "m" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.7** | Geological Block "Ha" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.8** | Production Target "MTPA" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.9** | Seams Available "As per GR" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.10** | Seams not considered for Mining with Reasons | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.11** | Gross Geological Reserve "Mt" (as per GR) | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.12** | Net Geological Reserve "Mt" (as per GR) | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.13** | Blocked Reserve "Mt" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.14** | Minable Reserve "Mt" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.15** | Extractable Reserve "Mt" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.16** | % of Extraction/ recovery | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.17** | Production till date (till the base date of the proposed Mining Plan) Reserve "Mt" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.18** | Balance Extractable Reserve "Mt" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.19** | Average Grade | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.20** | OB in Mm3 | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.21** | SR Mm3/t | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.22** | Mining Technology | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.23** | Coal Beneficiation envisaged | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.24** | Handling of Rejects | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.25** | Land use pattern "Ha" | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.5.26** | Reasons for revision | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **1.6.1** | No. of Project Affected People (PAPs) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.2** | No. of Woking-aged persons | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.3** | No. of Skilled/Semi Skilled /Unskilled persons profession wise, gender wise, age wise and location wise | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.4** | No. of persons in Vulnerable Groups (Women, Children, Handicap etc.) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.5** | Repurposing of land proposed | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.6** | Assessment of possible GHG emissions | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.7** | Tentative measures to curtail GHG emissions | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **1.6.8** | Efforts to achieve net zero, wherever applicable | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.1** | Name of the Geological Report with month and year of preparation | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.2** | Name of GR Preparing Agency | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.3** | Particulars of adjacent Area/ blocks: North, South, East, West | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.4** | Location of the Block District / State | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.5** | Area of the Block "Ha" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.6** | Area of the geological block projectised "in Ha" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.7** | Balance area yet to be projectised "Ha" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.8** | Likely geological Resource in the area yet to be projectised "MTPA" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.9** | Cardinal Point Co-ordinates of the non-coal/lignite bearing area/ Coal/lignite bearing area within the existing mining lease outside the allotted Geological Coal/Lignite block | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **2.1.10** | Certificate of Qualified person/ Accredited Mining Plan preparing agency (MPPA) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.11** | KML file of the Proposed lease area, Project Area and geological block | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.12** | Whether the proposed project area is confined within the allotted block boundary/existing mining lease | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.1.13** | If the project area extends outside the allotted block boundary/existing mining lease, confirmation about non-occurrence of coal/lignite in the area under reference needs to be furnished | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **2.1.14** | Type of the Project (Operating under implementation) and year of Starting | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.1** | Regional geological set up of the area, geology, structure, stratigraphic sequence, characteristics of the litho-logical units (coal seams/partings/overburden) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.2** | Local geology, Structure, Stratigraphic sequence, Characteristics of the litho-logical units (coal seams /partings/overburden) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.3** | Geological Block Area "Ha" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.4** | Status of Exploration of the block | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.5** | Area covered by 'detailed' exploration within the block (sq. km) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.6** | Whether entire lease area has been covered by `detailed' exploration | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.7** | No. of boreholes drilled within the mining area of the block | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.8** | Whether any further exploration/study is required or suggested and time frame in which it is to be completed | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.9** | Year wise future programme of exploration | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **2.2.10** | Overall borehole density within the mining area (no./ sq. km) approx. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.11** | No of Seams available as per GR | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.12** | Seams not considered for Mining with Reasons | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.13** | Dip of the Seam | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.14** | Seam wise thickness, depth and reserve | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.15** | Methodology of resources estimation (also mention if any software package has been used) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.16** | Average GCV "KCal/kg" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.17** | Gross Geological Reserve of the block "Mt" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.18** | Net Geological Reserve of the block "Mt" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.19** | Minable Reserve of the block "Mt" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.20** | Blocked Reserve “Mt” | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.21** | Corresponding extractable Reserve of the block "Mt" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.22** | Percentage of Extraction | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.23** | Resource already depleted (Base date of Mining Plan) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **2.2.24** | Balance Resource (as on Base Date) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.1** | Existing method of mining if the mine is under operation | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **3.1.2** | Proposed method of mining with justification on suitability of method of mining | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.3** | Coal production capacity proposed "MTPA" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.4** | Justification for optimization of Coal production capacity | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.5** | The calendar year from which the production will start | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.6** | Year of Achieving rated production | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.7** | Tentative Coal Production Plan "Mt" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.8** | Rated Capacity “MTPA” | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.9** | Life of the mine: “Years” | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.10** | Whether the proposed external OB dump site is coal/ lignite bearing: If so, whether coal/lignite below the waste disposal area is extractable, If so, by OC or UG method | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **3.1.11** | Whether negative proving for coal/lignite in the proposed site for OB dump/ infrastructure has been done. | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **3.1.12** | Results of any investigation carried out for scientific mining, conservation of minerals and protection of environment; future proposals. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **3.1.13** | Type of Equipment/HEMM proposed | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **4.1.1** | Important safety aspects: Major Risks and uncertainties to the project viz. Proximity to river, adjacent working, geo-mining disturbances, slope stability and remedial measures suggested | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **4.1.2** | A Commitment from the Company Board that entire mining operation will be carried out as per the Statutory provision given under Mines Act 1952, Coal Mine Regulation 2017 | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.1** | Mine infrastructure required e.g., Equipment maintenance planning, Office buildings, Workshop, Power supply arrangement, Water supply etc. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.2** | Power supply and illumination. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.3** | Drainage and Pumping: Assessment of Volume of Water for Pumping, Pumping Capacity and Pump Selection | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.4** | Coal Handling Arrangement: Brief detail of the CHP/ Mode of Dispatch, Coal quality and Coal staking and handling arrangement | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.5** | Coal washing and the proposed handling/ disposal of rejects. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.6** | Water Consumption and Wastewater generation | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **5.7** | Other infrastructures for air pollution control (fog cannons, fixed water spraying systems, cold fog, Vertical Greenery System (VGS), wind barriers, or other relevant technologies) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.1.1** | Total Land requirement for the mine in "Ha" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.1.2** | During mining Land use details: | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.1.3** | Surface features over the block area | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.1.4** | No. of villages/Houses to be shifted | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.1.5** | Population to be affected by the project | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.1.6** | Proposed Rehabilitation programme | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.1** | Status of Lease | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.2** | Existing Lease Area "Ha" | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.3** | Period for which Mining Lease has been granted/is to be renewed/ is to be applied for. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.4** | Date of expiry of earlier Mining Lease, if any | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **6.2.5** | Whether the lease boundary/ required boundary is same as mentioned in the allotment order | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.6** | Lease Area (applied/ required) as per the Mining Plan under consideration (Ha) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.7** | Whether the applied lease area falls within the allotted block | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.8** | Area (Ha) of lease which falls outside the delineated Block Boundary/Existing Mining Lease | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **6.2.9** | Details of outside area: Whether forms part of any other coal block, coal content, purpose | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **6.2.10** | Whether some part(s) of the allotted block has not been applied for mining lease: Total area, resources & reasons | `CONDITIONAL` | Authoritative Appendix-I parameter incorporated. |
| **7.1** | The project proponent shall submit an undertaking that the mine shall be operated as per the Environment Clearance (EC) and Forestry Clearance (FC) for the project. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.1.1** | Tentative Land Degradation and Technical Reclamation (Commutative Area "Ha") | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.1.2** | Tentative Biological Reclamation (Cumulative in "Ha") | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.2** | Post Closure Water Quality management: | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.3** | Post Closure Air Quality management | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.4** | Waste Management (Figures in MM3) (Tentative) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.5** | Top Soil Management — (Including Action plan for Top Soil management) (Tentative) | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.6** | Management of Coal Rejects. | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.7** | Restoration of Land used for Infrastructure | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.8** | Disposal of Mining Machinery | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.9** | Safety and Security | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.10.1** | Mine Closure Cost: Cost of Activities to be taken up for closure of the mines | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **8.10.2** | Financial Assurance: Amount to be deposited in Escrow account as a security against the mine activities to be carried out for the closure of the mine | `MATCH` | Authoritative Appendix-I parameter incorporated. |
| **Plate I** | Location plan... | `MATCH` | Official Roman-numeral plate mapped with scale 1:50,000 / Topo Sheet. |
| **Plate II** | Plan certified by Qualified person (QP) / Accredited Mining Plan preparing agenc... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate III** | KML file of the Proposed lease area, Project Area and geological block (printed ... | `MATCH` | Official Roman-numeral plate mapped with scale Satellite Overlay. |
| **Plate IV** | Cadastral plan showing approved block boundary vis-à-vis proposed/existing minin... | `MATCH` | Official Roman-numeral plate mapped with scale Cadastral Scale (1:4,000). |
| **Plate V** | Geological plan showing all the boreholes drilled and proposed to be drilled sho... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate VI** | Graphic Litholog... | `MATCH` | Official Roman-numeral plate mapped with scale Vertical Graphic Scale. |
| **Plate VII** | Surface Plan showing drainage system, Contour, at minimum 3m interval, location ... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000 (3m contour). |
| **Plate VIII** | Conceptual plan showing infrastructure facilities including colony, boundary of ... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate IX** | Tentative land use plan showing land type (Govt., forest and tenancy land) with ... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate X** | Floor contour plan and seam folio plan, ISO-grade plan... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XI** | X-section showing coal/Lignite seams... | `MATCH` | Official Roman-numeral plate mapped with scale Longitudinal & Transverse. |
| **Plate XII** | Plan showing existing and proposed surface layout... | `MATCH` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XIII** | Plan showing total coal thickness and overburden thickness and stripping ratio... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XIV** | Final stage quarry plan showing haul road alignment... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XV** | Plan showing mode and location of entries and surface layouts... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XVI** | Layout of the panel for each system (like Longwall, Continuous Miner, Bord and P... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:1,000 / 1:2,000. |
| **Plate XVII** | Layout of pillar extraction... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:1,000 / 1:2,000. |
| **Plate XVIII** | Support system... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale Detailed Engineering Scale. |
| **Plate XIX** | Haulage and transport system... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XX** | Post mining land use plan... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XXI** | Progressive mine closure plan/ stage plan indicating stages at 1st, 3rd, 5th, 10... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000 stage series. |
| **Plate XXII** | Year 30 Stage Plan... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Plate XXIII** | Reclamation plan for which detailed planning has been done... | `CONDITIONAL` | Official Roman-numeral plate mapped with scale 1:2,000 / 1:5,000. |
| **Annexure-I** | Copy of allotment order / Vesting order... | `MATCH` | Prescribed Section C annexure verified. |
| **Annexure-II** | Certificate of Qualified person (QP) / Accredited Mining Plan preparing agency (... | `MATCH` | Prescribed Section C annexure verified. |
| **Annexure-III** | Approval of the Company Board (giving undertaking for data correctness, QP eligi... | `MATCH` | Prescribed Section C annexure verified. |
| **Annexure-IV** | Copy of earlier approval of mining plan... | `CONDITIONAL` | Prescribed Section C annexure verified. |
| **Annexure-V** | Plan / chart showing schedule of Implementation of Mine closure activities (prog... | `MATCH` | Prescribed Section C annexure verified. |
| **Annexure-VI** | Non-refundable Application Fee Proof of the payment... | `MATCH` | Prescribed Section C annexure verified. |
| **Annexure-VII** | Expert-Review Report Carried out by Accredited Mining Plan Preparing Agency (MPP... | `MATCH` | Prescribed Section C annexure verified. |
| **Annexure-VIII** | Other document (if any)... | `CONDITIONAL` | Prescribed Section C annexure verified. |
| **Cert-1** | Qualified Person Block Boundary Confinement Certificate | `MATCH` | Statutory execution instrument mapped. |
| **Cert-2** | Board Undertaking on Data Correctness & Statutory Adherence | `MATCH` | Statutory execution instrument mapped. |
| **Cert-3** | Progressive & Final Mine Closure Execution Undertaking | `MATCH` | Statutory execution instrument mapped. |
| **Cert-4** | Environmental Clearance (EC) & Forestry Clearance (FC) Compliance Undertaking | `MATCH` | Statutory execution instrument mapped. |
