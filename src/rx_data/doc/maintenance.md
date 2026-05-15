[TOC]

## List LFNs

Do:

```bash
list_lfns -v v1 v2 v3 -p rx
```

To create `lfns.txt` with a list of LFNs corresponding to the versions
shown above for the `rx` project. To check the amount of data in those files
do:

```bash
dirac-dms-data-size -u MB lfns.txt
```

This list can later be used to remove old files from the grid with:

```bash
dirac-dms-remove-files lfns.txt
```

## Listing available triggers

In order to see what triggers are present in the current version of the ntuples do:

```bash
list_triggers -v v1 -k rx

# And this will save them to a yaml file
list_triggers -v v1 -k rx -o triggers.yaml
```

## Downloading the ntuples

For this, run:

```bash
download_rx_data -m 5 -v v1 -d -t triggers.yaml -k rx
```

which will use 5 threads to download the ntuples associated to the triggers in `triggers.yaml`
and version `v1` to the specified path.

The full options are:

```
options:
  -h, --help              show this help message and exit
  -t TRIG, --trig TRIG    Path to YAML file with list of triggers
  -v VERS, --vers VERS    Version of LFNs
  -k KIND, --kind KIND    Type of production
  -n NFILE, --nfile NFILE Number of files to download
  -l {10,20,30,40}, --log {10,20,30,40} Log level, default 20
  -m MTH, --mth MTH       Number of threads to use for downloading, default 1
  -r, --ran               When picking a subset of files, with -n, pick them randomly
  -d, --dryr              If used, it will skip downloads, but do everything else
  -f, --force             If used, it will download even if output already exists
```

**IMPORTANT**:
- In order to prevent deleting the data, save it in a hiden folder, e.g. one starting with a period. Above it is `.data`.
- This path is optional, one can export `DOWNLOAD_NTUPPATH` and the path will be picked up

**Potential problems**:
The download happens through XROOTD, which will try to pick a kerberos token. If authentication problems happen, do:

```bash
which kinit
```

and make sure that your kinit does not come from a virtual environment but it is the one in the LHCb stack or the native one.

## Checking for corrupted files

For this run:

```bash
check_corrupted -p /path/to/directory/with/files -x "data_*_MVA_*.root"
```

Which will check for corrupted files and will remove them.
`-x` can be used to pass wildcards, in the case above, it would target only data.
After removal, the download can be tried again, which would run only on the missing samples.
This might allow for these files to be fixed, assuming that they were broken due to network issues. 

## Organizing paths

### Merging data files

After the preselection the data files are very small and there are many of them. The following line can be used to merge them:

```bash
merge_samples -p rx -s DATA_24_MagDown_24c3 -t Hlt2RD_BuToKpMuMu_MVA    -v v7
merge_samples -p rx -s DATA_24_MagDown_24c2 -t Hlt2RD_B0ToKpPimMuMu_MVA -v v7
```

where the command will merge all the files associated to a given sample and trigger.

## Samples naming

The samples were named after the DecFiles names for the samples and:

- Replacing certain special charactes as shown [here](https://github.com/acampove/ap_utilities/blob/main/src/ap_utilities/decays/utilities.py#L24)
- Adding a `_SS` suffix for split sim samples. I.e. samples where the photon converts into an electron pair.

A useful guide showing the correspondence between event type and name is [here](https://github.com/acampove/ap_utilities/blob/main/src/ap_utilities_data/evt_form.yaml)

## Printing information on samples

Use:

```bash
check_sample_stats -p /path/to/rx_samples.yaml
```

to print a table to markdown with the sizes of each sample in Megabytes. e.g.:

```markdown
| Sample                                      | Trigger                        |   Size |
|:--------------------------------------------|:-------------------------------|-------:|
| Bu_JpsiK_mm_eq_DPC                          | Hlt2RD_BuToKpMuMu_MVA          |  15829 |     ■■■■ 'BuToKpMuMu': Possible spelling mistake found.
| Bs_Jpsiphi_mm_eq_CPV_update2016_DPC         | Hlt2RD_BuToKpMuMu_MVA          |  11164 |     ■■■■ 'BuToKpMuMu': Possible spelling mistake found.
| Bd_JpsiKst_mm_eq_DPC                        | Hlt2RD_BuToKpMuMu_MVA          |   9945 |     ■■■■ 'BuToKpMuMu': Possible spelling mistake found.
| Bu_JpsiK_ee_eq_DPC                          | Hlt2RD_BuToKpEE_MVA_cal        |   8873 |     ■■■■■ 'BuToKpEE': Possible spelling mistake found.
| Bu_JpsiK_ee_eq_DPC                          | Hlt2RD_BuToKpEE_MVA            |   8488 |
...
```

## Copying files

If the original files are downloaded to a cluster and the user needs the files in e.g. a laptop one could:

- Use SSHFS to mount the cluster's file system in the laptop.
- Copy the files through

```bash
copy_samples -k all -c rk
```

where:

`-k` Kind of files to be copied, i.e. friend tree like `mva`, `main`, `hop` etc. For everything use `all`.   
`-c` Name of config specifying what to copy, e.g. `rk`, `rkst`. This is also the project directory.
`-s` Optional, name of friend tree to skip, e.g. `mva`
`-v` Version of files to download. By default it should get the latest. This should be used only if `k` is not `all`
     given that different types of friend trees will have different versions.

The config files live in `src/rx_data_data/copy_files` and can be adapted for new samples or different source paths.
If the files to be copied already exist locally, it will check that the sizes are the same, if not, it will remove the
local file and copy again.


## Calculating extra branches

Given the files produced by `post_ap`, new branches can be attached. These branches can be calculated using
`branch_calculator` and can be placed in small files. These latter files would be made into friends of the main files.

In order to do this we assume that all the ntuples live in `$DATADIR/main/vx`, where `DATADIR` needs to be exported
such that the code will pick it up. `vx` represents a version of the ntuples (e.g. `v1`, `v2`, etc), the code will 
pick up the latest. Then run:

```bash
branch_calculator -k swp_jpsi_misid -p  0 40 -b -v v1 -s 10000 -P rk
```

which will:

- Create a new set of files in `$ANADIR/Data/swp_jpsi_misid/v1` with each input file, corresponding to an output file.
- Split the input files into 40 groups, with roughly the same file size.
- Process files by chunks of 10 thousands entries at a time. This is needed to prevent the cluster (HTCondor, etc) to run out of memory.
- Process the zeroth group.

Thus, this can be parallelized by running the line above 40 times in 40 jobs.

Currently the command can add:

- `mass`: The candidates masses are recalculated assuming that the two leptons are pions and kaons. Needed for misID studies.

- `swp_jpsi_misid`: Branches corresponding to lepton kaon swaps that make the resonant mode leak into rare modes. Where the swap is inverted and the $J/\psi$ mass provided

- `swp_cascade`: Branches corresponding to $D\to K\pi$ with $\pi\to\ell$ swaps, where the swap is inverted and the $D$ mass provided.

- `hop`: With the $\alpha$ and mass branches calculated

- `brem_track_2`: This will calculate branches associated to the brem correction. 
    The branches will include:
    - Masses of B and Jpsi.
    - Momenta of mesons and electrons.
    - Derived quantities like `DIRA` or the `brem` categories.

- `mva`: With the BDT branches 
- `smear`: This will calculate the smeared masses `B_Mass_smr` and `Jpsi_Mass_smr` and `q2_smr`.

```mermaid
graph TD
  mass([mass])
  swp_jpsi_misid([swp_jpsi_misid])
  swp_cascade([swp_cascade])
  hop([hop])
  brem_track_2([brem_track_2])
  smear([smear])
  mva([mva])

  brem_track_2 -->|needs corrected masses| smear
  brem_track_2 -->|training on brem features| mva
  hop -->|required by mva| mva
  smear -->|q² wise models from smeared q²| mva
```

### Calculating friend trees with jobs

These trees take time to calculate, therefore one has to send jobs to the cluster in IHEP 
(LXPLUS HTCondor is not supported). For that do:

```bash
make_friend_trees -p rk_nopid -e mva smear -c rk # makes all the trees excluding mva and smear
make_friend_trees -p rk_nopid -o smear     -c rk # makes only the smear tree
make_friend_trees -p rk_nopid -o mva       -c rk # makes only the mva tree
```

Where the order of the trees is needed due to the dependencies. E.g. in order to make the `smear` trees
one needs the `brem_track_2` trees. The options are:

```
options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Name of config file, e.g. rk_nopid
  -p PROJECT, --project PROJECT
                        Name of project, e.g. rk
  -e EXCLUDE [EXCLUDE ...], --exclude EXCLUDE [EXCLUDE ...]
                        List of names of friend trees to exclude
  -o ONLY, --only ONLY  Name the only friend tree to make
  -w WCARD, --wcard WCARD
                        Wildcard to match files
  -d, --dry_run         If used, it will do a dry run, fewer jobs and no outputs
  -l {10,20,30}, --log_lvl {10,20,30}
                        Logging level
```

In this case, these last two flags are needed because the `mva` trees are calculated with the `brem_track_2`
trees as input. Therefore they can only be processed afterwards.

## Missing files

Once the extra branches have been calculated, one will have a file structure like:

```
├── brem_track_2
│   └── v1
├── hop
│   ├── v1
│   └── v2
├── main
│   ├── v1
│   ├── v5
│   └── v7
├── mva
│   ├── v1
│   ├── v2
│   ├── v3
│   └── v4
├── swp_cascade
│   ├── v1
│   └── v2
└── swp_jpsi_misid
    ├── v1
    └── v2
```

Typically (not always), a sample in `main` should be also in all the other friend trees.
If samples are missing, one could do:

```bash
check_missing -p rx
```

other options are:

```
options:
  -h, --help            show this help message and exit
  -p --project E.g. rx 
  -o --only    Optional, if used, will check only this friend, e.g. mva
  -s SKIP_SAM [SKIP_SAM ...], --skip_sam SKIP_SAM [SKIP_SAM ...]
                        Samples to skip
  -l {10,20,30}, --log_level {10,20,30}
                        Logging level
```

the output will be `missing.yaml`. This file will tell you:

- Which friend trees have which samples missing.
- Which are the files missing

In this case `missing` is relative to the samples and files in the `main` sample.

## Moving files from one project to another

If one needs to create a new project from an existing one, and put existing files
in that project, one can:

```bash
move_sample -r "^data_24.*" -s rk -t rk_old
```

which will create an `rk_old` project with both main and friend trees of the `rk`
project and will move all data files to it. Use `-d` for a dry run.

## Calculating luminosity

For this one would have to use the `get_lumi` script in this project, together
with the one in [this](https://gitlab.cern.ch/lhcb-luminosity/lumi_calib/-/blob/master/get_lumi.py?ref_type=heads)
project. This should, at some point, be cleaned up.

