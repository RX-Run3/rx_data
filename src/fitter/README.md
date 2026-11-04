[TOC]

# Fitter

This project is meant to automate:

- Building of models
- Fits to MC 
- Fits to data
- Creation of validation plots, tables, etc
- Application of constraints
- Obtention of fitting information, specially:
    - Mass scales, resolutions
    - Signal yields for resonant and rare modes

And be used as an input for:

- Systematics evaluation
- Extraction of $R_K$ and $R_K^*$
- Calibrations

Ideally with minimal changes for new observables.
The class is organized as in the diagram below:

![project diagram](./doc/images/fitter.png)

This project makes heavy use of caching through the [Cache](https://github.com/acampove/dmu?tab=readme-ov-file#caching-with-a-base-class)
class and thus:

- It allows for fast reruns
- It allows for the fitters to also be used to retrieve parameters

## Usage

For fits to data do:

```bash
fit_rx_reso -c rare/electron -q central -C 0.5 -P 0.5
```

to use the configuration in `src/fitter_data/rare/electron/data.yaml`
with an MVA working point of `0.5` for the combinatorial and part reco BDTs.

The script:

- Builds a likelihood for the data fit. Which requires fits to the simulation
  in order to pick up the components, which implies:
    - Apply the selection on the MC and data
    - Fit the MC
    - Use the MC to create components for the fit to the data
- Extracts constraints. Which in the case above constraint the misID yields
and the ratio of rare part reco background to signal.
- Minimizes the negative log-likelihood.

```python
from dmu.generic import utilities as gut
from dmu.stats   import zfit
from dmu.stats   import ConstraintAdder

from fitter      import DataFitter
from fitter      import LikelihoodFactory

fit_cfg = gut.load_conf(package='fitter_data', fpath='rare/electron/data.yaml')

# The observable should correspond to the branch name
# For resonant mode we have:
#
# - B_const_mass_M
# - B_const_mass_psi2S_M
#
# For the muon rare mode B_M is good enough
obs = zfit.Space('B_Mass_smr', limits=(4600, 7000))
ftr = LikelihoodFactory(
    obs    = obs,
    q2bin  = 'central',
    sample = 'DATA_24_*',
    trigger= 'Hlt2RD_BuToKpEE_MVA',
    project= 'rx',
    cfg    = fit_cfg)
nll = ftr.run()
cfg = ftr.get_config()

cfg_cns = _get_constraints()

cad = ConstraintAdder(nll=nll, cns=cfg_cns)
nll = cad.get_nll()

ftr = DataFitter(
    name = 'data_fit',
    d_nll= {'' : (nll, cfg)},  # If doing simultaneous fits, this dictionary
    cfg  = fit_cfg)            # will hold each signal region
obj = ftr.run()
```

where `obj` is a `DictConf` (from the `omegaconf` project) dictionary where the
parameters and errors can be accessed as:

```python
val = obj['name']['value']
err = obj['name']['error']
```

### Constraints

The constraints are given by a configuration like the one below:

```yaml
signal_shape:
  kind        : GaussianConstraint 
  parameters  :
    - mu
    - sg
  observation : 
    - 5200
    - 50
  cov: 
    - [100, 10]
    - [ 10,  4]
yields:
  kind        : PoissonConstraint
  parameters  :
    - nsig 
    - nbkg 
  observation : 
    - 1000 
    - 1000 
```

where the are multiple sections, each of them specifying the kind of constraint, the
parameters to which these constraints are applied and the values of the parameters.

The constraints can be written to a YAML file or written in a python dictionary.
These then need to be made into a `DictConfig` with:

```python
from omegaconf import OmegaConf

cfg = OmegaConf.create(config)
```

before passing it to the `ConstraintAdder`, which will attach the constraints
to the likelihood.

### Summarize fits

To collect the fit parameters do:

```python
from fitter import FitSummary

smr = FitSummary(name='mid_window')
df  = smr.get_df(force_update = False) # By default False, will cache
```

which will:

- Look for all the `mid_window` fits and collect the parameters from
the JSON files.
- Use them to build a pandas dataframe and return it.
- The dataframe will be cached in the fits directory as a parquet file.
  Run with `force_update=True` to remake it.

### Access parameters

The result of this will be a large table, this table can be accessed with:

```python
from fitter    import ParameterReader
from rx_common import Project
from rx_common import Trigger 
from rx_common import Qsq 

rdr = ParameterReader(name = 'mid_window')
ms  = rdr(
    brem     = 1, 
    block    = 3, 
    is_mc    = True, # or False
    cmb      = MVAWp.from_str('0.99'),
    prc      = MVAWp.from_str('0.60'),
    trigger  = Trigger.rk_ee_os, 
    q2bin    = Qsq.jpsi)
```

If one has access to the parquet file with the parameters, one can do:

```python
from fitter    import ParameterReader
from rx_common import Project
from rx_common import Trigger 
from rx_common import Qsq 

with ParameterReader.inputs_from(pars_path = '/path/to/parameters.parquet'):
    rdr = ParameterReader()
    ms  = rdr(
        brem     = 1, 
        block    = 3, 
        is_mc    = True, # or False
        cmb      = MVAWp.from_str('0.99'),
        prc      = MVAWp.from_str('0.60'),
        trigger  = Trigger.rk_ee_os, 
        q2bin    = Qsq.jpsi)
```

where `ms` is a `Measurement` object that can be read with:

```python
# Retrieve yield for resonant fit component
value, error = ms['yld_jpsi']

# Print contents
print(ms)
```

## Signal expectation

In order to optimize the MVA working point one needs the signal and background yields.
The signal can be obtained through the yield in resonant mode, the efficiencies and the branching
fractions through:

$$
N_{\text{sig}}(B^+\to K^+ e^+e^-) = N_{\text{reso}}(B^+\to K^+ J/\psi(\to e^+e^-)) \times \frac{\varepsilon(B^+\to K^+ e^+e^-)}{\varepsilon(B^+\to K^+ J/\psi(\to e^+e^-))} \times \frac{\mathcal{B}(B^+\to K^+ e^+e^-)}{\mathcal{B}(B^+\to K^+ J/\psi)\,\mathcal{B}(J/\psi\to e^+e^-)}
$$

run:

```bash
rxfitter signal-expectation -n rare -c 0.99 -p 0.6 -t rk_ee_os -q central
```

which will:

- Use the config in `rare.yaml`, which specifies the spacing in the MVA plane among other things
- Pick the resonant mode fit at a combinatorial working point above 0.99 and a part reco working point above 0.6.
  The corresponding resonant mode efficiencies will also be calculated at this point.
- Pick the resonant fits and simulation for the $R_K$ analysis in the electron channel to calculate the efficiencies
- Calculate the efficiencies for the rare mode in the `central` $q^2$ bin.

## Simultaneous fits

For this run:

```bash
fit_rx_rare_sim -b -1 -g test -k rk -q low -C 0900 -P 0600 -s nominal
```
Which will do the muon and electron channel fits needed to extract $R_K$. For $R_{K^*}$ run with
`-k rkst` and for the full fit with both extracted simultaneously do `-k rx`.

In order to switch the $q^2$ bin definition use the `-Q` flag, by default it will use the
nominal definition, but it can be switched to `constrained`, `track` for the DTF version and the
track based version.

The fits will parametrize:

- **$R_K$**: The muon signal yield is parametrized as a function of the electron signal yield and $R_K$:
  $$
  N(B^+\to K^+\mu^+\mu^-) = N(B^+\to K^+e^+e^-) \times R_K
  $$
- **$R_{K^*}$**: Similarly, for the $K^*0$ modes:
  $$
  N(B^0\to K^{*0}\mu^+\mu^-) = N(B^0\to K^{*0}e^+e^-) \times R_{K^*}
  $$
- **Part-reconstructed backgrounds**: Linked between channels using efficiency ratios and scaling factors (e.g., $B^0 \to K^{*0}\mu^+\mu^-$ relative to $B^0 \to K^{*0}e^+e^-$ and $B^+ \to K^+ e^+e^-$ cross-feed components).
- **Categorization**: Handled across different bremsstrahlung categories (`x12`, `xx1`, `xx2`) and MVA working points.

## Systematic variations

For this vary the `-s` argument, as in:

```bash
fit_rx_rare_sim -b -1 -g test -k rk -q low -C 0900 -P 0600 -s rk_mm_sig 
```

which will switch the signal model based on the contents of `fitter/systematics/model.yaml`
