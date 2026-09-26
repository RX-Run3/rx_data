[TOC]

# $R_X$ data

## Loading dataframes

- Copy the directory structure present in EOS at `/eos/lhcb/wg/RD/RX_run3`
to a local file system
- Export a variable with the location of the files, i.e.

```bash
export ANADIR=/path/to/directory/with/Data
```

in EOS it would be

```bash
export ANADIR=/eos/lhcb/wg/RD/RX_run3
```

- Install this project in a separate mamba environment:

```bash
git clone ssh://git@gitlab.cern.ch:7999/LHCb-RD/cal-rx-run3.git
cd cal-rx-run3
# Install the dependencies
pip install -r requirements-dep.txt

# Install the analysis packages
pip install -r requirements-ana.txt
```

- In a python script one should be able to do:

```python
from rx_data    import RDFGetter
from rx_common  import Trigger
from rx_common  import Component 

component = Component.bpkpee
trigger   = Trigger.rk_ee_os

gtr = RDFGetter(sample=component, trigger=trigger)
rdf = gtr.get_rdf(per_file=False)
```

would provide a ROOT dataframe with the data associated to the respective
sample under the given trigger.

To list all the components and triggers do in an interactive python session:

```python
from rx_common  import Trigger
from rx_common  import Component 

for val in Trigger:
    print(val)

for val in Component:
    print(val)
```

check the tests at `src/rx_data/tests` for more examples and more functionality

## Adding missing block branch in MCDecayTree

This branch can be added back based on the hash
that is part of the file name. For this run:

```bash
rxdata patch-files -p rkst -v v1
rxdata patch-files -p rk   -v v1
```

where `v1` is the version of the main trees. However this is not needed if one won't use `MCDecayTree`

## Database creation

Using `RDFGetter` on the filtered ntuples can cause the code to be slow. A further filtering step can
be applied where:

- Most of the selection is applied, except for a few cuts
- Most of the branches are dropped

The branches kept are listed in `rx_data_data/databases/*.yaml`. These files can be made by running:

```bash
snakemake -s snakemake/rules/fits/make_databases.smk --profile ihep --logger=flowo \
          --logger-flowo-name=database --keep-going --quiet \
          --configfile snakemake/configs/fits/database.yaml
```

and the outputs will go to `{ANADIR}/DB/fitter/{COMPONENT}/{TRIGGER}/data.root`.
The config file and snakefile can be changed for different usecases.
