[TOC]

For:

- Instructions on how to install this project, check [this](doc/installation.md)
- Instuctions on how to create a new production from `rd_ap_2024`, check [this](doc/new_production.md)
- Tools to deal with nicknames check [this](doc/nicknames.md)
- Instructions to mount EOS in your laptop check [this](doc/mounting_eos.md)
- Documentation specific to MVA lines of the RD group, check [this](doc/mva_lines.md)

# Objectives

This project is meant to:

- Check if MC samples exist in the bookkeeping, starting from an event type list. [Link](doc/find_mc.md)
- Out of the samples in bookkeeping, check which samples have not been ntupled. [Link](doc/ntupled_samples.md)
- Assuming you have a new production made as [here](doc/new_production.md), [this](doc/add_samples.md) shows how to add new MC decays.
- Checks for AP before and after ntupling jobs [here](doc/ntupling_checks.md)

# Utilities

## Listing ntupled samples

In order to list the samples ntupled and belonging to `rd_ap_2024` do:

```bash
list_ap_samples -v v1r3788 -p rd_ap_2024
```

where the version is associated to the AP MR. This is equivalent to:

```bash
apd-list-samples RD rd_ap_2024 --version v1r3788
```

but with a cleaner output.

## Accessing alternative shells

- A shell with access to Ganga through python can be created with:

```bash
ganga_shell
```

- If the user wants a shell with dirac (i.e. one can do `dirac-bookeeping...`), do:

```bash
dirac_shell
```

