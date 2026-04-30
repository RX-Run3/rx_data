[TOC]

# TLDR

To submit the jobs do:

```bash
# A virtual environment as shown below
micromamba activate post_ap

# This should allow access to shell with Ganga
# .ganga.py has to have the path to site-packages added
# to python path as shown below
post_shell

# Create proxy with 100 hours validity
lhcb-proxy-init -v 100:00

# Submit job "data_2024" with configuration in v1.yaml. The job name in dirac will be
# filter_001.
job_filter_ganga -n filter_001 -p rx_2024 -s data_2024 -c rk/v1.yaml -b Dirac -v 037
```

# Description

This project is used to:

- Filter, slim, trim the trees from a given AP production
- Rename branches

This is done using configurations in a YAML file and through Ganga jobs.

## Installation

You will need to install this project in a virtual environment provided by micromamba. 
For that, check [this](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
Once micromamba is installed in your system:

- Make sure that the `${HOME}/.local` directory does not exist. If a dependency
of `post_ap` is installed there, `ganga` would have to be pointed to that location and to
the location of the virtual environment. This is too complicated and should not be done.

- Create a new environment:

```bash
# python 3.11 is used by DIRAC and it's better to also use it here 
micromamba create -n post_ap python==3.12
micromamba activate post_ap
```

- In the `$HOME/.bashrc` export `POSTAP_PATH`, which will point to the place where your environment
is installed, e.g.:

```bash
export POSTAP_PATH=/home/acampove/micromamba/envs/post_ap/bin
```

which is needed to find the executables.

- Install `XROOTD` using:

```bash
micromamba install xrootd
```

which is needed to download the ntuples and is not a python project, therefore
it cannot be installed with `pip`.

- Install this project.

```bash
# can also be installed in editable mode
pip install post_ap
```

- In order to make Ganga aware of the `post_ap` package, in `$HOME/.ganga.py` add:

```python
import sys

# Or the proper place where the environment is installed in your system
sys.path.append('/home/acampove/micromamba/envs/post_ap/lib/python3.12/site-packages')
```

- This project is used from inside Ganga. To have access to Ganga do:

```bash
# Setup LHCb environment
. /cvmfs/lhcb.cern.ch/lib/LbEnv

# Make a proxy that lasts 100 hours
lhcb-proxy-init -v 100:00
```

- To check that this is working, open ganga and run:

```python
from post_ap.pfn_reader        import PFNReader
```

# Submitting jobs

## Environment

The script in the next setion needs a special environment to run. This environment is created by:

- Go to a virtual environment where this project is installed, could be named e.g. `post_ap`
- Run:

```bash
post_shell
```

- Make a grid token with:

```bash
lhcb-proxy-init -v 100:00
```

which will leave you in a new shell with the required environment variables

- Run the commands shown below

## Submission script

For this one would run a line like:

```bash
job_filter_ganga -n job_name -p PRODUCTION -s SAMPLE -c rk/v13.yaml -b BACKEND -v VERSION_OF_ENV 

# For example
job_filter_ganga -n flt_002 -p rx_2024 -s w37_39_v1r3788 -c rk/v13.yaml -b Dirac -v 037
```

- The number of jobs will be equal to the number of PFNs, up to 500 jobs.
- The code used to filter reside in the grid and the only thing the user has to do is to provide the latest version

The options that can be used are:

```bash
usage: job_filter_ganga [-h] -n NAME -p PROD -s SAMP -c CONF [-b {Interactive,Local,Dirac}] [-t] -v VENV [-d]

Script used to send ntuple filtering jobs to the Grid, through ganga

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Job name
  -p PROD, --prod PROD  Production
  -s SAMP, --samp SAMP  Sample
  -c CONF, --conf CONF  Relative path to config file 
  -b {Interactive,Local,Dirac}, --back {Interactive,Local,Dirac}
                        Backend
  -t, --test            Will run one job only if used
  -v VENV, --venv VENV  Version of virtual environment used to run filtering
  -d, --dry_run         If used, will not create and send job, only initialize
```

**RX jobs**: See [this](doc/rx_jobs.md).   
**LbpKmumu jobs**: See [this](doc/lbpkmm_jobs.md)

## Check latest version of virtual environment

The jobs below will run with code from a virtual environment that is already in the grid. One should use the
latest version of this environment. To know the latest versions, run:

```bash
# In a separate terminal open a shell with access to dirac
post_shell

# Run this command for a list of environmets
list_venvs
```

The `post_shell` terminal won't be used to send jobs.

## Config file

Here is where all the configuration goes and an example of a config can be found [here](https://github.com/acampove/config_files/blob/main/post_ap/v7.yaml).
One of the sections contains the list of MC samples, this can be updated by:

```bash
dump_samples -p rd_ap_2024 -g rd -v v1r2437 -a RK RKst
```

Which will dump a `yaml` file with the samples for the `rd_ap_2024` production in the `rd` group and in
version `v1r2437` used by the `RK` and `RKst` analyses.

## Validation

In order to validate the ntuples slimmed run:

```bash
validate_slimming -P rk -v v1 -p /path/to/directory/with/slimmed/ntuples 
```

to validate ntuples produced with `v1.yaml` config from the `rk` project.
This should check that:

- Every ntuple that was meant to be slimmed, was slimmed.
- Each ntuple that was meant to be slimmed produced the same number of ntuples.

## Optional

- In order to improve the ganga experience use: 

```bash
# Minimizes messages when opening ganga
# Does not start monitoring of jobs by default
alias ganga='ganga --quiet --no-mon'
```

in the `$HOME/.bashrc` file. Monitoring can be turned on by hand as explained [here](https://twiki.cern.ch/twiki/bin/viewauth/LHCb/FAQ/GangaLHCbFAQ#How_can_I_run_the_monitoring_loo)

# Make your own virtual environment

You can also:

- Modify this project
- Make a virtual environment and put it in a tarball
- Upload it to the grid and make your jobs use it.

For this export:

- **LXNAME**: Your username in LXPLUS, which should also be the one in the grid, 
used to know where in the grid the environment will go.
- **VENVS**: Path to the directory where the code will place all the tarballs holding the environments.
- **POSTAP_PATH**: Path to micromamba directory in which the environment where you are developing is located
e.g. `/home/acampove/micromamba/envs/run3/bin`. Here the name of the environment is `run3`.

Then do:

```bash
# This leaves you in a shell with the right environment
post_shell

# Create and upload the environment with version 030
update_tarball -v 030
```
## Utilities

For brevity, these utilities are documented separately, the utilities are:

- [dump_sample](doc/utilities/dump_samples.md) Used to search for existing and missing samples in a production

## Things that can go wrong

For brevity, each of these issues will be documented in a separate file,

[Missing ganga jobs](doc/missing_jobs.md)
If ganga has problems, the jobs might not appear, despite they did run.

