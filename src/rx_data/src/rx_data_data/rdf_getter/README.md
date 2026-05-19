# Description

These YAML files are used to:

- Define new branches that were missed in DaVinci or the slimming
- Redefine branches

The files are:

## common.yaml

With code used by all analyses

## rk.yaml and rkst.yaml

With config used by respective analyses.
These settings are reused by _inherited_ analyses, 
e.g. `rk` uses the same as `rk_nopid` or `rk_sim10d`

## blocks.json

Some of the MC samples for sim10g have the block number missing in the MCDecayTree
due to:

https://gitlab.cern.ch/lhcb-datapkg/AnalysisProductions/-/blob/10738c94bb68315e7f809f34961fc16be08d42d4/rx_filter/src/filter/filter_dataframe.py#L193

The values can, nevertheless be recovered, because the filtering job name used in the `rx_filter`
project was used to generate a hash, which is added to the name of each ROOT file. The correspondence
can be picked from `test_pfn_reader.py`, specifically `test_hash`.

This was done and the numbers are stored in this JSON file.

