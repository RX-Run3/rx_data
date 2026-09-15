# AGENTS.md

## Project Overview
This project is meant to:

- Transform ROOT ntuples into small parquet files with needed columns and
after preselection.
- Load data from the muon channel
- Load simulation from the muon and electron channel
- Calculate transfer functions allowing us to move from muon to electron channel
- Apply them to low sideband data in muon channel, which represent part reco components.
- Use these expectation of the part-reco in the electron channel to setup fits to measure
the ratio of part-reco over fully-reco decays.
- Use those ratios to build templates for models describing the charmonium contamination in the
high-q2 bin in the electron channel.

## Structure
- `src/hqm/` — core library: binning, PDFs, fits, ratios, transfer functions
- `src/hqm/cli/` — CLI entry points for building databases, fitting, plotting
- `src/hqm_data/config/` — YAML configuration files
- `tests/` — test suite (pytest)
- `run_*.nu` — nushell scripts to run various pipelines

## Conventions
- Python, type-checked with pyright, linted with ruff
- (any naming conventions, docstring style, etc.)

## Common Commands
- Run tests: `pytest`
- Lint: `ruff check .`
- Type check: `pyright`
