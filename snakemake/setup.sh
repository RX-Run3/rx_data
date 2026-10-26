#!/usr/bin/env bash

# This script is meant to be ran by a Snakefile in order to
# stup the environment before running tests in the REANA cluster
#
# TL;DR the user should not source this

set -euo pipefail

ENVNAME=$1
export HOME=$2

activate_env()
{
    set +euo pipefail
    source $HOME/.bashrc
    set -euo pipefail

    pixi shell
}

check_env()
{
    FAIL=0

    if ! command -v python &>/dev/null;then
        echo "Failed to find python"
        FAIL=1
    fi

    if ! command -v root   &>/dev/null;then
        echo "Failed to find ROOT"
        FAIL=1
    fi

    if [[ $FAIL -ne 0 ]];then
        echo "Failed to find ROOT/Python"
        exit 1
    fi
}

export ZFIT_DISABLE_TF_WARNINGS=1
export MPLCONFIGDIR=/tmp/rx/mplt
export USER=$ENVNAME

activate_env
check_env
