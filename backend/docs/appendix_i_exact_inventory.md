# Exhaustive Statutory Inventory: Ministry of Coal / CCO 2025 Mining Plan Guidelines

**Authoritative Source**:
Government of India, Ministry of Coal, Coal Controller Organisation
Office Memorandum F.No. CPAM-34011/28/2019-CPAM [E-343762] dated 31 January 2025
**Appendix-I: "DETAILS TO BE FURNISHED IN THE MINING PLANS FOR COAL/LIGNITE BLOCKS"**
Official Source URL: https://coalcontroller.gov.in/files/guidelines-acts-documents/mp-guidelines-31012025_0.pdf
Local Governing Reference: `backend/docs/mp-guidelines-31012025_0.pdf` (Pages 23 to 55 of 83; PDF Pages 25 to 57)

---

## 1. Statutory Summary & Mathematical Reconciliation

The counts below are derived as direct mathematical sums from the extracted inventory:
- **TOTAL CHAPTER PARAMETERS**: **156** parameters across Chapters 1 to 8
  * **Chapter 1 (Project Information)**: 67 parameters (1.1: 6, 1.2: 5, 1.3: 9, 1.4: 13, 1.5: 26, 1.6: 8)
  * **Chapter 2 (Exploration, Geology & Reserves)**: 38 parameters (2.1: 14, 2.2: 24)
  * **Chapter 3 (Mining)**: 13 parameters (3.1.1–3.1.13)
  * **Chapter 4 (Safety and Health Management)**: 2 parameters (4.1.1–4.1.2)
  * **Chapter 5 (Infrastructure Facilities)**: 7 parameters (5.1–5.7)
  * **Chapter 6 (Land Requirement)**: 16 parameters (6.1: 6, 6.2: 10)
  * **Chapter 7 (Environmental Management)**: 1 parameter (7.1)
  * **Chapter 8 (Progressive & Final Mine Closure Plan)**: 12 parameters (8.1.1–8.1.2, 8.2–8.9, 8.10.1–8.10.2)
  * **Mathematical Proof**: 67 + 38 + 13 + 2 + 7 + 16 + 1 + 12 = **156**
- **TOTAL TECHNICAL PLATES**: **23** drawings (Plates I to XXIII)
- **TOTAL STATUTORY ANNEXURES**: **8** annexures (Annexure-I to Annexure-VIII Other)
- **TOTAL CERTIFICATIONS & UNDERTAKINGS**: **4** statutory instruments (Cert-1 to Cert-4)

---

## 2. Complete Numbered Parameter Inventory (Chapters 1 to 8)

| Official ID | Exact Official Label | Parent Section | Data Type | Unit | Required Status | Applicability | Source Page (Guide/PDF) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1.1.1** | Name of Coal / Lignite mine or block | 1.1 INTRODUCTION | string | - | MANDATORY | Universal | 27 / 29 |
| **1.1.2** | Name of Coalfield/ Lignite field | 1.1 INTRODUCTION | string | - | MANDATORY | Universal | 27 / 29 |
| **1.1.3** | The base date of Mining Plan | 1.1 INTRODUCTION | date | YYYY-MM | MANDATORY | Universal | 27 / 29 |
| **1.1.4** | Linked End Use Plant | 1.1 INTRODUCTION | string | - | MANDATORY | Universal | 27 / 29 |
| **1.1.5** | Distance of End use plant from the pit head of the project in "km" | 1.1 INTRODUCTION | float | km | MANDATORY | Universal | 27 / 29 |
| **1.1.6** | Mode of Coal Transport/Despatch | 1.1 INTRODUCTION | string | - | MANDATORY | Universal | 27 / 29 |
| **1.2.1** | Location of coal mine/block (District and State) | 1.2 LOCATION, TOPOGRAPHY & COMM. | string | - | MANDATORY | Universal | 27 / 29 |
| **1.2.2** | Communication: PWD roads, railway lines, Air | 1.2 LOCATION, TOPOGRAPHY & COMM. | string | - | MANDATORY | Universal | 27 / 29 |
| **1.2.3** | Availability of power supply, water etc. | 1.2 LOCATION, TOPOGRAPHY & COMM. | string | - | MANDATORY | Universal | 27 / 29 |
| **1.2.4** | Prominent physiographic features, drainage pattern, natural water courses, rainfall data, highest flood level | 1.2 LOCATION, TOPOGRAPHY & COMM. | text | - | MANDATORY | Universal | 27 / 29 |
| **1.2.5** | Important surface features within the project area and major diversion or shifting involved | 1.2 LOCATION, TOPOGRAPHY & COMM. | text | - | MANDATORY | Universal | 27 / 29 |
| **1.3.1** | Name of the Allottee | 1.3 ALLOTMENT AGREEMENT | string | - | MANDATORY | Universal | 27 / 29 |
| **1.3.2** | Details of allotment/ vesting order | 1.3 ALLOTMENT AGREEMENT | string | - | MANDATORY | Universal | 27 / 29 |
| **1.3.3** | Name and address of the applicant (Regd. Office, Principal Place of Business) | 1.3 ALLOTMENT AGREEMENT | text | - | MANDATORY | Universal | 27 / 29 |
| **1.3.4** | Name of the Previous Allottee of the Block | 1.3 ALLOTMENT AGREEMENT | string | - | CONDITIONAL | Prior Allottee Blocks | 27 / 29 |
| **1.3.5** | Date of Mining Opening permission granted by CCO | 1.3 ALLOTMENT AGREEMENT | date | YYYY-MM-DD | CONDITIONAL | Operating Mines | 27-28 / 29-30 |
| **1.3.6** | Rated Capacity as per CMDPA | 1.3 ALLOTMENT AGREEMENT | float | MTPA | MANDATORY | Universal | 28 / 30 |
| **1.3.7** | Production Schedule as per opening permission (meeting provisions of CMDPA, if any) | 1.3 ALLOTMENT AGREEMENT | text | - | CONDITIONAL | Operating Mines | 28 / 30 |
| **1.3.8** | End Use of Coal/Lignite as per allotment order if any | 1.3 ALLOTMENT AGREEMENT | string | - | MANDATORY | Universal | 28 / 30 |
| **1.3.9** | Cardinal Point co-ordinates (WGS84) of the Block boundary | 1.3 ALLOTMENT AGREEMENT | table | Latitude/Longitude | MANDATORY | Universal | 28 / 30 |
| **1.4.1** | Whether any mining plan has been previously approved | 1.4 PREVIOUS APPROVAL | boolean | - | MANDATORY | Universal | 28 / 30 |
| **1.4.2** | Title of the Mining Plan | 1.4 PREVIOUS APPROVAL | string | - | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.3** | Base Date | 1.4 PREVIOUS APPROVAL | date | YYYY-MM | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.4** | Submitted By | 1.4 PREVIOUS APPROVAL | string | - | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.5** | Approval Reference, with Date | 1.4 PREVIOUS APPROVAL | string | - | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.6** | Conditions, if any, and compliance | 1.4 PREVIOUS APPROVAL | table | Conditions/Compliance | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.7** | Scheduled year of start of production | 1.4 PREVIOUS APPROVAL | integer | YYYY | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.8** | Proposed year of achieving the targeted production | 1.4 PREVIOUS APPROVAL | integer | YYYY | CONDITIONAL | If Previously Approved | 28 / 30 |
| **1.4.9** | Date of actual commencement of mining operations, if operations already started | 1.4 PREVIOUS APPROVAL | date | YYYY-MM-DD | CONDITIONAL | Operating Mines | 28 / 30 |
| **1.4.10** | Likely date of mining operations, if operations not yet started and reasons for non-commencement of operations | 1.4 PREVIOUS APPROVAL | text | - | CONDITIONAL | Non-Operating Mines | 28 / 30 |
| **1.4.11** | Planned production and actual levels achieved in last 3 financial years (Coal in Mt, OB in Mm3, SR in M3/t) and in current year till base date | 1.4 PREVIOUS APPROVAL | table | MT / Mm3 / SR | CONDITIONAL | Operating Mines | 28-29 / 30-31 |
| **1.4.12** | Statutory obligations vis-a-vis compliance status in a tabular form | 1.4 PREVIOUS APPROVAL | table | Obligations/Status | CONDITIONAL | Operating Mines | 29 / 31 |
| **1.4.13** | Reasons for difference between the planned and actual production levels | 1.4 PREVIOUS APPROVAL | text | - | CONDITIONAL | Operating Mines | 29 / 31 |
| **1.5.1** | Allocated Block Area in "Ha" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Ha | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.2** | Allocated Block Area Projectised "Ha" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Ha | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.3** | Proposed Mining Lease area "Ha" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Ha | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.4** | Project Area "Ha" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Ha | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.5** | Life of the Project "Yrs" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Years | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.6** | Minimum and Maximum Depth of working "m" | 1.5 PARAMETERS APPROVED VS PROPOSED | string | m | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.7** | Geological Block "Ha" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Ha | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.8** | Production Target "MTPA" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MTPA | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.9** | Seams Available "As per GR" | 1.5 PARAMETERS APPROVED VS PROPOSED | text | - | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.10** | Seams not considered for Mining with Reasons | 1.5 PARAMETERS APPROVED VS PROPOSED | text | - | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.11** | Gross Geological Reserve "Mt" (as per GR) | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 29 / 31 |
| **1.5.12** | Net Geological Reserve "Mt" (as per GR) | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.13** | Blocked Reserve "Mt" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.14** | Minable Reserve "Mt" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.15** | Extractable Reserve "Mt" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.16** | % of Extraction/ recovery | 1.5 PARAMETERS APPROVED VS PROPOSED | float | % | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.17** | Production till date (till the base date of the proposed Mining Plan) Reserve "Mt" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.18** | Balance Extractable Reserve "Mt" | 1.5 PARAMETERS APPROVED VS PROPOSED | float | MT | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.19** | Average Grade | 1.5 PARAMETERS APPROVED VS PROPOSED | string | - | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.20** | OB in Mm3 | 1.5 PARAMETERS APPROVED VS PROPOSED | float | Mm3 | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.21** | SR Mm3/t | 1.5 PARAMETERS APPROVED VS PROPOSED | float | m3/t | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.22** | Mining Technology | 1.5 PARAMETERS APPROVED VS PROPOSED | string | - | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.23** | Coal Beneficiation envisaged | 1.5 PARAMETERS APPROVED VS PROPOSED | text | - | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.24** | Handling of Rejects | 1.5 PARAMETERS APPROVED VS PROPOSED | text | - | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.25** | Land use pattern "Ha" | 1.5 PARAMETERS APPROVED VS PROPOSED | table | Ha | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.5.26** | Reasons for revision | 1.5 PARAMETERS APPROVED VS PROPOSED | text | - | CONDITIONAL | Revised Plans | 30 / 32 |
| **1.6.1** | No. of Project Affected People (PAPs) | 1.6 SUSTAINABILITY | integer | persons | MANDATORY | Universal | 30 / 32 |
| **1.6.2** | No. of Woking-aged persons | 1.6 SUSTAINABILITY | integer | persons | MANDATORY | Universal | 30 / 32 |
| **1.6.3** | No. of Skilled/Semi Skilled /Unskilled persons profession wise, gender wise, age wise and location wise | 1.6 SUSTAINABILITY | table | persons | MANDATORY | Universal | 30 / 32 |
| **1.6.4** | No. of persons in Vulnerable Groups (Women, Children, Handicap etc.) | 1.6 SUSTAINABILITY | integer | persons | MANDATORY | Universal | 31 / 33 |
| **1.6.5** | Repurposing of land proposed | 1.6 SUSTAINABILITY | text | - | MANDATORY | Universal | 31 / 33 |
| **1.6.6** | Assessment of possible GHG emissions | 1.6 SUSTAINABILITY | text | - | MANDATORY | Universal | 31 / 33 |
| **1.6.7** | Tentative measures to curtail GHG emissions | 1.6 SUSTAINABILITY | text | - | MANDATORY | Universal | 31 / 33 |
| **1.6.8** | Efforts to achieve net zero, wherever applicable | 1.6 SUSTAINABILITY | text | - | MANDATORY | Universal | 31 / 33 |
| **2.1.1** | Name of the Geological Report with month and year of preparation | 2.1 DETAILS OF THE BLOCK | string | - | MANDATORY | Universal | 31 / 33 |
| **2.1.2** | Name of GR Preparing Agency | 2.1 DETAILS OF THE BLOCK | string | - | MANDATORY | Universal | 31 / 33 |
| **2.1.3** | Particulars of adjacent Area/ blocks: North, South, East, West | 2.1 DETAILS OF THE BLOCK | text | - | MANDATORY | Universal | 31 / 33 |
| **2.1.4** | Location of the Block District / State | 2.1 DETAILS OF THE BLOCK | string | - | MANDATORY | Universal | 31 / 33 |
| **2.1.5** | Area of the Block "Ha" | 2.1 DETAILS OF THE BLOCK | float | Ha | MANDATORY | Universal | 31 / 33 |
| **2.1.6** | Area of the geological block projectised "in Ha" | 2.1 DETAILS OF THE BLOCK | float | Ha | MANDATORY | Universal | 31 / 33 |
| **2.1.7** | Balance area yet to be projectised "Ha" | 2.1 DETAILS OF THE BLOCK | float | Ha | MANDATORY | Universal | 31 / 33 |
| **2.1.8** | Likely geological Resource in the area yet to be projectised "MTPA" | 2.1 DETAILS OF THE BLOCK | float | MT | MANDATORY | Universal | 31 / 33 |
| **2.1.9** | Cardinal Point Co-ordinates of the non-coal/lignite bearing area/ Coal/lignite bearing area within the existing mining lease outside the allotted Geological Coal/Lignite block | 2.1 DETAILS OF THE BLOCK | table | Latitude/Longitude | CONDITIONAL | If Area Outside Block | 31-32 / 33-34 |
| **2.1.10** | Certificate of Qualified person/ Accredited Mining Plan preparing agency (MPPA) | 2.1 DETAILS OF THE BLOCK | text | - | MANDATORY | Universal | 32 / 34 |
| **2.1.11** | KML file of the Proposed lease area, Project Area and geological block | 2.1 DETAILS OF THE BLOCK | file | KML | MANDATORY | Universal | 32 / 34 |
| **2.1.12** | Whether the proposed project area is confined within the allotted block boundary/existing mining lease | 2.1 DETAILS OF THE BLOCK | boolean | - | MANDATORY | Universal | 32 / 34 |
| **2.1.13** | If the project area extends outside the allotted block boundary/existing mining lease, confirmation about non-occurrence of coal/lignite in the area under reference needs to be furnished | 2.1 DETAILS OF THE BLOCK | text | - | CONDITIONAL | If Extends Outside | 32-33 / 34-35 |
| **2.1.14** | Type of the Project (Operating under implementation) and year of Starting | 2.1 DETAILS OF THE BLOCK | string | - | MANDATORY | Universal | 33 / 35 |
| **2.2.1** | Regional geological set up of the area, geology, structure, stratigraphic sequence, characteristics of the litho-logical units (coal seams/partings/overburden) | 2.2 EXPLORATION & RESERVES | text | - | MANDATORY | Universal | 33 / 35 |
| **2.2.2** | Local geology, Structure, Stratigraphic sequence, Characteristics of the litho-logical units (coal seams /partings/overburden) | 2.2 EXPLORATION & RESERVES | text | - | MANDATORY | Universal | 33 / 35 |
| **2.2.3** | Geological Block Area "Ha" | 2.2 EXPLORATION & RESERVES | float | Ha | MANDATORY | Universal | 33 / 35 |
| **2.2.4** | Status of Exploration of the block | 2.2 EXPLORATION & RESERVES | table | Ha / % | MANDATORY | Universal | 33 / 35 |
| **2.2.5** | Area covered by 'detailed' exploration within the block (sq. km) | 2.2 EXPLORATION & RESERVES | float | sq.km | MANDATORY | Universal | 33 / 35 |
| **2.2.6** | Whether entire lease area has been covered by `detailed' exploration | 2.2 EXPLORATION & RESERVES | boolean | - | MANDATORY | Universal | 33 / 35 |
| **2.2.7** | No. of boreholes drilled within the mining area of the block | 2.2 EXPLORATION & RESERVES | integer | count | MANDATORY | Universal | 33 / 35 |
| **2.2.8** | Whether any further exploration/study is required or suggested and time frame in which it is to be completed | 2.2 EXPLORATION & RESERVES | boolean | - | MANDATORY | Universal | 33 / 35 |
| **2.2.9** | Year wise future programme of exploration | 2.2 EXPLORATION & RESERVES | table | m / Rs | CONDITIONAL | If Future Exploration Req | 33 / 35 |
| **2.2.10** | Overall borehole density within the mining area (no./ sq. km) approx. | 2.2 EXPLORATION & RESERVES | float | no/sq.km | MANDATORY | Universal | 33 / 35 |
| **2.2.11** | No of Seams available as per GR | 2.2 EXPLORATION & RESERVES | integer | count | MANDATORY | Universal | 33 / 35 |
| **2.2.12** | Seams not considered for Mining with Reasons | 2.2 EXPLORATION & RESERVES | text | - | MANDATORY | Universal | 33 / 35 |
| **2.2.13** | Dip of the Seam | 2.2 EXPLORATION & RESERVES | string | deg | MANDATORY | Universal | 33 / 35 |
| **2.2.14** | Seam wise thickness, depth and reserve | 2.2 EXPLORATION & RESERVES | table | m / MT | MANDATORY | Universal | 33-34 / 35-36 |
| **2.2.15** | Methodology of resources estimation (also mention if any software package has been used) | 2.2 EXPLORATION & RESERVES | text | - | MANDATORY | Universal | 34 / 36 |
| **2.2.16** | Average GCV "KCal/kg" | 2.2 EXPLORATION & RESERVES | float | KCal/kg | MANDATORY | Universal | 34 / 36 |
| **2.2.17** | Gross Geological Reserve of the block "Mt" | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **2.2.18** | Net Geological Reserve of the block "Mt" | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **2.2.19** | Minable Reserve of the block "Mt" | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **2.2.20** | Blocked Reserve “Mt” | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **2.2.21** | Corresponding extractable Reserve of the block "Mt" | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **2.2.22** | Percentage of Extraction | 2.2 EXPLORATION & RESERVES | float | % | MANDATORY | Universal | 34 / 36 |
| **2.2.23** | Resource already depleted (Base date of Mining Plan) | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **2.2.24** | Balance Resource (as on Base Date) | 2.2 EXPLORATION & RESERVES | float | MT | MANDATORY | Universal | 34 / 36 |
| **3.1.1** | Existing method of mining if the mine is under operation | 3.1 MINING METHOD | text | - | CONDITIONAL | Operating Mines | 34 / 36 |
| **3.1.2** | Proposed method of mining with justification on suitability of method of mining | 3.1 MINING METHOD | text | - | MANDATORY | Universal | 35-36 / 37-38 |
| **3.1.3** | Coal production capacity proposed "MTPA" | 3.1 MINING METHOD | table | MTPA | MANDATORY | Universal | 36 / 38 |
| **3.1.4** | Justification for optimization of Coal production capacity | 3.1 MINING METHOD | text | - | MANDATORY | Universal | 36 / 38 |
| **3.1.5** | The calendar year from which the production will start | 3.1 MINING METHOD | integer | YYYY | MANDATORY | Universal | 36 / 38 |
| **3.1.6** | Year of Achieving rated production | 3.1 MINING METHOD | integer | YYYY | MANDATORY | Universal | 36 / 38 |
| **3.1.7** | Tentative Coal Production Plan "Mt" | 3.1 MINING METHOD | table | MT / MM3 / SR | MANDATORY | Universal | 36-37 / 38-39 |
| **3.1.8** | Rated Capacity “MTPA” | 3.1 MINING METHOD | float | MTPA | MANDATORY | Universal | 37 / 39 |
| **3.1.9** | Life of the mine: “Years” | 3.1 MINING METHOD | float | Years | MANDATORY | Universal | 37 / 39 |
| **3.1.10** | Whether the proposed external OB dump site is coal/ lignite bearing: If so, whether coal/lignite below the waste disposal area is extractable, If so, by OC or UG method | 3.1 MINING METHOD | text | - | CONDITIONAL | Opencast Mines | 37 / 39 |
| **3.1.11** | Whether negative proving for coal/lignite in the proposed site for OB dump/ infrastructure has been done. | 3.1 MINING METHOD | boolean | - | CONDITIONAL | Opencast Mines | 37 / 39 |
| **3.1.12** | Results of any investigation carried out for scientific mining, conservation of minerals and protection of environment; future proposals. | 3.1 MINING METHOD | text | - | MANDATORY | Universal | 37 / 39 |
| **3.1.13** | Type of Equipment/HEMM proposed | 3.1 MINING METHOD | table | Fleet/Capacity | MANDATORY | Universal | 37 / 39 |
| **4.1.1** | Important safety aspects: Major Risks and uncertainties to the project viz. Proximity to river, adjacent working, geo-mining disturbances, slope stability and remedial measures suggested | 4.1 SAFETY & HEALTH AUDIT | text | - | MANDATORY | Universal | 38 / 40 |
| **4.1.2** | A Commitment from the Company Board that entire mining operation will be carried out as per the Statutory provision given under Mines Act 1952, Coal Mine Regulation 2017 | 4.1 SAFETY & HEALTH AUDIT | text | - | MANDATORY | Universal | 38 / 40 |
| **5.1** | Mine infrastructure required e.g., Equipment maintenance planning, Office buildings, Workshop, Power supply arrangement, Water supply etc. | Chapter 5 | table | Ha | MANDATORY | Universal | 39 / 41 |
| **5.2** | Power supply and illumination. | Chapter 5 | text | - | MANDATORY | Universal | 39 / 41 |
| **5.3** | Drainage and Pumping: Assessment of Volume of Water for Pumping, Pumping Capacity and Pump Selection | Chapter 5 | text | - | MANDATORY | Universal | 39 / 41 |
| **5.4** | Coal Handling Arrangement: Brief detail of the CHP/ Mode of Dispatch, Coal quality and Coal staking and handling arrangement | Chapter 5 | text | - | MANDATORY | Universal | 39 / 41 |
| **5.5** | Coal washing and the proposed handling/ disposal of rejects. | Chapter 5 | table | MT / % | MANDATORY | Universal | 39 / 41 |
| **5.6** | Water Consumption and Wastewater generation | Chapter 5 | text | KLD | MANDATORY | Universal | 39-40 / 41-42 |
| **5.7** | Other infrastructures for air pollution control (fog cannons, fixed water spraying systems, cold fog, Vertical Greenery System (VGS), wind barriers, or other relevant technologies) | Chapter 5 | text | - | MANDATORY | Universal | 40 / 42 |
| **6.1.1** | Total Land requirement for the mine in "Ha" | 6.1 LAND REQUIREMENT | table | Ha | MANDATORY | Universal | 40 / 42 |
| **6.1.2** | During mining Land use details: | 6.1 LAND REQUIREMENT | table | Ha | MANDATORY | Universal | 40-42 / 42-44 |
| **6.1.3** | Surface features over the block area | 6.1 LAND REQUIREMENT | text | - | MANDATORY | Universal | 42 / 44 |
| **6.1.4** | No. of villages/Houses to be shifted | 6.1 LAND REQUIREMENT | integer | count | MANDATORY | Universal | 42 / 44 |
| **6.1.5** | Population to be affected by the project | 6.1 LAND REQUIREMENT | integer | persons | MANDATORY | Universal | 42 / 44 |
| **6.1.6** | Proposed Rehabilitation programme | 6.1 LAND REQUIREMENT | text | - | MANDATORY | Universal | 42 / 44 |
| **6.2.1** | Status of Lease | 6.2 DETAILS OF LEASE | string | - | MANDATORY | Universal | 42 / 44 |
| **6.2.2** | Existing Lease Area "Ha" | 6.2 DETAILS OF LEASE | float | Ha | MANDATORY | Universal | 42 / 44 |
| **6.2.3** | Period for which Mining Lease has been granted/is to be renewed/ is to be applied for. | 6.2 DETAILS OF LEASE | string | Years | MANDATORY | Universal | 42 / 44 |
| **6.2.4** | Date of expiry of earlier Mining Lease, if any | 6.2 DETAILS OF LEASE | date | YYYY-MM-DD | CONDITIONAL | Renewals / Expansions | 42 / 44 |
| **6.2.5** | Whether the lease boundary/ required boundary is same as mentioned in the allotment order | 6.2 DETAILS OF LEASE | boolean | - | MANDATORY | Universal | 42 / 44 |
| **6.2.6** | Lease Area (applied/ required) as per the Mining Plan under consideration (Ha) | 6.2 DETAILS OF LEASE | float | Ha | MANDATORY | Universal | 42 / 44 |
| **6.2.7** | Whether the applied lease area falls within the allotted block | 6.2 DETAILS OF LEASE | boolean | - | MANDATORY | Universal | 42 / 44 |
| **6.2.8** | Area (Ha) of lease which falls outside the delineated Block Boundary/Existing Mining Lease | 6.2 DETAILS OF LEASE | float | Ha | MANDATORY | Universal | 42 / 44 |
| **6.2.9** | Details of outside area: Whether forms part of any other coal block, coal content, purpose | 6.2 DETAILS OF LEASE | text | - | CONDITIONAL | If Lease Outside Block | 42-43 / 44-45 |
| **6.2.10** | Whether some part(s) of the allotted block has not been applied for mining lease: Total area, resources & reasons | 6.2 DETAILS OF LEASE | text | - | CONDITIONAL | If Part Left Out | 43 / 45 |
| **7.1** | The project proponent shall submit an undertaking that the mine shall be operated as per the Environment Clearance (EC) and Forestry Clearance (FC) for the project. | Chapter 7 | text | - | MANDATORY | Universal | 43-44 / 45-46 |
| **8.1.1** | Tentative Land Degradation and Technical Reclamation (Commutative Area "Ha") | 8.1 LAND DEGRADATION & RESTORATION | table | Ha | MANDATORY | Universal | 44 / 46 |
| **8.1.2** | Tentative Biological Reclamation (Cumulative in "Ha") | 8.1 LAND DEGRADATION & RESTORATION | table | Ha | MANDATORY | Universal | 44-45 / 46-47 |
| **8.2** | Post Closure Water Quality management: | Chapter 8 | text | - | MANDATORY | Universal | 45 / 47 |
| **8.3** | Post Closure Air Quality management | Chapter 8 | text | - | MANDATORY | Universal | 45 / 47 |
| **8.4** | Waste Management (Figures in MM3) (Tentative) | Chapter 8 | table | Mm3 | MANDATORY | Universal | 45-46 / 47-48 |
| **8.5** | Top Soil Management — (Including Action plan for Top Soil management) (Tentative) | Chapter 8 | table | Mm3 | MANDATORY | Universal | 46 / 48 |
| **8.6** | Management of Coal Rejects. | Chapter 8 | text | - | MANDATORY | Universal | 46 / 48 |
| **8.7** | Restoration of Land used for Infrastructure | Chapter 8 | text | - | MANDATORY | Universal | 46 / 48 |
| **8.8** | Disposal of Mining Machinery | Chapter 8 | text | - | MANDATORY | Universal | 46 / 48 |
| **8.9** | Safety and Security | Chapter 8 | text | - | MANDATORY | Universal | 46 / 48 |
| **8.10.1** | Mine Closure Cost: Cost of Activities to be taken up for closure of the mines | 8.10 CLOSURE COST & ESCROW | table | Rs. Cr | MANDATORY | Universal | 46-49 / 48-51 |
| **8.10.2** | Financial Assurance: Amount to be deposited in Escrow account as a security against the mine activities to be carried out for the closure of the mine | 8.10 CLOSURE COST & ESCROW | table | Rs. Cr | MANDATORY | Universal | 49-51 / 51-53 |

---

## 3. Official Plans / Plates / Technical Drawings Inventory (Plates I to XXIII)

| Plate Number | Official Title & Technical Description | Sequence | Applicability | Scale Requirement | Source Page |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Plate I** | Location plan | 1 | UNIVERSAL | 1:50,000 / Topo Sheet | 54 / 56 |
| **Plate II** | Plan certified by Qualified person (QP) / Accredited Mining Plan preparing agency (MPPA) if the project area is confined within the vested/allotted block boundary and where extending beyond supported with State Govt certified plan with cardinal coordinates (Plan in support of Annexure - II) | 2 | UNIVERSAL | 1:2,000 / 1:5,000 | 54 / 56 |
| **Plate III** | KML file of the Proposed lease area, Project Area and geological block (printed copy superimposed on recent satellite image < 1 yr + soft copy) | 3 | UNIVERSAL | Satellite Overlay | 54 / 56 |
| **Plate IV** | Cadastral plan showing approved block boundary vis-à-vis proposed/existing mining lease and Mine boundary superimposed over it in distinct colour, showing land use and infrastructure etc. | 4 | UNIVERSAL | Cadastral Scale (1:4,000) | 54 / 56 |
| **Plate V** | Geological plan showing all the boreholes drilled and proposed to be drilled showing allotted block boundary and required lease area | 5 | UNIVERSAL | 1:2,000 / 1:5,000 | 54 / 56 |
| **Plate VI** | Graphic Litholog | 6 | UNIVERSAL | Vertical Graphic Scale | 54 / 56 |
| **Plate VII** | Surface Plan showing drainage system, Contour, at minimum 3m interval, location of BH | 7 | UNIVERSAL | 1:2,000 / 1:5,000 (3m contour) | 54 / 56 |
| **Plate VIII** | Conceptual plan showing infrastructure facilities including colony, boundary of mining area, mine entries, roads including road diversion alignment etc | 8 | UNIVERSAL | 1:2,000 / 1:5,000 | 54 / 56 |
| **Plate IX** | Tentative land use plan showing land type (Govt., forest and tenancy land) with its data source | 9 | UNIVERSAL | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate X** | Floor contour plan and seam folio plan, ISO-grade plan | 10 | UNIVERSAL | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XI** | X-section showing coal/Lignite seams | 11 | UNIVERSAL | Longitudinal & Transverse | 55 / 57 |
| **Plate XII** | Plan showing existing and proposed surface layout | 12 | UNIVERSAL | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XIII** | Plan showing total coal thickness and overburden thickness and stripping ratio | 13 | OC_ONLY | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XIV** | Final stage quarry plan showing haul road alignment | 14 | OC_ONLY | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XV** | Plan showing mode and location of entries and surface layouts | 15 | UG_ONLY | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XVI** | Layout of the panel for each system (like Longwall, Continuous Miner, Bord and Pillar, road header etc.) | 16 | UG_ONLY | 1:1,000 / 1:2,000 | 55 / 57 |
| **Plate XVII** | Layout of pillar extraction | 17 | UG_ONLY | 1:1,000 / 1:2,000 | 55 / 57 |
| **Plate XVIII** | Support system | 18 | UG_ONLY | Detailed Engineering Scale | 55 / 57 |
| **Plate XIX** | Haulage and transport system | 19 | UG_ONLY | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XX** | Post mining land use plan | 20 | CLOSURE_UNIVERSAL | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XXI** | Progressive mine closure plan/ stage plan indicating stages at 1st, 3rd, 5th, 10th year of achieving rated capacity of the mine and end of life (showing area, volume, dump height etc. for OC and seam-wise layout projects and ventilation system in UG) | 21 | CLOSURE_UNIVERSAL | 1:2,000 / 1:5,000 stage series | 55 / 57 |
| **Plate XXII** | Year 30 Stage Plan | 22 | CLOSURE_CONDITIONAL | 1:2,000 / 1:5,000 | 55 / 57 |
| **Plate XXIII** | Reclamation plan for which detailed planning has been done | 23 | CLOSURE_UNIVERSAL | 1:2,000 / 1:5,000 | 55 / 57 |

---

## 4. Official Statutory Annexures Schedule (Section C)

| Official ID | Exact Official Title | Required Status | Applicability | Official Statutory Purpose | Source Page |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Annexure-I** | Copy of allotment order / Vesting order | MANDATORY | Universal | Legal entitlement of the block/mine | 51 / 53 |
| **Annexure-II** | Certificate of Qualified person (QP) / Accredited Mining Plan preparing agency (MPPA) certifying that project area is confined within the vested/allotted block boundary/ existing mining lessee (or State NOC, non-coal certificate, technical viability certificate) | MANDATORY | Universal (with conditional clauses if extending outside) | Block boundary confinement and non-encroachment verification | 51 / 53 |
| **Annexure-III** | Approval of the Company Board (giving undertaking for data correctness, QP eligibility, acceptance, statutory compliance with Mines Act 1952, CMR 2017, EP Act 1986, FC Act 1980, Financial Assurance, Reclamation and Rehabilitation before July 1st, Mine closure certificate and surrender of land) | MANDATORY | Universal | Corporate governance approval, data correctness undertaking, and statutory commitments | 51-53 / 53-55 |
| **Annexure-IV** | Copy of earlier approval of mining plan | CONDITIONAL | Revised Plans Only | Baseline reference for modifications/revisions | 53 / 55 |
| **Annexure-V** | Plan / chart showing schedule of Implementation of Mine closure activities (progressive and final closure) with duration of important activities | MANDATORY | Universal | Gantt chart timeline of closure execution | 53 / 55 |
| **Annexure-VI** | Non-refundable Application Fee Proof of the payment | MANDATORY | Universal | Evidence of statutory processing fee paid to CCO | 53 / 55 |
| **Annexure-VII** | Expert-Review Report Carried out by Accredited Mining Plan Preparing Agency (MPPA) | MANDATORY | Universal | Independent expert technical appraisal | 53 / 55 |
| **Annexure-VIII** | Other document (if any) | OPTIONAL | As Required | Supplementary statutory approvals, leases, or NOCs | 53 / 55 |

---

## 5. Official Statutory Certifications & Undertakings

| Certificate ID | Official Designation & Statutory Purpose | Signatory Authority | Mandated Statutory Content | Source Page |
| :--- | :--- | :--- | :--- | :--- |
| **Cert-1** | Qualified Person Block Boundary Confinement Certificate | Qualified Person (Rule 22C MCR 1960) / MPPA | Certifies that project area is strictly confined within allocated block boundary, or furnishes required State NOC and CMPDI non-coal/technical-viability proof | 32, 51, 54 / 34, 53, 56 |
| **Cert-2** | Board Undertaking on Data Correctness & Statutory Adherence | Company Board / Authorized Signatory | Undertaking for correctness of data, acceptance of Mining Plan, adherence to Mines Act 1952, CMR 2017, EP Act 1986, FC Act 1980 | 38, 51-52 / 40, 53-54 |
| **Cert-3** | Progressive & Final Mine Closure Execution Undertaking | Lessee / Nominated Owner | Undertaking that reclamation & rehabilitation shall follow approved closure plan; annual compliance report to CCO before 1st July; surrender of reclaimed land | 52-53 / 54-55 |
| **Cert-4** | Environmental Clearance (EC) & Forestry Clearance (FC) Compliance Undertaking | Lessee / Nominated Owner | Mandatory undertaking that mine operations shall be strictly executed in compliance with terms of EC and FC | 43-44 / 45-46 |

---

## 6. Official Statutory Escrow & Just Transformation Rules

### Rule A: Community Development & Livelihood Projects (5-Yearly Escrow Head)
- **Governing Clause**: Section 3.5.5(ii), Page 14 of 83 (PDF Page 16)
- **Mandatory Earmarking**: **A minimum of 25%** of the five-yearly escrow amount deposited shall be utilized for community development and livelihood-related activities.
- **Single-Activity Cap**: Claim for expenditure towards any one activity **shall not exceed one third (33.33%)** of the five-yearly total escrow amount earmarked for this head.
- **Scope of Activities**: Skill development, alternative livelihood projects (agriculture, handicrafts, poultry), drinking water, health facilities (per Appendix-IX).
- **Accounting Bucket**: Drawn progressively from the 5-yearly escrow reimbursement window.

### Rule B: Just Transformation Corpus (Final Mine Closure Head)
- **Governing Clause**: Section 3.5.5(iv), Page 15 of 83 (PDF Page 17)
- **Mandatory Earmarking**: **A corpus of 10% of the balance deposited amount from final mine closure cost** is created towards Just Transformation.
- **Execution Mandate**: The project proponent must prepare a specialized plan for socio-transition after mine closure in consultation with district administration, local authority, and stakeholders for sustained employment and economic diversification.
- **Release Condition**: The proponent must engage an agency and implement the Just Transformation plan **before the reimbursement of the remaining 90% of the balance escrow amount**.
- **Accounting Bucket**: Dedicated corpus created from the final closure settlement, distinct from the 25% 5-yearly progressive community development fund.
