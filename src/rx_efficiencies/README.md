[TOC]

# $R_X$ efficiencies

Project used to calculate efficiencies for different simulated datasets. 
This project assumes (as all the others in the RX group) that an `ANADIR` variable is set and points to a directory
where the outputs can be written.

## Geometric acceptance

This work was done for Run1/2 datasets by [prec_acceptances](https://gitlab.cern.ch/r_k/prec_acceptances/-/tree/master?ref_type=heads)
and that code has been transferred and upgraded in this project.

### Making ntuples

The geometric acceptance should be calculated using [rapidsim](https://github.com/gcowan/RapidSim)
given that:

1. Accessing the generator tables is not trivial.
1. Using RapidSim is trivial.
1. One might need special definitions for the acceptance and having the ntuples with the
decay product values offers higher flexibility.

To install rapidsim do inside a micromamba environment:

```bash
micromamba install rapidsim
```

To create the ntuples with the decays, do:

```bash
create_rapidsim_ntuples -n 100000 -v v2
```

where the utility will pick up every decay configuration in the `rx_efficiencies_data/prec_decfiles/v2` directory and 

- Create the respective ntuple with the logfile and some histogram file and with 100K entries.
- Make the output path if not found and send the outputs there.

The output in this case would go to:

```bash
$ANADIR/Rapidsim/v2/DECAYNAME/ENERGY/
```

### Measuring acceptances from them

This can be done with the `AcceptanceCalculator` class as shown below:

```python
from rx_efficiencies.acceptance_calculator import AcceptanceCalculator

obj=AcceptanceCalculator(rdf=rdf)
obj.plot_dir     = '/optional/path/where/diagnostic/plots/are/saved'
acc_phy, acc_lhc = obj.get_acceptances()
```

where `acc_phy` is the physical acceptance and `acc_lhc` is the LHC one:

`Physical Acceptance`: The probability that the detector will see the reconstructed candidate. E.g. for $B_s\to\phi(\to KK)ee$ decays reconstructed as
$B^+\to K^+ee$, the decay counts as in acceptance, even if $K^-$ is not in acceptance.
`LHC acceptance`: What the _generator tables_ provide. All the decay products have to be in the acceptance.

These acceptances can be calculated all at once with:

```bash
calculate_acceptances -v v1 -p rk # or rkst
```

which will make the `JSON`, `TEX` and `PNG` files with the acceptances, the tables for the note/paper and the plots.

### Reading acceptances

This is done with the `AcceptanceReader` class with:

```python
from rx_efficiencies.acceptance_reader import AcceptanceReader

obj=AcceptanceReader(year=year, proc=process)
acc=obj.read()
```

## Acceptance, Reconstruction and selection efficiencies

The product of these efficiencies can be obtained by dividing:

**Numerator:** The number of entries in the `DecayTree` after the full selection   
**Denominator:** The number of entries in the `MCDecayTree` from the same files.

And multiplying the ratio by the acceptance from RapidSim. This is done by running:

```python
from rx_efficiencies.efficiency_calculator import EfficiencyCalculator

# q2 bin in low, central, high
obj         = EfficiencyCalculator(q2bin='central')
# The plots in this directory show the product of reconstruction and selection efficiencies.
# The YAML files include also the acceptances.
obj.out_dir = '/path/to/validation/directory'
eff, err    = obj.get_efficiency(sample='bpkpee')
```

which provides the efficiency value and the error from **unweighted** simulation.

## Scanning of efficiencies

The efficiencies can be scanned in a grid with:

```python
from rx_efficiencies.efficiency_scanner import EfficiencyScanner

l_wp = [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70,
        0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84, 0.86, 0.88, 0.90, 0.92,
        0.94, 0.96, 0.98]

cfg  = {
        'input' :
        {
            'sample' : sample,
            'trigger': 'Hlt2RD_BuToKpEE_MVA',
            'q2bin'  : q2bin,
            },
        'variables' :
        {
            'mva_cmb' : l_wp,
            'mva_prc' : l_wp,
            }
        }

obj = EfficiencyScanner(cfg=cfg)
df  = obj.run()
```

this would return a dataframe with columns `mva_cmb`, `mva_prc` 
and `eff`, the last of which is the efficiency.

