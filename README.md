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
hqm build-database -t rkst_mm_os -c bdkstkpipsi2mm
hqm build-database -t rkst_ee_os -c bdkstkpipsi2ee

hqm build-database -t rkst_mm_os -c bdkstkpijpsimm
hqm build-database -t rkst_ee_os -c bdkstkpijpsiee

hqm build-database -t rkst_mm_os -c data_24
hqm build-database -t rkst_ee_os -c data_24

hqm build-database -t rk_mm_os   -c bpkpjpsimm
hqm build-database -t rk_ee_os   -c bpkpjpsiee

hqm build-database -t rk_mm_os   -c bpkppsi2mm
hqm build-database -t rk_ee_os   -c bpkppsi2ee

hqm build-database -t rk_mm_os   -c data_24
hqm build-database -t rk_ee_os   -c data_24
```

for different processes and triggers

## Fit simulation

With the data above already made run:

```bash
pairs=(
  "bpkpjpsiee     rk_ee_os"
  "bpkppsi2ee     rk_ee_os"
  "bpkpjpsimm     rk_mm_os"
  "bpkppsi2mm     rk_mm_os"
  "bdkstkpijpsiee rkst_ee_os"
  "bdkstkpipsi2ee rkst_ee_os"
  "bdkstkpijpsimm rkst_mm_os"
  "bdkstkpipsi2mm rkst_mm_os"
)

for pair in "${pairs[@]}"; do
  read -r component trigger <<< "$pair"
  for q2bin in jpsi psi2 high; do
    hqm fit-mc -c "$component" -t "$trigger" -q "$q2bin" -d -b "block-1 mva_cmb-7 mva_prc-7"
    hqm fit-mc -c "$component" -t "$trigger" -q "$q2bin" -k -b "block-1 mva_cmb-7 mva_prc-7"
    hqm fit-mc -c "$component" -t "$trigger" -q "$q2bin"    -b "block-1 mva_cmb-7 mva_prc-7"
  done
done
```

where:

- `-d` requires the `q2` cut to be on the DTF variable.
- `-k` requires a KDE fit and without it will try a parametric fit
- `-b` specifies the binning by using the variable and the bin index

The binning is specified in `hqm_data/config/binning.yaml`.

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

## Make part reco PDFs

With the transfer functions and the data in the low sideband in the muon mode
one can calculate the expected partially reconstructed electron charmonium shapes with:

```bash
hqm make-prec -T rk_ee_os   -s jpsi -t jpsi -b 5
hqm make-prec -T rk_ee_os   -s jpsi -t psi2 -b 5
hqm make-prec -T rk_ee_os   -s jpsi -t high -b 5

hqm make-prec -T rk_ee_os   -s psi2 -t jpsi -b 5
hqm make-prec -T rk_ee_os   -s psi2 -t psi2 -b 5
hqm make-prec -T rk_ee_os   -s psi2 -t high -b 5

hqm make-prec -T rkst_ee_os -s jpsi -t jpsi -b 5
hqm make-prec -T rkst_ee_os -s jpsi -t psi2 -b 5
hqm make-prec -T rkst_ee_os -s jpsi -t high -b 5

hqm make-prec -T rkst_ee_os -s psi2 -t jpsi -b 5
hqm make-prec -T rkst_ee_os -s psi2 -t psi2 -b 5
hqm make-prec -T rkst_ee_os -s psi2 -t high -b 5
```

For e.g. block 5.
