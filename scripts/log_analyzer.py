#!/usr/bin/env python3
"""
scripts/log_analyzer.py

Reads config/test_config.yaml to get the list of tests, then analyzes
the logs from a single regression run:

    logs/regression_<weekday>_<YYYYMMDD>_<HHMMSS>/<test>.log

By default it picks the MOST RECENT logs/regression_* folder
(scripts/regression_runner.py creates a new one per `make regress`
run). Pass --run <folder_name> to analyze an older run instead. If no
regression_* folder exists at all, it falls back to flat logs/<test>.log
(the ad-hoc `make run` case).

For each test log it counts UVM_INFO / UVM_WARNING / UVM_ERROR /
UVM_FATAL occurrences, detects the pass/fail result line, and extracts
the sv_seed the test was run with (from the `vsim ... -sv_seed <N> ...`
invocation line at the top of the log), using only plain string
methods (count(), find(), split(), splitlines(), "in") -- no regex.

Expected result line format in each log, e.g.:
    TEST_CASE: test1 RESULT: PASSED
    TEST_CASE: test2 RESULT: FAILED

Expected seed on the vsim command-line echo at the top of the log, e.g.:
    # vsim -c -lib work counter_tb_opt -sv_seed 2 "+TESTNAME=test2" ...

Reports are written into the folder matching the run being analyzed:
    reports/regression_<weekday>_<YYYYMMDD>_<HHMMSS>/summary.csv
    reports/regression_<weekday>_<YYYYMMDD>_<HHMMSS>/summary.xlsx
    reports/regression_<weekday>_<YYYYMMDD>_<HHMMSS>/summary.yaml
(or flat reports/ in the ad-hoc fallback case)

summary.csv   -- via stdlib csv module
summary.xlsx  -- hand-written minimal xlsx, via zipfile -- no openpyxl
summary.yaml  -- via PyYAML, default_flow_style=False, sort_keys=False

Only depends on PyYAML (yaml) beyond the standard library -- no
pandas, no openpyxl.

Prints an overall PASS/FAIL count to the console when finished.

Usage (normally invoked via `make parse_log` from the sim/ directory):
    python3 ../scripts/log_analyzer.py
    python3 ../scripts/log_analyzer.py --run regression_Sat_20260711_143205
"""

import argparse
import csv
import glob
import os
import sys
import zipfile
from xml.sax.saxutils import escape as xml_escape

import yaml

# ---------------------------------------------------------------
# Paths -- resolved relative to this script's location so the
# script behaves the same regardless of the caller's cwd.
# ---------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)                 # counter_verif/
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "test_config.yaml")
LOG_DIR = os.path.join(ROOT_DIR, "logs")
REPORT_DIR = os.path.join(ROOT_DIR, "reports")

MARKERS = ("UVM_INFO", "UVM_WARNING", "UVM_ERROR", "UVM_FATAL")
SEED_FLAG = "-sv_seed"


FIELDS = ["test", "seed", "errors", "warnings", "fatals", "result"]
NUMERIC_FIELDS = {"seed", "errors", "warnings", "fatals"}


def _col_letter(idx):
    """0-based column index -> Excel column letter (0 -> A, 1 -> B, ...)."""
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def write_xlsx(summary, xlsx_path):
    """
    Write a minimal valid .xlsx using only the stdlib (zipfile + raw
    XML). An .xlsx is just a zip of XML parts, so no openpyxl/pandas
    is required. Numeric fields (seed/errors/warnings/fatals) are
    written as real numbers; test/result are written as inline
    strings. A non-numeric seed (e.g. "UNKNOWN") falls back to a
    string cell so the file never gets a malformed <v>.
    """
    rows = [FIELDS] + [[row[f] for f in FIELDS] for row in summary]

    sheet_rows_xml = []
    for r, row in enumerate(rows, start=1):
        cells_xml = []
        for c, value in enumerate(row):
            ref = f"{_col_letter(c)}{r}"
            field = FIELDS[c]
            is_numeric_cell = (
                r > 1
                and field in NUMERIC_FIELDS
                and str(value).lstrip("-").isdigit()
            )
            if is_numeric_cell:
                cells_xml.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = xml_escape(str(value))
                cells_xml.append(
                    f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'
                )
        sheet_rows_xml.append(f'<row r="{r}">' + "".join(cells_xml) + "</row>")

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows_xml) + "</sheetData>"
        "</worksheet>"
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )

    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(xlsx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", root_rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def find_latest_regression_dir():
    """
    Return the path of the most recently modified logs/regression_*
    folder, or None if there isn't one (e.g. only ad-hoc `make run`
    logs exist).
    """
    candidates = glob.glob(os.path.join(LOG_DIR, "regression_*"))
    candidates = [c for c in candidates if os.path.isdir(c)]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def resolve_run_dirs(run_name):
    """
    Decide which logs/ folder to read from and which reports/ folder
    to write to.

    - If --run <name> was given, use logs/<name> explicitly.
    - Otherwise, use the most recent logs/regression_* folder if one
      exists.
    - Otherwise, fall back to flat logs/ / reports/ (single ad-hoc
      `make run` logs, not part of a regression).

    Returns (log_dir, report_dir, label).
    """
    if run_name:
        log_dir = os.path.join(LOG_DIR, run_name)
        if not os.path.isdir(log_dir):
            print(f"Requested run not found: {log_dir}", file=sys.stderr)
            sys.exit(1)
        return log_dir, os.path.join(REPORT_DIR, run_name), run_name

    latest = find_latest_regression_dir()
    if latest:
        name = os.path.basename(latest)
        return latest, os.path.join(REPORT_DIR, name), name

    return LOG_DIR, REPORT_DIR, "(flat logs/, no regression run found)"


def load_test_names(config_path):
    """Return the list of test names from test_config.yaml."""
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return [t["name"] for t in data.get("tests", [])]


def extract_seed(line):
    """
    Given a line containing '-sv_seed', return the token right after
    it (the seed value), using only string methods. Returns None if
    the flag isn't followed by anything (malformed line).

    e.g. '# vsim -c -lib work counter_tb_opt -sv_seed 2 "+TESTNAME=..."'
    -> "2"
    """
    tokens = line.split()
    for i, tok in enumerate(tokens):
        if tok == SEED_FLAG and i + 1 < len(tokens):
            return tokens[i + 1]
    return None


def analyze_log(log_path):
    """
    Scan a single log file and return a dict with counts of each
    UVM message severity, the sv_seed the run used, and the
    PASS/FAIL/UNKNOWN result -- using only string methods (no regex).
    """
    counts = {"UVM_INFO": 0, "UVM_WARNING": 0, "UVM_ERROR": 0, "UVM_FATAL": 0}
    result = "UNKNOWN"
    seed = "UNKNOWN"

    if not os.path.isfile(log_path):
        return counts, seed, "MISSING"

    with open(log_path, "r", errors="replace") as f:
        text = f.read()

    for line in text.splitlines():
        # A line can in principle carry more than one marker
        # occurrence -- count() handles that; "in" alone would not.
        for marker in MARKERS:
            if marker in line:
                counts[marker] += line.count(marker)

        # The seed only ever appears once, on the vsim invocation
        # line echoed at the top of the log. Grab it the first time
        # we see it and don't bother looking again.
        if seed == "UNKNOWN" and SEED_FLAG in line:
            found = extract_seed(line)
            if found is not None:
                seed = found

        # Look for the "TEST_CASE ... RESULT: PASSED/FAILED" line.
        if "TEST_CASE" in line and "RESULT:" in line:
            idx = line.find("RESULT:")
            after_result = line[idx + len("RESULT:"):].strip()
            # First whitespace-delimited token after "RESULT:"
            token = after_result.split()[0] if after_result else ""
            if "PASS" in token.upper():
                result = "PASSED"
            elif "FAIL" in token.upper():
                result = "FAILED"

    return counts, seed, result


def build_summary(test_names, log_dir):
    """Build the list-of-dicts summary, one entry per test."""
    summary = []
    for name in test_names:
        log_path = os.path.join(log_dir, f"{name}.log")
        counts, seed, result = analyze_log(log_path)
        summary.append({
            "test": name,
            "seed": seed,
            "errors": counts["UVM_ERROR"],
            "warnings": counts["UVM_WARNING"],
            "fatals": counts["UVM_FATAL"],
            "result": result,
        })
    return summary


def write_reports(summary, report_dir):
    os.makedirs(report_dir, exist_ok=True)

    csv_path = os.path.join(report_dir, "summary.csv")
    xlsx_path = os.path.join(report_dir, "summary.xlsx")
    yaml_path = os.path.join(report_dir, "summary.yaml")

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(summary)

    write_xlsx(summary, xlsx_path)

    with open(yaml_path, "w") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

    return csv_path, xlsx_path, yaml_path


def main():
    parser = argparse.ArgumentParser(
        description="Analyze regression logs and generate reports"
    )
    parser.add_argument(
        "--run", default=None,
        help=(
            "Name of a specific regression folder under logs/ to analyze "
            "(e.g. regression_Sat_20260711_143205). Defaults to the most "
            "recent logs/regression_* folder; falls back to flat logs/ "
            "if none exist."
        ),
    )
    args = parser.parse_args()

    if not os.path.isfile(CONFIG_PATH):
        print(f"Config not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    log_dir, report_dir, label = resolve_run_dirs(args.run)
    print(f"Analyzing run: {label}")
    print(f"  reading logs from  {log_dir}")
    print(f"  writing reports to {report_dir}\n")

    test_names = load_test_names(CONFIG_PATH)
    summary = build_summary(test_names, log_dir)
    csv_path, xlsx_path, yaml_path = write_reports(summary, report_dir)

    print("Reports written:")
    print(f"  {csv_path}")
    print(f"  {xlsx_path}")
    print(f"  {yaml_path}")

    passed = sum(1 for row in summary if row["result"] == "PASSED")
    failed = sum(1 for row in summary if row["result"] == "FAILED")
    other = len(summary) - passed - failed

    print("\n=== Overall Result ===")
    print(f"  PASSED: {passed}")
    print(f"  FAILED: {failed}")
    if other:
        print(f"  UNKNOWN/MISSING: {other}")
    print(f"  TOTAL:  {len(summary)}")


if __name__ == "__main__":
    main()