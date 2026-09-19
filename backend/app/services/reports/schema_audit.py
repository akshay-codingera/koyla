"""
Schema Audit Command for Official Government Report Formats
Verifies integrity, relations, and derives authoritative counts from the machine-readable schema.
"""
import json
import os
import sys
from typing import Dict, Any, List

def audit_schema(schema_path: str = None) -> Dict[str, Any]:
    if not schema_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(base_dir, "mining_plan_2025_schema.json")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    nodes = schema.get("nodes", [])

    # Integrity check collections
    internal_ids = set()
    errors = []
    warnings = []

    # Valid parent IDs map
    all_node_ids = {n["internal_id"] for n in nodes if "internal_id" in n}

    # Counts
    front_matter_requirements = 0
    checklist_requirements = 0
    chapter_fields_parameters = 0
    prescribed_tables = 0
    plans_plates_drawings = 0
    annexure_supporting_documents = 0
    certification_signature_requirements = 0
    conditional_items = 0
    mandatory_items = 0
    items_requiring_human_input = 0
    items_requiring_external_attachments = 0

    # Official ID checks
    official_id_map = {}

    for idx, node in enumerate(nodes):
        iid = node.get("internal_id")
        oid = node.get("official_id")
        label = node.get("exact_official_label")
        pid = node.get("parent_id")
        ntype = node.get("node_type")
        seq = node.get("sequence")
        req = node.get("required_status")
        mapping_status = node.get("koyla_mapping_status")

        # 1. Duplicate internal_id check
        if not iid:
            errors.append(f"Node at index {idx} has missing or empty internal_id")
        elif iid in internal_ids:
            errors.append(f"Duplicate internal_id found: '{iid}'")
        else:
            internal_ids.add(iid)

        # 2. Official ID check
        if oid is not None:
            # Check duplicates per node type to ensure unique statutory numbering within category
            key = (ntype, oid)
            if key in official_id_map:
                errors.append(f"Duplicate official_id '{oid}' within node_type '{ntype}' (nodes '{official_id_map[key]}' and '{iid}')")
            else:
                official_id_map[key] = iid

        # 3. Missing sequence number check
        if seq is None or not isinstance(seq, int) or seq <= 0:
            errors.append(f"Node '{iid}' has missing or invalid sequence: {seq}")

        # 4. Missing label check
        if not label or not isinstance(label, str) or not label.strip():
            errors.append(f"Node '{iid}' has missing or empty exact_official_label")

        # 5. Invalid reference check
        if pid is not None and pid not in all_node_ids:
            errors.append(f"Node '{iid}' references non-existent parent_id '{pid}'")

        # 6. Orphaned node check (non-root nodes must have valid parent)
        # Root nodes: parent_id is None and node_type in ("FRONT_MATTER", "CHECKLIST", "CHAPTER", "PLAN_OR_PLATE", "ANNEXURE", "CERTIFICATION")
        if pid is None and ntype not in ("FRONT_MATTER", "CHECKLIST", "CHAPTER", "PLAN_OR_PLATE", "ANNEXURE", "CERTIFICATION"):
            errors.append(f"Orphaned schema node '{iid}' of type '{ntype}' with parent_id=None")

        # Actionable requirement node types
        actionable_types = ("FRONT_MATTER", "CHECKLIST", "FIELD", "TABLE", "PLATE", "PLAN_OR_PLATE", "ANNEXURE", "CERTIFICATION")

        # Derive counts
        if ntype == "FRONT_MATTER" and pid is not None:
            front_matter_requirements += 1
        elif ntype == "CHECKLIST" and pid is not None:
            checklist_requirements += 1
        elif ntype == "FIELD":
            chapter_fields_parameters += 1
        elif ntype == "TABLE":
            prescribed_tables += 1
        elif ntype in ("PLATE", "PLAN_OR_PLATE") and pid is not None:
            plans_plates_drawings += 1
        elif ntype == "ANNEXURE" and pid is not None:
            annexure_supporting_documents += 1
        elif ntype == "CERTIFICATION" and pid is not None:
            certification_signature_requirements += 1

        # Count requirement status across actionable requirement items (excluding structural containers)
        if pid is not None and ntype in actionable_types:
            if req == "CONDITIONAL":
                conditional_items += 1
            elif req == "MANDATORY":
                mandatory_items += 1

            if mapping_status == "REQUIRES_HUMAN_INPUT":
                items_requiring_human_input += 1
            elif mapping_status == "REQUIRES_EXTERNAL_ATTACHMENT":
                items_requiring_external_attachments += 1

    total_chapter_parameters = chapter_fields_parameters + prescribed_tables
    total_requirements = (
        front_matter_requirements
        + checklist_requirements
        + total_chapter_parameters
        + plans_plates_drawings
        + annexure_supporting_documents
        + certification_signature_requirements
    )

    result = {
        "status": "PASS" if not errors else "FAIL",
        "format_id": schema.get("format_id"),
        "document_title": schema.get("document_title"),
        "om_number": schema.get("om_number"),
        "om_date": schema.get("om_date"),
        "total_nodes": len(nodes),
        "total_actionable_requirements": total_requirements,
        "counts": {
            "front_matter_requirements": front_matter_requirements,
            "checklist_requirements": checklist_requirements,
            "total_chapter_parameters": total_chapter_parameters,
            "chapter_fields_parameters": chapter_fields_parameters,
            "prescribed_tables": prescribed_tables,
            "plans_plates_drawings": plans_plates_drawings,
            "annexure_supporting_documents": annexure_supporting_documents,
            "certification_signature_requirements": certification_signature_requirements,
            "conditional_items": conditional_items,
            "mandatory_items": mandatory_items,
            "items_requiring_human_input": items_requiring_human_input,
            "items_requiring_external_attachments": items_requiring_external_attachments
        },
        "errors": errors,
        "warnings": warnings
    }

    return result

def main():
    try:
        report = audit_schema()
    except Exception as e:
        print(f"SCHEMA AUDIT FATAL ERROR: {e}")
        sys.exit(1)

    print("================================================================================")
    print(" KOYLA OFFICIAL REPORT SCHEMA AUDIT REPORT")
    print(f" Document: {report['document_title']}")
    print(f" Reference: OM {report['om_number']} dated {report['om_date']}")
    print("================================================================================")
    print(f" Audit Status: {report['status']}")
    print(f" Total Schema Nodes (incl. hierarchy): {report['total_nodes']}")
    print(f" Total Prescribed Requirements:        {report['total_actionable_requirements']}")
    print("--------------------------------------------------------------------------------")
    print(" AUTOMATED INVENTORY COUNTS (DERIVED FROM OFFICIAL SCHEMA JSON):")
    counts = report["counts"]
    print(f"   * Front-matter requirements:               {counts['front_matter_requirements']}")
    print(f"   * Checklist requirements:                  {counts['checklist_requirements']}")
    print(f"   * Chapter fields / parameters:             {counts['chapter_fields_parameters']}")
    print(f"   * Prescribed tables:                       {counts['prescribed_tables']}")
    print(f"   * Plans / plates / drawings:               {counts['plans_plates_drawings']}")
    print(f"   * Annexure / supporting-documents:         {counts['annexure_supporting_documents']}")
    print(f"   * Certification / signature requirements:  {counts['certification_signature_requirements']}")
    print("--------------------------------------------------------------------------------")
    print(f"   * Mandatory items:                         {counts['mandatory_items']}")
    print(f"   * Conditional items:                       {counts['conditional_items']}")
    print(f"   * Items requiring human input:             {counts['items_requiring_human_input']}")
    print(f"   * Items requiring external/CAD/GIS attach: {counts['items_requiring_external_attachments']}")
    print("================================================================================")

    if report["errors"]:
        print(f"\nFAILED WITH {len(report['errors'])} ERRORS:")
        for err in report["errors"]:
            print(f" [ERROR] {err}")
        sys.exit(1)
    else:
        print("\nALL INTEGRITY CHECKS PASSED: Zero duplicates, zero orphaned nodes, valid references.")
        sys.exit(0)

if __name__ == "__main__":
    main()
