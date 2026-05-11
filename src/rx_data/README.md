[TOC]

# $R_X$ data

> [!WARNING]
> For the instructions below to work, you need to use the `root` and `xrootd`
> versions from conda, due to [this](https://github.com/root-project/root/issues/20782) issue:
> i.e.
> ```bash
> pip uninstall root
> pip uninstall xrootd
> micromamba install root xrootd
> ```

This project is meant to:

- Download ntuples for a given AP
- Reorganize them into a directory structure
- Provide tools to access the data
- Provide tools to correct the data and add extra information

All the instructions below assume that there is a directory where the data will go.
The location of that directory needs to be exported as in:

```bash
export ANADIR=/home/user/rk
```

ideally in the `~/.bashrc` file. The user should have around 1TB of storage in the location where `ANADIR` lives.

## Downloading ntuples

For this:

- Setup the LHCb environment with:

```bash
. /cvmfs/lhcb.cern.ch/lib/LbEnv
```

- Create a grid proxy with `lhcb-proxy-init`
- Log into APD with `apd-login`

do:

```bash
rxdata download-ntuples -n 6 -v v1r5849
```

where the downloaded ntuples will come from version `v1r5849` and they will be
downloaded with 6 cores from the `rx_filter` project.

## Transferring ntuples from server

If the ntuples were downloaded to a local cluster and the user needs them in
their laptop one can use the following snakemake workflow:

```bash
snakemake -s snakemake/rules/ntuples/transfer.smk  --configfile snakemake/configs/ntuples/transfer.yaml -c 8
```

Which requires:

- `ANADIR` to also be defined in the laptop's environment
- The remote filesystem to be mounted through SSHFS
- The fields:
```
SERVER = 'ihep'
DATASET= 'from_ap'
```
in the `smk` file to be updated accordingly
- The `yaml` file to also be updated.

## Organizing the ntuples into a directory structure

The ntuples downloaded above will end up in the `downloads/` directory
and will contain files with a structure like:

```bash
rootls -r 00383232_00000001_1.sim10g_ss.root
FileSummaryRecord
Hlt2RD_B0ToKpPimEE_SameSign_MVA
  DecayTree
Hlt2RD_BuToKpEE_SameSign_MVA
  DecayTree
MCDT
  MCDecayTree
MCDT_HEADONLY
  MCDecayTree
```

But the files need to be:

- Merged by job if they are still split, i.e. one file per job.
- Split by project, i.e. placed in an `rk` and `rkst` 
  project with the corresponding trees properly located
- Renamed such that they follow the naming convention the code understands

For this do:

```bash
rxdata organize-paths -v v1r5849
```

which will produce files that will look like:

```bash
rxdata organize-paths -v v1r5849
```

> [!NOTE]
> The merging step will require writting large temporary files. 
> These will live in `/tmp/`. This can be overriden with:
> 
> ```bash
> export SCRATCH=/some/large/storage/device/
> ```
> In case `/tmp` has storage left. 

