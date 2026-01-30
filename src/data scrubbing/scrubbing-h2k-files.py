#!/usr/bin/env python3
"""
ERS/H2K sanitizer (general, CLI-only paths)

Features:
- Works on any folder; all paths come from CLI flags (no hardcoded dirs).
- Either edits files in-place (--in-place) OR copies to --dest (keeps original filenames).
- Sets <Identification> (default: file stem; configurable via --id-source).
- Scrubs PII under ProgramInformation/File (incl. CompanyTelephone).
- Scrubs Client name/phone/addresses; ensures UnitNumber exists.
- Province set from Weather/Region/English (maps "YUKON TERRITORY" -> "YUKON").
- Program/Options: deletes conditional input nodes when flags enabled; sets all flags to false.
- Vermiculite set to code="1", English="Unknown", French="Inconnu".
- <Results><Tsv>: wipes ALL values/text under every <Tsv> (future-proof). Optional: --drop-tsv deletes Tsv nodes.
- Global scrub anywhere in the XML for: UserTelephone, UserExtension, CompanyTelephone, EAphone, SOphone, HomeownerAuthorizationId.
- ERS results: clears value="" for tags matching HOC[a-zA-Z].

Python 3.10+ required (for | type unions).
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict


# ---------------------------
# XML helper utilities
# ---------------------------

def find(elem: ET.Element | None, path: str) -> ET.Element | None:
    if elem is None:
        return None
    return elem.find(path)

def ensure_child(parent: ET.Element | None, tag: str) -> ET.Element | None:
    if parent is None:
        return None
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child

def set_text(elem: ET.Element | None, text: str) -> None:
    if elem is not None:
        elem.text = text

def set_attrib(elem: ET.Element | None, key: str, value: str) -> None:
    if elem is not None:
        elem.set(key, value)

def delete_if_exists(parent: ET.Element | None, child_tag: str) -> None:
    if parent is None:
        return
    child = parent.find(child_tag)
    if child is not None:
        parent.remove(child)

def write_xml(tree: ET.ElementTree, path: Path) -> None:
    tree.write(path, encoding="utf-8", xml_declaration=True)

def province_initials(region_english: str | None) -> str:
    """
    First letter of each word, uppercase. E.g. "NOVA SCOTIA" -> "NS".
    """
    if not region_english:
        return ""
    parts = [p.strip() for p in region_english.strip().split() if p.strip()]
    return "".join(p[0] for p in parts).upper()

def truncate_builder_name(builder_text: str | None) -> str:
    """
    Match Ruby behavior: uppercased, left-stripped, first 5 chars only.
    """
    if not builder_text:
        return ""
    s = builder_text.lstrip().upper()
    return s[:5]

def tag_matches_hoc_alpha(tag: str | None) -> bool:
    return bool(tag) and re.match(r"^HOC[a-zA-Z]", tag) is not None


# ---------------------------
# Global PII scrub targets (anywhere in the XML)
# ---------------------------

# Tags to clear anywhere in the document (text content only)
GLOBAL_CLEAR_TEXT_TAGS = {
    "UserTelephone",
    "UserExtension",
    "CompanyTelephone",
    "HomeownerAuthorizationId",
}

# Tags that often store values as attributes (clear their 'value' and any text variants)
GLOBAL_CLEAR_ATTR_TAGS = {
    "EAphone",
    "SOphone",
    "CompanyTelephone",  # include here too: some files encode it either way
}


# ---------------------------
# Core sanitizer
# ---------------------------

def process_xml_file(
    xml_path: Path,
    identification_value: str | None,
    builder_code_map: dict[str, str],
    per_province_counter: defaultdict[str, int],
    drop_tsv: bool = False,
) -> tuple[str, str]:
    """
    Open XML at xml_path, sanitize in-place.

    Returns:
      (builder_raw_5char, builder_assigned_code)
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # ProgramInformation
    pi = find(root, "HouseFile/ProgramInformation")
    file_node = find(pi, "File")
    weather_region_english = find(find(find(pi, "Weather"), "Region"), "English")
    weather_region_english_text = weather_region_english.text if weather_region_english is not None else ""

    # File attributes / text
    set_attrib(file_node, "evaluationDate", str(date.today()))
    if identification_value is not None:
        set_text(find(file_node, "Identification"), identification_value)
    set_text(find(file_node, "PreviousFileId"), "")
    set_text(find(file_node, "EnrollmentId"), "")
    set_text(find(file_node, "TaxNumber"), "")
    set_text(find(file_node, "EnteredBy"), "Energy Advisor")
    set_text(find(file_node, "Company"), "Private")
    set_text(find(file_node, "CompanyTelephone"), "")  # scrub

    # Province initials from Weather/Region/English
    province_code = province_initials(weather_region_english_text)

    # Builder code mapping (privacy-preserving)
    builder_raw_text = (find(file_node, "BuilderName").text
                        if find(file_node, "BuilderName") is not None else "")
    builder_raw_5 = truncate_builder_name(builder_raw_text)

    if builder_raw_5 not in builder_code_map:
        if re.search(r"H0000", builder_raw_5):
            builder_code_map[builder_raw_5] = "H0000"
        else:
            n = per_province_counter[province_code]
            # If province_code is empty (missing Weather/Region/English), just use the number
            builder_code_map[builder_raw_5] = f"{province_code}-{n}" if province_code else f"{n}"
            per_province_counter[province_code] = n + 1

    builder_assigned_code = builder_code_map.get(builder_raw_5, "")
    set_text(find(file_node, "BuilderName"), builder_assigned_code)

    # Ensure HomeownerAuthorizationId exists and is cleared
    # (If missing, create; if present, blank)
    if file_node is not None:
        h = file_node.find("HomeownerAuthorizationId")
        if h is None:
            h = ET.SubElement(file_node, "HomeownerAuthorizationId")
        h.text = ""

    # Client data
    client = find(pi, "Client")
    set_text(find(find(client, "Name"), "First"), "")
    set_text(find(find(client, "Name"), "Last"), "")
    set_text(find(client, "Telephone"), "")

    street_addr = find(client, "StreetAddress")
    set_text(find(street_addr, "Street"), "")
    unit_num = find(street_addr, "UnitNumber")
    if unit_num is None:
        unit_num = ensure_child(street_addr, "UnitNumber")
    set_text(unit_num, "")
    set_text(find(street_addr, "City"), "")

    # Province from Weather.Region.English (Yukon mapping)
    province_text = weather_region_english_text or ""
    if province_text.strip().upper() == "YUKON TERRITORY":
        province_text = "YUKON"
    set_text(find(street_addr, "Province"), province_text)
    set_text(find(street_addr, "PostalCode"), "")

    # Mailing address
    mailing = find(client, "MailingAddress")
    set_text(find(mailing, "Name"), "")
    set_text(find(mailing, "Street"), "")
    mu = find(mailing, "UnitNumber")
    if mu is None:
        mu = ensure_child(mailing, "UnitNumber")
    set_text(mu, "")
    set_text(find(mailing, "City"), "")
    set_text(find(mailing, "Province"), "")
    set_text(find(mailing, "PostalCode"), "")

    # PossessionDate selected="false"
    poss_date = find(find(pi, "Justifications"), "PossessionDate")
    set_attrib(poss_date, "selected", "false")

    # Remove Information node
    delete_if_exists(pi, "Information")

    # Program options & Vermiculite, and ERS conditional input removal
    prog = find(root, "HouseFile/Program")
    options = find(prog, "Options")
    delete_if_exists(options, "HouseholdOperatingConditions")

    main_opts = find(options, "Main")
    verm_parent = find(main_opts, "Vermiculite")
    if verm_parent is not None:
        verm_parent.set("code", "1")
        set_text(find(verm_parent, "English"), "Unknown")
        set_text(find(verm_parent, "French"), "Inconnu")

    def main_attr_is_true(attr: str) -> bool:
        return (main_opts is not None and main_opts.get(attr, "").lower() == "true")

    if main_attr_is_true("applyHouseholdOperatingConditions"):
        delete_if_exists(options, "HouseholdOperatingConditions")
    if main_attr_is_true("applyReducedOperatingConditions"):
        delete_if_exists(options, "ReducedOperatingConditions")
    if main_attr_is_true("waterConservation"):
        delete_if_exists(options, "WaterConservation")
    if main_attr_is_true("atypicalElectricalLoads"):
        delete_if_exists(options, "AtypicalElectricalLoads")
    if main_attr_is_true("referenceHouse"):
        delete_if_exists(options, "ReferenceHouse")

    if main_opts is not None:
        main_opts.set("applyHouseholdOperatingConditions", "false")
        main_opts.set("applyReducedOperatingConditions", "false")
        main_opts.set("atypicalElectricalLoads", "false")
        main_opts.set("referenceHouse", "false")
        main_opts.set("waterConservation", "false")

    # === TSV results: clear ALL 'value' attributes and any text under every <Tsv> ===
    if drop_tsv:
        # Optionally drop the entire <Tsv> node(s)
        for results in root.findall(".//Results"):
            tsv_node = results.find("Tsv")
            if tsv_node is not None:
                results.remove(tsv_node)
    else:
        for tsv in root.findall(".//Tsv"):
            for el in tsv.iter():
                if "value" in el.attrib:
                    el.set("value", "")
                if el.text and el.text.strip():
                    el.text = ""

    # === Global scrubs for known phone/PII fields ANYWHERE in the XML ===
    # Clear element text (e.g., <UserTelephone>867...</UserTelephone>)
    for tag in GLOBAL_CLEAR_TEXT_TAGS:
        for el in root.findall(f".//{tag}"):
            el.text = ""

    # Clear 'value' attributes and any text variants (e.g., <EAphone value="..."/>)
    for tag in GLOBAL_CLEAR_ATTR_TAGS:
        for el in root.findall(f".//{tag}"):
            if "value" in el.attrib:
                el.set("value", "")
            if el.text and el.text.strip():
                el.text = ""

    # === ERS results: for any element tag matching HOC[a-zA-Z], set value="" ===
    for node in root.findall(".//Results//*"):
        if tag_matches_hoc_alpha(node.tag):
            node.set("value", "")

    write_xml(tree, xml_path)
    return builder_raw_5, builder_assigned_code


# ---------------------------
# Driver
# ---------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sanitize ERS *.H2K XMLs (paths only via CLI; no hardcoded dirs)."
    )
    group_dest = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument("--origin", required=True, help="Folder containing source .H2K files")
    group_dest.add_argument("--dest", help="Destination folder for sanitized copies (keeps same filenames)")
    group_dest.add_argument("--in-place", action="store_true", help="Edit files in-place under --origin (NO copying)")
    parser.add_argument("--recurse", action="store_true", help="Recurse into subfolders under --origin")
    parser.add_argument(
        "--id-source",
        choices=["stem", "name", "none"],
        default="stem",
        help="What to write into <Identification>: file stem (default), full filename (name), or do not change (none)."
    )
    parser.add_argument(
        "--drop-tsv", action="store_true",
        help="Delete <Tsv> sections entirely instead of blanking their values."
    )
    parser.add_argument(
        "--summary", help="Optional path to write Summary CSV; if omitted, writes to --dest or --origin (in-place)."
    )
    args = parser.parse_args()

    origin = Path(args.origin)
    if not origin.exists():
        print(f"[ERROR] Origin folder does not exist: {origin}", file=sys.stderr)
        sys.exit(2)

    # Resolve dest/in-place
    if args.in_place:
        dest = origin
        print("[INFO] Editing files in-place (no copies).")
    else:
        dest = Path(args.dest).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Writing sanitized copies to: {dest}")

    # Enumerate files (.H2K and .h2k)
    patterns = ["**/*.H2K", "**/*.h2k"] if args.recurse else ["*.H2K", "*.h2k"]
    files: list[Path] = []
    for patt in patterns:
        files.extend(origin.glob(patt))
    files = sorted(set(files))
    if not files:
        print("[INFO] No .H2K files found.")
        return

    # Summary CSV path
    if args.summary:
        summary_path = Path(args.summary).resolve()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        default_summary_base = dest if not args.in_place else origin
        summary_path = (default_summary_base / "Summary.csv").resolve()

    # Init builder mapping (province-based counters start at 1000)
    per_province_counter = defaultdict(lambda: 1000)
    builder_code_map: dict[str, str] = {}

    with summary_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["<Identification>", "Filename", "BuilderRawFirst5", "BuilderAssignedCode"])

        for src in files:
            # Determine target path
            if args.in_place:
                target = src
            else:
                rel = src.relative_to(origin)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)

            # Determine <Identification> content
            if args.id_source == "stem":
                identification_value = target.stem
            elif args.id_source == "name":
                identification_value = target.name
            else:  # "none"
                identification_value = None

            try:
                builder_raw5, builder_assigned = process_xml_file(
                    target,
                    identification_value=identification_value,
                    builder_code_map=builder_code_map,
                    per_province_counter=per_province_counter,
                    drop_tsv=args.drop_tsv,
                )
                writer.writerow([identification_value if identification_value is not None else "", target.name, builder_raw5, builder_assigned])
                print(f"[OK] {target.name} sanitized | <Identification>={identification_value if identification_value is not None else '(unchanged)'} | Builder:{builder_raw5} -> {builder_assigned}")
            except Exception as ex:
                print(f"[ERROR] Failed processing {target}: {ex}", file=sys.stderr)

    print(f"[DONE] Processed {len(files)} file(s). Summary: {summary_path}")

if __name__ == "__main__":
    main()