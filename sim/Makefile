# =============================================================
# Makefile for counter_verif (Questa, plain SystemVerilog)
# ==============================================================

RTL_DIR   := ../rtl
TB_DIR    := ../tb
LOG_DIR   := ../logs

LIB       := work
TOP       := counter_tb
OPT_TOP   := counter_tb_opt

RTL_SRC   := $(RTL_DIR)/counter.sv
TB_SRC    := $(TB_DIR)/counter_tb.sv

# Command-line overridable vars
TESTNAME  ?= test1
SEED      ?= 1
DEFS      ?=

# GUI options
NW      ?= 0      # NW=1 -> don't open GUI
GUI_DO  ?= 0      # GUI_DO=1 -> execute run.do when GUI opens

# ---------------------------------------------------------------
# Timestamped run directory: evaluated once per `make` invocation
# (':=' not '=' ), so `make sim` writes compile.log, opt.log, and
# the vsim log all into the same ../logs/<YYYYMMDD_HHMMSS>/ folder.
# ---------------------------------------------------------------
RUN_TS := $(shell date +%A_%Y%m%d_%H%M%S)
RUN_DIR := $(LOG_DIR)/$(RUN_TS)

.PHONY: lib compile opt sim run regress parse_log clean

# -------------------------------------------------------------
# 1. Create the working library
# -------------------------------------------------------------
lib:
	vlib $(LIB)

# -------------------------------------------------------------
# 2. Compile RTL + TB
# -------------------------------------------------------------
compile: lib | $(RUN_DIR)
	vlog -work $(LIB) $(DEFS) $(RTL_SRC) $(TB_SRC) \
		-l $(RUN_DIR)/compile.log

# -------------------------------------------------------------
# 3. Optimize into a named snapshot
# -------------------------------------------------------------
opt: compile | $(RUN_DIR)
	vopt -work $(LIB) \
	     +acc \
	     $(TOP) \
	     -o $(OPT_TOP) \
	     -l $(RUN_DIR)/opt.log

NW  ?= 0

sim: opt | $(RUN_DIR)
	vsim -c -lib $(LIB) $(OPT_TOP) \
		-sv_seed $(SEED) \
		+TESTNAME=$(TESTNAME) \
		-l $(RUN_DIR)/$(TESTNAME)_$(SEED).log \
		-do "run -all; quit -f"

ifeq ($(NW),1)
	vsim -lib $(LIB) $(OPT_TOP) \
		-sv_seed $(SEED) \
		+TESTNAME=$(TESTNAME)
else
	vsim -lib $(LIB) $(OPT_TOP) \
	-sv_seed $(SEED) \
	+TESTNAME=$(TESTNAME) \
	-do "do run.do; run -all"
endif

$(RUN_DIR):
	mkdir -p $(RUN_DIR)

# -------------------------------------------------------------
# 5. Run one test in batch mode, no GUI.
#    Flat log at ../logs/<TESTNAME>.log (not timestamped) so
#    scripts/log_analyzer.py can find it by test name.
# -------------------------------------------------------------
run: opt
	vsim -c -quiet -lib $(LIB) $(OPT_TOP) \
		-sv_seed $(SEED) \
		+TESTNAME=$(TESTNAME) \
		-l $(LOG_DIR)/$(TESTNAME).log \
		-do "run -all; quit -f" > /dev/null 2>&1

# -------------------------------------------------------------
# 6. Regression: runs every test listed in config/test_config.yaml
#    via scripts/regression_runner.py (batch mode, one flat log
#    per test in ../logs/<test>.log).
# -------------------------------------------------------------
regress: opt
	python3 ../scripts/regression_runner.py

# -------------------------------------------------------------
# 7. Parse logs and generate reports/summary.{csv,xlsx,yaml}
#    via scripts/log_analyzer.py.
# -------------------------------------------------------------
parse_log:
	python3 ../scripts/log_analyzer.py

# -------------------------------------------------------------
# 8. Clean
# -------------------------------------------------------------
clean:
	rm -rf $(LIB)
	rm -rf $(LOG_DIR)/*
	rm -f transcript vsim.wlf

.DEFAULT_GOAL := help

.PHONY: help

help:
	@echo ""
	@echo "================ counter_verif Makefile ================"
	@echo ""
	@echo "Targets:"
	@echo "  make lib                               Create work library"
	@echo "  make compile [DEFS=\"+define+DEBUG\"]    Compile RTL and TB"
	@echo "  make opt                               Optimize design"
	@echo "  make sim                               Run simulation and open Questa GUI"
	@echo "  make run                               Run one test, batch mode, no GUI"
	@echo "                                          -> ../logs/<TESTNAME>.log"
	@echo "  make regress                           Run all tests from config/test_config.yaml"
	@echo "                                          -> ../logs/<test>.log per test"
	@echo "  make parse_log                         Analyze logs -> reports/summary.{csv,xlsx,yaml}"
	@echo "  make clean                             Remove generated files"
	@echo ""
	@echo "Variables:"
	@echo "  TESTNAME=<name>    Test name (default: $(TESTNAME))"
	@echo "  SEED=<n>           Random seed (default: $(SEED))"
	@echo "  DEFS=\"...\"         Extra vlog defines"
	@echo "  NW=1               Do NOT open Questa GUI"
	@echo "Logs are written to ../logs/<YYYYMMDD_HHMMSS>/, one folder"
	@echo "Examples:"
	@echo "  make sim"
	@echo "  make sim TESTNAME=test1"
	@echo "  make sim TESTNAME=test1 SEED=10"
	@echo "  make sim TESTNAME=test1 SEED=10 NW=1"
	@echo "  make sim TESTNAME=test1 GUI_DO=1"
	@echo "  make run TESTNAME=test1 SEED=1"
	@echo "  make regress"
	@echo "  make parse_log"
	@echo ""
	@echo "========================================================"