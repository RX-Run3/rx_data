# $R_X$ orchestration

This project is meant to chain all the subtasks in the $R_X$ project.
The dependencies are listed in the `pyproject.toml` and are meant to
be taken from gitlab's master branch, where the latest valid version should be.

# Usage

## Plotting

These are workflows associated to the `rx_plots` project.

| Command       | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `cutflow_law` | Creates plots for the effect of cuts on different variables                 |
| `compare_law` | Compares the effect of:<br>• Brem correction on resolution<br>• Smearing MC due to scale and resolution differences with data |
| `plot_2d`     | Plots: <br>• Mass vs $q^2$ for data with and without the brem correction|

## Training of classifiers

These workflows are associated to the `rx_classifier` project.

```bash
train_law
```

trains the classifiers, the config is in:

`configs/rx_classifier/train.yaml`

## Mass scales and resolutions

For this run:

```
scales_law
```

the config is in:

`configs/rx_q2/scales.yaml`

## Analysis Note

### Tables

The following commands need to be ran to make tables to for the analysis note:

```bash
# Will make table with MC samples used in analysis
tabulate_samples
```
