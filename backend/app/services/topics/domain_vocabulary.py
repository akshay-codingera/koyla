"""
Domain vocabulary and stopwords for Indian Coal Mining and Statutory Reporting.
Provides curated lists for text cleaning, domain term preservation, and noise reduction.
"""

# Indian Coal Mining Domain Entities and Technical Terminology
COAL_MINING_TERMS = {
    # Geology & Reserves
    "geological reserve", "proved reserve", "indicated reserve", "inferred reserve",
    "extractable reserve", "mineable reserve", "in-situ reserve",
    "seam", "seam thickness", "parting", "strike", "dip", "gradient",
    "overburden", "stripping ratio", "specific gravity", "lithology",
    "gross calorific value", "gcv", "proximate analysis", "ultimate analysis",
    "ash content", "moisture content", "volatile matter", "fixed carbon",
    "useful heat value", "uhv", "coal grade", "grade g1", "grade g2", "grade g3",
    "grade g4", "grade g5", "grade g6", "grade g7", "grade g8", "grade g9",
    "grade g10", "grade g11", "grade g12", "grade g13", "grade g14", "grade g15",
    "grade g16", "grade g17", "coking coal", "non-coking coal", "thermal coal",
    "prime coking", "medium coking", "semi coking", "metallurgical coal",
    "coal seam", "borehole", "core drilling", "strata", "strata control",
    
    # Mining Operations & Methods
    "opencast", "underground", "surface mining", "bord and pillar",
    "longwall", "continuous miner", "shovel dumper", "dragline",
    "highwall mining", "blasting", "drilling", "crushing",
    "run of mine", "rom", "coal handling plant", "chp", "washery",
    "yield percentage", "rejects", "railway siding", "siding",
    "merry go round", "mgr", "haul road", "dump yard", "ob dump",
    "external dump", "internal dump", "backfilling", "bench height",
    
    # Mine Closure & Environment
    "mine closure", "progressive mine closure", "final mine closure",
    "mine closure plan", "closure plan", "post-closure", "reclamation",
    "technical reclamation", "biological reclamation", "afforestation",
    "topsoil preservation", "topsoil management", "green belt",
    "subsidence", "subsidence management", "degasification",
    "coal bed methane", "cbm", "spontaneous combustion", "water treatment",
    "effluent treatment", "acid mine drainage", "bank guarantee",
    "escrow account", "financial assurance", "corpus fund",
    
    # Organizations & Authorities
    "coal india limited", "cil", "cmpdi", "cco", "coal controller",
    "dgms", "directorate general of mines safety", "moefcc",
    "ministry of coal", "moc", "niti aayog", "central pollution control board",
    "cpcb", "spcb", "state pollution control board",
    "ecl", "eastern coalfields", "bccl", "bharat coking coal",
    "ccl", "central coalfields", "wcl", "western coalfields",
    "secl", "south eastern coalfields", "mcl", "mahanadi coalfields",
    "ncl", "northern coalfields", "necl", "north eastern coalfields",
}

# Statutory and Regulatory Terms to Strictly Preserve During Cleaning
STATUTORY_TERMS_PRESERVED = {
    "rule", "section", "act", "regulation", "clause", "sub-section", "sub-rule",
    "mines act", "mines act 1952", "coal mines regulations", "cmr 2017", "cmr",
    "mines and minerals development and regulation act", "mmdr act", "mmdr",
    "mineral concession rules", "mcr 1960", "mcr",
    "environment protection act", "epa 1986", "epa",
    "forest conservation act", "fca 1980", "fca",
    "water prevention and control of pollution act", "water act",
    "air prevention and control of pollution act", "air act",
    "environmental clearance", "ec", "forest clearance", "fc",
    "consent to establish", "cte", "consent to operate", "cto",
    "office memorandum", "om", "statutory", "appendix", "guidelines",
    "form", "schedule", "compliance", "statutory compliance",
    "qualified person", "qp", "competent authority",
}

# Domain Stopwords to Filter Out (Boilerplate / Layout noise that does not carry semantic topic signal)
DOMAIN_STOPWORDS = {
    "page", "pages", "table", "tables", "annexure", "annexures",
    "figure", "figures", "plate", "plates", "drawing", "drawings",
    "dated", "date", "ref", "reference", "no", "vide", "etc",
    "herein", "thereof", "whereas", "abovementioned", "aforesaid",
    "hereby", "sno", "sl", "sr", "total", "subtotal",
    "nil", "na", "n/a", "yes", "applicable", "not applicable",
    "enclosed", "attached", "annexed", "duly", "undersigned",
    "authorized signatory", "signature", "seal", "stamp",
    "chapter", "para", "paragraph", "item", "serial",
    "sheet", "volume", "part", "section_header",
}
