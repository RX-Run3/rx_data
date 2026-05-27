# Checks 

## Before pipelines 

There are four files relevant to the production:

### tupling/config/samples_turbo_lines_mapping.yaml

This is where the sample $\to$ HLT line category is specified. I.e. each sample
will be processed under a certain group of lines, `rx_muon` lines, `rx_electron` lines etc.

### tupling/config/mcfuntuple.yaml

This is where the decay destriptors used for the `MCDecayTree` building are specified

### info.yaml 

This is where the samples that are made into ntuples will be specified.

### Reference event types

Which are stored in this project, in:

```bash
ap_utilities/src/ap_utilities_data/analyses/analyses.yaml
```

and which describes, for each analysis (currently `rk` and `rx`), what event types should be used.

One needs to make sure that samples that will be made: 
- Have a descriptor for the `MCDecayTree`.
- Are in the reference `analyses.yaml` file

Etc

In order to do these checks run:

```bash
check_production -p /home/acampove/Packages/AnalysisProductions/rd_ap_2024 -a rx
```

This script will produce `report.yaml`, which looks like:

```yaml
# Print nicknames of samples going above 100 characters
long_nicknames: ['105', 'some_long_sample_name']
missing:
  info_mcfuntuple:
    only info:        # Samples specified for production, but without MCDecayTree
      - ...
    only mcfuntuple:  # Samples with MCDecayTree but not been made
      - ...
  info_rx:
    only info:        # Samples been made, but not in the reference file
      - ...
    only rx:          # Samples in the reference file but not been made
      - ...
  info_samples:
    only info:        # Samples been made, but without trigger association (DANGER: this wil break the pipeline)
      - ...
    only samples:     # Samples with trigger association and not been ntupled
      - ...
  mcfuntuple_samples:
    only mcfuntuple:  # Samples with MCDecayTree but not been ntupled
      - ...
    only samples:     # Samples with HLT trigger association but no MCDecayTree.
      - ...
```

## After pipelines

In order to validate the new production run:

```bash
validate_ap_tuples -o /path/to/old/file.root -n /path/to/new/file.root -e Hlt1 _fix_
```

which will compare a file produced from an old production to a new one, from the pipeline.
The validation will:

- Check which trees were present before and are missing now and vicevesa.
They will appear in a section like:

```yaml
Directories:
  Hlt2RD_B0ToKpPimMuE_MVA:
    new: true
    old: false
  Hlt2RD_BsToPhiMuE_MVA:
    new: true
    old: false
```

which would mean that now we have a `MuE` tree that we did not before.

- Check, for each trigger, which branches are present now that were not present before
and viceversa, giving a section like:

```yaml
Trees:
  Hlt2RD_B0ToKpPimEE_MVA:
    new:
      - B_DOWNSTREAM_TRACK_ISOLATION_eminus_MULT
      - B_DOWNSTREAM_TRACK_ISOLATION_eplus_MULT
      - B_DTF_CTAU
      - B_DTF_CTAUERR
    old:
      - B_ALV
      - B_ALV12
      - B_DOCA12
```

- Exclude from these lists branches containing the substring `Hlt1` or `_fix_`
