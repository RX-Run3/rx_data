![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)

# $$R_X \text{ With Run 3 Data}$$

This is the repository for the combined measurement of $R_K$ and $R_{K^*}$
in run 3.

Find in the following links:

- [Installation instructions](doc/installation.md)

## Analysis packages

This project contains the following packages:

| Project         | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| [post_ap](src/post_ap/README.md)                 | Contains code needed to slim ntuples made by the analysis productions   | 
| [fitter](src/fitter/README.md)                   | Has code needed to run fits to rare and resonant channel                |
| [hqm](src/hqm/README.md)                         | Used to get the charmonium template for the high-q2 bin                 |
| [rx_classifier](src/rx_classifier/README.md)     | Used to train classifiers                                               |
| [rx_data](src/rx_data/README.md)                 | Allows access to the data and also has tools for further processing     |
| [rx_efficiencies](src/rx_efficiencies/README.md) | Used to calculate geometric acceptances and reconstruction efficiencies |
| [rx_misid](src/rx_misid/README.md)               | Has utilities to work with hadronic mis-ID backgrounds |
| [rx_pid](src/rx_pid/README.md)                   | Has utilities to make PID maps through PIDCalib2 |
| [rx_plots](src/rx_plots/README.md)               | Has code needed to make plots | 
| [rx_q2](src/rx_q2/README.md)                     | Has code needed to study mass scales and resolutions| 
| [rx_selection](src/rx_selection/README.md)       | Has code needed apply selection | 

## Development packages

In order to make developing the code easier it is advised to use type anotations
with an LSP server, e.g. ruff and pyright. These server won't work unless the upstream
projects have also type annotations. That is not the case often, but annotations can
be added through stub packages. This project includes, zfit-stubs, vector-stubs 
and root_stubs.

## CI/CD

This project is meant to allow for:

- **Continuous Integration:** I.e. we will make it easy to build and test the project on each commit to find bugs
as soon as they are introduced.

- **Continuous Delivery:** I.e. we will recalculate everything all the way up to blinded versions of $R_K$ and $R_{K^*}$
within a day, to check stability of results and get insights on how to improve the analysis.

More details on this can be found [here](doc/ci_cd.md)

## Workflows

To automate the execution of the code this project uses snakemake workflows. Some workflows using
[LAW](https://github.com/riga/law) are also available in `rx_orchestration` but these should be moved
to snakemake eventually. The workflows reside in the `snakemake` directory alongside the config files.
A typical run of these workflows would look like:

```bash
snakemake -s snakemake/rules/ntuples/friends.smk --configfile snakemake/configs/ntuples/friends.yaml -c 6
```

which would:

- Run the worklow in the smk file
- Use the yaml file for configuration
- Use six cores

For further instructions check [workflows](doc/workflows.md)
