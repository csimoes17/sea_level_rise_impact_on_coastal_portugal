"""
12b_consolidate_adaptation.py
==============================
Consolidates all Pillar 3 adaptation-comparison CSVs into a single master file
for Tableau Dashboard 5 (Adaptation Break-Even Analysis).

Input files (must exist in the same directory as this script):
  mondego_bypass_comparison.csv       ← 10a: Mondego railway bypass
  tagus_bypass_comparison.csv         ← 10b: Tagus floodplain railway
  aveiro_bypass_comparison.csv        ← 10c: Aveiro Ria railway
  ports_adaptation_comparison.csv     ← 11a: Leixões / Lisbon / Setúbal ports
  vdg_adaptation_comparison.csv       ← 11b: Vasco da Gama bridge south approach
  a1_adaptation_comparison.csv        ← 11c: A1 motorway Azambuja

Output:
  pillar3_adaptation_master.csv       ← stacked, section column added, used in Tableau D5

Notes:
- The ports file (11a) already contains a port_name / section column — kept as-is.
- All other files get a `section` column derived from the filename.
- A `section_type` column is added (railway / road / port) for Tableau filtering.
- Run from the project Python directory:
    python 12b_consolidate_adaptation.py
"""

import os
import csv
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Map: filename → (section label, section_type)
SECTION_MAP = {
    "mondego_bypass_comparison.csv":   ("Mondego (railway)",         "Railway"),
    "tagus_bypass_comparison.csv":     ("Tagus floodplain (railway)", "Railway"),
    "aveiro_bypass_comparison.csv":    ("Aveiro Ria (railway)",       "Railway"),
    # "vdg_adaptation_comparison.csv": ("VdG south approach (road)", "Road"),  # REMOVED Session 28
    # VdG (11b) excluded: not updated with raise_requirements.csv scenario heights.
    "a1_adaptation_comparison.csv":    ("A1 Azambuja (road)",         "Road"),
    # New sections added Session 28 — raise heights from raise_requirements.csv
    "a14_adaptation_comparison.csv":                      ("A14 Mondego (road)",        "Road"),
    "algarve_faro_olhao_adaptation_comparison.csv":        ("Faro–Olhão (railway)",      "Railway"),
    "algarve_portimao_arade_adaptation_comparison.csv":    ("Portimão/Arade (railway)",  "Railway"),
}

PORTS_FILE = "ports_adaptation_comparison.csv"

OUTPUT_FILE = os.path.join(SCRIPT_DIR, "pillar3_adaptation_master.csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv(path):
    """Return list of dicts from a CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def detect_ports_section_col(header):
    """Find the column that names individual ports in the ports file."""
    for candidate in ("port_name", "section", "port", "name"):
        if candidate in header:
            return candidate
    return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_rows = []
    master_fieldnames = None

    # --- 1. Process single-section files ---
    for filename, (section_label, section_type) in SECTION_MAP.items():
        path = os.path.join(SCRIPT_DIR, filename)
        if not os.path.exists(path):
            print(f"  [SKIP] {filename} not found — run the relevant script first.")
            continue

        rows = read_csv(path)
        if not rows:
            print(f"  [SKIP] {filename} is empty.")
            continue

        for row in rows:
            row["section"]      = section_label
            row["section_type"] = section_type

        if master_fieldnames is None:
            master_fieldnames = list(rows[0].keys())
        else:
            for k in rows[0].keys():
                if k not in master_fieldnames:
                    master_fieldnames.append(k)

        all_rows.extend(rows)
        print(f"  [OK]   {filename}: {len(rows)} rows  →  section = '{section_label}'")

    # --- 2. Process ports file (already multi-section) ---
    ports_path = os.path.join(SCRIPT_DIR, PORTS_FILE)
    if os.path.exists(ports_path):
        rows = read_csv(ports_path)
        if rows:
            ports_section_col = detect_ports_section_col(list(rows[0].keys()))

            for row in rows:
                if ports_section_col and ports_section_col != "section":
                    row["section"] = row[ports_section_col]
                elif "section" not in row:
                    row["section"] = "Port (unknown)"
                row["section_type"] = "Port"

            if master_fieldnames is None:
                master_fieldnames = list(rows[0].keys())
            else:
                for k in rows[0].keys():
                    if k not in master_fieldnames:
                        master_fieldnames.append(k)

            all_rows.extend(rows)
            print(f"  [OK]   {PORTS_FILE}: {len(rows)} rows  →  section_type = 'Port'")
        else:
            print(f"  [SKIP] {PORTS_FILE} is empty.")
    else:
        print(f"  [SKIP] {PORTS_FILE} not found — run 11a_ports.py first.")

    # --- 3. Validate ---
    if not all_rows:
        print("\nERROR: No rows collected. Check that Pillar 3 scripts have been run.")
        sys.exit(1)

    # Ensure all rows have all fieldnames (fill missing with "")
    for row in all_rows:
        for fn in master_fieldnames:
            if fn not in row:
                row[fn] = ""

    # --- 4. Write master CSV ---
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=master_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    # --- 5. Summary ---
    sections  = sorted(set(r["section"]       for r in all_rows))
    sec_types = sorted(set(r["section_type"]  for r in all_rows))
    options   = sorted(set(r.get("option", r.get("option_label", "?")) for r in all_rows))

    print(f"\n  ✓  pillar3_adaptation_master.csv written: {len(all_rows)} rows")
    print(f"     Sections   : {sections}")
    print(f"     Types      : {sec_types}")
    print(f"     Options    : {options}")
    print(f"     Output     : {OUTPUT_FILE}")


if __name__ == "__main__":
    print("=== 12b: Consolidating Pillar 3 adaptation-comparison files ===\n")
    main()
