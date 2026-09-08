#!/usr/bin/env bash

set -e

for T in rk_ee_os rkst_ee_os; do
    for s in jpsi psi2; do
        for t in jpsi psi2 high;do
            for block in {1..8}; do
                hqm make-prec -T "$T" -s "$s" -t "$t" -b "$block"
            done
        done
    done
done
