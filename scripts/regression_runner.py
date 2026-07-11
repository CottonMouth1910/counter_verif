#!/usr/bin/env python3
"""
scripts/regression_runner.py

Reads config/test_config.yaml and runs each listed test with Questa's
vsim in batch mode (no GUI). Each regression run gets its own
timestamped folder under logs/, e.g.:

    logs/regression_Sat_20260711_143205/test1.log
    logs/regression_Sat_20260711_143205/test2.log
    ...

so runs from different days/times don't overwrite each other.
scripts/log_analyzer.py picks up the most recent regression folder
automatically (or a specific one via --run).

Assumes `make opt` (or `make regress`, which depends on opt) has
already built the work library and the counter_tb_opt snapshot in
sim/. This script does not compile or optimize -- it only elaborates
and runs against the existing optimized snapshot, once per test.

Usage (normally invoked via `make regress` from the sim/ directory):
    python3 ../scripts/regression_runner.py
    python3 ../scripts/regression_runner.py --config ../config/test_config.yaml
"""

import argparse
import datetime
import os
import subprocess
import sys

import yaml

# ---------------------------------------------------------------
# Paths -- resolved relative to this script's location so the
# script behaves the same regardless of the caller's cwd.
# ---------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)          # counter_verif/
SIM_DIR = os.path.join(ROOT_DIR, "sim")         # counter_verif/sim
LOG_DIR = os.path.join(ROOT_DIR, "logs")        # counter_verif/logs
DEFAULT_CONFIG = os.path.join(ROOT_DIR, "config", "test_config.yaml")

LIB = "work"
OPT_TOP = "counter_tb_opt"

# e.g. regression_Sat_20260711_143205
TIMESTAMP_FMT = "%a_%Y%m%d_%H%M%S"


def load_tests(config_path):
    """Load and return the list of test dicts from the YAML config."""
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    tests = data.get("tests", [])
    if not tests:
        print(f"No tests found in {config_path}", file=sys.stderr)
        sys.exit(1)
    return tests


def run_test(test, regression_log_dir):
    """Run a single test with vsim in batch mode. Returns the exit code."""
    name = test["name"]
    seed = test["seed"]
    verbosity = test["verbosity"]
    timeout_ns = test["timeout_ns"]

    log_path = os.path.join(regression_log_dir, f"{name}.log")

    cmd = [
        "vsim", "-c",
        "-lib", LIB,
        OPT_TOP,
        "-sv_seed", str(seed),
        f"+TESTNAME={name}",
        f"+UVM_VERBOSITY={verbosity}",
        f"+TIMEOUT_NS={timeout_ns}",
        "-l", log_path,
        "-do", "run -all; quit -f",
    ]

    print(f">>> Running {name}  (seed={seed}, verbosity={verbosity}, "
          f"timeout_ns={timeout_ns})")
    print(f"    log -> {log_path}")

    try:
        result = subprocess.run(cmd, cwd=SIM_DIR)
    except FileNotFoundError:
        print("ERROR: 'vsim' not found on PATH. Source your Questa "
              "setup script (e.g. `source /path/to/questa/settings.sh`) "
              "before running `make regress`.", file=sys.stderr)
        return 127

    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run regression from test_config.yaml")
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG,
        help="Path to test_config.yaml (default: config/test_config.yaml)",
    )
    args = parser.parse_args()

    tests = load_tests(args.config)

    regression_name = "regression_" + datetime.datetime.now().strftime(TIMESTAMP_FMT)
    regression_log_dir = os.path.join(LOG_DIR, regression_name)
    os.makedirs(regression_log_dir, exist_ok=True)

    print(f"Regression run: {regression_name}")
    print(f"Logs folder:    {regression_log_dir}\n")

    exit_codes = {}
    for test in tests:
        exit_codes[test["name"]] = run_test(test, regression_log_dir)

    print("\n=== Regression run complete ===")
    for name, code in exit_codes.items():
        status = "OK" if code == 0 else f"vsim exited {code}"
        print(f"  {name}: {status}")

    print(f"\nLogs written to {regression_log_dir}/<test>.log")
    print("Run `make parse_log` to analyze results (picks up this run automatically).")

    # Non-zero exit if any vsim invocation itself failed to run
    # (this is about the tool invocation, not pass/fail of the test
    # content -- that's log_analyzer.py's job).
    if any(code != 0 for code in exit_codes.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()