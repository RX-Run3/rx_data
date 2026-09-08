#!/usr/bin/env bash

log_file="trfc_run_$(date +%Y%m%d_%H%M%S).log"

(
set -e
for block in {1..8}; do
    for project in rk rkst; do
        hqm make-trfc -b "$block" -p "$project" -s jpsi -t jpsi
        hqm make-trfc -b "$block" -p "$project" -s jpsi -t psi2
        hqm make-trfc -b "$block" -p "$project" -s psi2 -t jpsi
        hqm make-trfc -b "$block" -p "$project" -s psi2 -t psi2
        hqm make-trfc -b "$block" -p "$project" -s psi2 -t high
        hqm make-trfc -b "$block" -p "$project" -s jpsi -t high
    done
done
) > "$log_file" 2>&1

