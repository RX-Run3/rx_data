# HQM2

In the root directory do:

```bash
pip install .
```

This project is meant to:

- Provide templates for $c\bar{c}$ contributions to high-q2 $R_X$ signal region
- Validate method used to get those contributions

# CLI

All the CLIs for this projects can be accessed through `hqm`. For for information on them
check `hqm -h`.

The workflow proceeds as:

- Make databases, i.e. small parquet files with only needed data from ROOT files.
- Fit MC samples.
- Run fits to calculate transfer functions
- Fit the low sideband in the muon channel to get part reco template
- Get part-reco over fully-reco ratios from simultaneous fits
- Use part reco, ratios and fully reco components to build model

This full process can be steered by a snakemake workflow by running:

```bash
snakemake -s snakemake/rules/hqm/make_templates.smk --profile ihep --logger=flowo --logger-flowo-name=hqm --keep-going --quiet
```

# Accessing model

The model can be obtained with:

```python

from hqm           import ccbar_pdf
from dmu.generic   import Mode

obs     = zfit.Space('B_Mass', limits = (4600, 6500))
binning = 'block-3 mva_cmb-3'
project = Project.rk

ccb = CCbarPDFMaker(
    binning = binning,
    project = project)

model= ccb.get_pdf(obs = obs, mode = Mode.read)
pdf  = mode.pdf
```

Which will provide a PDF ready to be inserted in the full model.
