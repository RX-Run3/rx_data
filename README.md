# HQM2

In the root directory do:

```bash
pip install .
```

This project is meant to:

- Provide templates for $c\bar{c}$ contributions to high-q2 $R_X$ signal region
- Validate method used to get those contributions

# CLI

## Make databases

In order to speed up fits, etc, a database with parquet files, each containing
a pandas dataframe with only a few columns (masses, MVA scores, etc) is created
with:

```
hqm -t rkst_mm_os -c bdkstkpipsi2mm
hqm -t rkst_ee_os -c bdkstkpipsi2ee

hqm -t rkst_mm_os -c bdkstkpijpsimm
hqm -t rkst_ee_os -c bdkstkpijpsiee

hqm -t rkst_mm_os -c data_24
hqm -t rkst_ee_os -c data_24

hqm -t rk_mm_os   -c bpkpjpsimm
hqm -t rk_ee_os   -c bpkpjpsiee

hqm -t rk_mm_os   -c bpkppsi2mm
hqm -t rk_ee_os   -c bpkppsi2ee

hqm -t rk_mm_os   -c data_24
hqm -t rk_ee_os   -c data_24
```

for different processes and triggers

## Make transfer functions

After building the databases and fitting the shapes, the transfer functios are made with:

```bash
hqm make-trfc -b 1 -p rk   -s jpsi -t jpsi
hqm make-trfc -b 1 -p rk   -s jpsi -t psi2
hqm make-trfc -b 1 -p rk   -s psi2 -t jpsi
hqm make-trfc -b 1 -p rk   -s psi2 -t psi2
hqm make-trfc -b 1 -p rk   -s psi2 -t high
hqm make-trfc -b 1 -p rk   -s jpsi -t high

hqm make-trfc -b 1 -p rkst -s jpsi -t jpsi
hqm make-trfc -b 1 -p rkst -s jpsi -t psi2
hqm make-trfc -b 1 -p rkst -s psi2 -t jpsi
hqm make-trfc -b 1 -p rkst -s psi2 -t psi2
hqm make-trfc -b 1 -p rkst -s psi2 -t high
hqm make-trfc -b 1 -p rkst -s jpsi -t high
```

For block `1` and for each of the other 7 blocks.

