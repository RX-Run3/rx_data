[TOC]

This project is meant to be used to make classifiers for the RX analyses

# Training

For that run:

```bash
train_classifier -v v6 -c cmb -q low
train_classifier -v v6 -c cmb -q central
train_classifier -v v6 -c cmb -q high

train_classifier -v v6 -c prc -q low
train_classifier -v v6 -c prc -q central
train_classifier -v v6 -c prc -q high
```

Which will train the classifiers for different $q^2$ bins and with different
settings. The settings are part of `YAML` files and are stored in:

```bash
rx_classifier/src/rx_classifier_data/v6
```

The underlying tool doing all the training can be found in 
[dmu](https://github.com/acampove/dmu?tab=readme-ov-file#machine-learning)

other options that this utility takes are:

```
options:
  -h, --help            show this help message and exit
  -v VERSION, --version VERSION
                        Version of config files
  -c CFG_NAME, --cfg_name CFG_NAME
                        Kind of config file
  -q {low,central,jpsi,psi2S,high}, --q2bin {low,central,jpsi,psi2S,high}
                        q2bin
  -l {10,20,30}, --log_level {10,20,30}
                        Logging level
  -m MAX_ENTRIES, --max_entries MAX_ENTRIES
                        Limit datasets entries to this value
  -p, --plot_only       If used, will only do plots of feature distributions, not
                        training
  -L, --load_trained    Nothing changes, but instead of training models, will load
                        trained models, which should exist
```

# Output

The output of this training are, for each fold:

- Pickle file with the classifier
- ROC curve
- Importance table
- Classifier score
- Hyper-parameters table
- Plots of the features
- Covariance matrix

# Performance

In order to compare the performances use:

```bash
compare_classifier -c cmb_high -n 10000
```

where:

- `-c` specifies the name of the config file in `rx_classifier_data/performance/{name}.yaml`
- `-n` specifies the number of entries to use, these are chosen randomly.

The config file will specify:

- How to make the plots, ranges, colors, etc.
- What models to test.
- What samples to pick for signal and proxy backgrounds, including the selections.

**Note:** By selection, we mean what we add **on top** of the default analysis selection.

# TODO

Some things that can be tried are:

- Fix overtraining problem
- Improve way how paths are specified in YAML files
- Try MLFlow to keep track of plots, etc

# MVA Optimization

For this one needs:

- Expected signal yields for different working points
- Background yields from fits to actual data
- A utility that puts them together to find the optimal significance

### Signal yields

For this run:

```bash
rxfitter expected-signal -n full_scan -c 0.99 -p 0.6 -t rk_ee_os -q high
```

which will

- Use the `full_scan.yaml` config specifying 
    - The grid spacing
    - The name of the resonant mode fits to be used as normalization
    - The name of the directory in `ANADIR` where the yields will go
- Specify the working point at which the resonant mode yields should be used.
In the example above `(0.99, 0.6)`
- Specify the trigger and `q2bin` for which the expected signal yields are needed

### Background yields


