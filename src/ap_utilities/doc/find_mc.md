# Finding MC 

The commands below need to be run inside a DIRAC shell.

Two files control the samples used in the analysis:

- `ap_utilities_data/analyses/by_priority.yaml`: Which defines the event types to be used in priority sections.
- `ap_utilities_data/samples/2024_sim10f.yaml`: Which defines the settings used for each block of 2024 data

## Updating `by_priority.yaml` with new event types

In order to add new samples to the analysis do:

- Open `src/ap_utilities_data/analyses/by_priority.yaml`
- Add the event type to the `all` section
- Run

```bash
analyze_samples -c by_priority
```

this should create: 

**summary.yaml**: which will show the samples not found already in
`by_priority.yaml`. Add the lines to the sections according to the priority.
Samples in `all` but not `priority` section     will go in `missing`   
Samples in `priority` section, but not in `all` will go in `new`.

**missing.yaml**: If the missing sections were filled with lists of event types, `missing.yaml`
will contain the mappings with the decay string.

## Check existing samples 

The samples to be ntupled go to `rx_2024/info.yaml`. To get the contents run:

```bash
# Enter environment with access to dirac
# need grid certificate first
dirac_shell
check_bkk_samples -c 2024_sim10g -s by_priority -n 6 -p sim10g -k block
```

which will check for their existence with:

- 6 threads (default is 1). 
- sim10g samples (can also be sim10f, sim10d)
- `sim10g` samples, i.e. the signal samples.
- Will print a table showing what is available for each block

check [this](src/ap_utilities_data/analyses/by_priority.yaml) for the full list
of analyses sorted by priority. The script will produce:

- `info_SECTION_NAME.yaml`: Where `SECTION_NAME` corresponds to each section above, i.e. `one`, `two`, `three`
- `validation_SECTION_NAME.yaml`: Which will be needed for validation later.

Once this has been done, the lines needed for the `info.yaml` can be obtained by concatenating the partial outputs with:
