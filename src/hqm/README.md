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

```bash
nu run_databases.nu
```

for different processes and triggers

## Fit simulation

With the data above already made run:

```bash
nu run_fits.nu
```

where inside the script:

- `-d` requires the `q2` cut to be on the DTF variable.
- `-k` requires a KDE fit and without it will try a parametric fit
- `-b` specifies the binning by using the variable and the bin index
- `-s` performs smearing of the masses before running the selection

The binning is specified in `hqm_data/config/binning.yaml`.

## Make transfer functions

After building the databases and fitting the shapes, the transfer functios are made with:

```bash
nu run_trfc.nu
```


which will do the fits for all blocks and a given binning

## Make part reco PDFs

With the transfer functions and the data in the low sideband in the muon mode
one can calculate the expected partially reconstructed electron charmonium shapes with:

```bash
nu run_prec.nu
```

## Calculate ratios

In order to calculate the part reco over fully reconstructed yields run

```bash
nu run_ratios.nu
```

this will run simultaneous fit and store the parameters in a JSON file.

## Create $c\bar{c}$ templates

The script below:

```bash
nu run_ccbar.nu 
```

will:

- Put together fully and partially reconstructed templates with the ratio mentioned above
- Save model to JSON

