# CI/CD

For this we will use:

## A testing framework
Which in python can be offered by `pytest`. All the tests can be ran interactively with

```bash
pytest src/XXX/tests
```

where `XXX` denotes a given project.

## A parallelization framework

Which will rely on `REANA` and will be in charge of:

- Running tests using multiple CPUs, ideally 30-50.
- Running the analysis code and sending the outputs to EOS (i.e. the delivery).

Due to `REANA` capabilities of:

- Accessing a computing cluster at CERN using Kubernetes or HTCondor
- Accessing EOS, where the ntuples are located.
- Accessing the analysis code in `gitlab.cern.ch`, such that the workflow runs on each push.

## A software environment

Which will be provided by docker containers. These containers are built from a base image:

```bash
gitlab-registry.cern.ch/lhcb-rd/cal-rx-run3:v1
```

which holds the basic dependencies, ROOT, python, etc. On top of it, the analysis code is build
in the CI/CD step in the gitlab through the:

**docker/env.Dockerfile** : Creates image which will be tagged as v*. It installs analysis code on top of dependencies
**docker/ana.Dockerfile** : Creates image on top of tagged image. Installs only analysis code.

files. The latest tag of the image will contain
the latest version of the code that can be build successfuly.

This will ensure that:

- We have available an environment with frozen versions of the depdencies (e.g. pandas, numpy, ROOT)
- We do not need to install everything all over again.
- We do not rely on anyone to provide the software infrastructure (e.g. LCGEnv, Lbconda) and thus we are flexible
on what we need and when.

Currently, the docker container is hosted [here](https://gitlab.cern.ch/LHCb-RD/cal-rx-run3/container_registry/26425) and it can be used with:

```bash
podman pull gitlab-registry.cern.ch/lhcb-rd/cal-rx-run3:v6.4 # Change to latest tagged version
podman run \
    -it --rm --userns=host \
    -v $XDG_RUNTIME_DIR/krb5cc:$XDG_RUNTIME_DIR/krb5cc:Z \
    -e KRB5CCNAME=$XDG_RUNTIME_DIR/krb5cc \
    -e ANADIR=$ANADIR \
    -v $ANADIR:$ANADIR \
    gitlab-registry.cern.ch/lhcb-rd/cal-rx-run3:v6.4 bash
```

where `-v` in the last step will expose `ANADIR` (the path to the inputs) to the container.

### Requirements

The following files exist:

**requirements-dev.txt** Contains the analysis packages and development packages, e.g. pytest
**requirements-ana.txt** Conlains only the analysis packages, would be used to run code in HTCondor, REANA, etc
**requirements-dep.txt** Contains dependencies, pinned to a given version for reproducibility.
**requirements-dep.in** Same as above, but without pinning most packages, used as input for dependency resolver (e.g. uv).

# Further documentation

[On testing](doc/testing.md)
