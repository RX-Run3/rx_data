[TOC]

# Description

This project is used to filter ntuples produced by the AnalysisProduction.
The filtering is done also using the AnalysisProductions framework. 
The workflow is as follows:

- Make an MR
- Once the pipelines are gree request merging
- Once the jobs are done, download the filtered ntuples

In order to create the MR one needs an `info.yaml`. This file looks like:

```yaml
defaults:
  wg         : RD
  inform     : acampove 
  recipe:
    name       : filter-trees
    entrypoint : rx_filter.main:main
    extra_args:
      - '--max_entries=1000'

mc_24_w31_magup_sim10g_12123003_bu_kee_eq_btosllball05_dpc_filter:
  input :
    wg      : RD 
    analysis: rx_2024 
    tags:
      version : v1r5811 
      name    : mc_24_w31_magup_sim10g_12123003_bu_kee_eq_btosllball05_dpc_tuple
  output    : bu_kee_eq_btosllball05_dpc.root
...
```

With one job section per ntupling sample. 

# Making `info.yaml`

These file will most of the time contain more than 100 samples. Therefore the
following is used to make the corresponding sections:

```bash
post_ap make-info -p rx -g sim10g_unfiltered
```

where the first argument is needed to find:

```bash
src/post_ap/src/post_ap_data/filter/rx.yaml
```

and the second one is used to specify which samples to include. 
The config looks like:

```yaml
working_group: RD
productions:
  rx_2024:
    versions:
      # Here we map identifiers to a version of the AP jobs
      sim10g_unfiltered: v1r5754
      sim10g_filtered  : v1r5781 
    samples:
      # null will imply that all the samples are processed
      sim10g_unfiltered: null
      sim10g_filtered  :
        - mc_24_w31_magup_sim10g_12153001_bu_jpsik_ee_eq_dpc_filter
        - mc_24_w31_magup_sim10g_11144001_bd_jpsikst_mm_eq_dpc_filter
    fractions:
      # When a sample is too large, this will allow only a random subset to be processed
      mc_24_w31_magup_sim10g_11144001_bd_jpsikst_mm_eq_dpc_tuple      : 1.00 # Process the full sample
      mc_24_w32_34_magup_sim10g_11144001_bd_jpsikst_mm_eq_dpc_tuple   : 0.08 # Process only 8% 
      mc_24_w35_37_magup_sim10g_11144001_bd_jpsikst_mm_eq_dpc_tuple   : 0.08 
      mc_24_w37_39_magdown_sim10g_11144001_bd_jpsikst_mm_eq_dpc_tuple : 0.08 
      mc_24_w40_41_magdown_sim10g_11144001_bd_jpsikst_mm_eq_dpc_tuple : 0.08 
      mc_24_w41_42_magup_sim10g_11144001_bd_jpsikst_mm_eq_dpc_tuple   : 0.08 
```

# Testing locally

In order to test locally:

- Install the code as a package, using:

```toml
[build-system]
requires = ["setuptools>=42"]
build-backend = "setuptools.build_meta"

[project]
name = "rx_filter"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pytest",
    "pytest-xdist",
    "root",
    "pyyaml",
    "numba",
    "cffi",
    "pandas",
    "numpy",
    "awkward",
    "pydantic",
    "jinja2",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["rx_filter*"]

[tool.pytest.ini_options]
pythonpath = ["."]
```
which has to be placed in the `AnalysisProduction` directory and:

```bash
pip install -e .
```

from the same directory

- Download testing ntuples and update the paths in:

`AnalysisProductions/rx_filter/tests/test_filter_dataframe.py`

- Run pytest on that file and the config test.
