# Installation

This project uses [Pixi](https://pixi.sh/) for dependency management and environment setup.

1. Install Pixi, following the instructions [here](https://pixi.sh/)
2. Clone the repository and navigate into the directory:
   ```bash
   git clone git@github.com:acampove/cal-rx-run3.git
   cd cal-rx-run3
   ```
3. Install the environment and dependencies:
   ```bash
   pixi install
   ```

4. Enter the Pixi environment shell:
   ```bash
   pixi shell
   ```

5. Install package:

    ```bash
    uv pip install -r requirements.txt
    ```

6. Install the pre-commit hooks:
   ```bash
   pre-commit install
   ```

These hooks live in `hooks/` and will

- Copy the `pyrefly.toml` of the project to each package.
This is done in order to make sure all the packages follow the same
static analysis configuration.
