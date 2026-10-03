# World's Edge Group trade-report platform
# Usage: make all ISSUE=2026-10-canola-china
ISSUE   ?= 2026-10-canola-china
VINTAGE ?= pinned
UV      ?= uv
RUN      = $(UV) run python -m weg

.PHONY: help setup download clean analyze figures report all test archive lock

help:
	@echo "Targets (ISSUE=$(ISSUE), VINTAGE=$(VINTAGE)):"
	@echo "  setup     install Python 3.12 env from uv.lock (frozen)"
	@echo "  download  fetch raw data for the issue into data/raw and record manifests/data_manifest.csv"
	@echo "            VINTAGE=latest pulls live sources and records a new vintage; default resolves the pinned release"
	@echo "  clean     build standard parquet tables in data/clean"
	@echo "  analyze   compute outputs/numbers.json and outputs/tables for the issue"
	@echo "  figures   render outputs/figures (SVG + PNG)"
	@echo "  report    render REPORT.md from REPORT.template.md and numbers.json"
	@echo "  all       setup download clean analyze figures"
	@echo "  test      pytest (no network needed)"
	@echo "  archive   upload the issue's raw snapshot as a GitHub release asset"
	@echo "  lock      regenerate uv.lock"

setup:
	$(UV) sync --frozen

lock:
	$(UV) lock

download:
	$(RUN) download --issue $(ISSUE) --vintage $(VINTAGE)

clean:
	$(RUN) clean --issue $(ISSUE)

analyze:
	$(RUN) analyze --issue $(ISSUE)

figures:
	$(RUN) figures --issue $(ISSUE)

report:
	$(RUN) report --issue $(ISSUE)

all: setup download clean analyze figures report

test:
	$(UV) run pytest

archive:
	$(RUN) archive --issue $(ISSUE)
