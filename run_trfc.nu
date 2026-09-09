#!/usr/bin/env nu

mkdir logs
let log_file = $"logs/trfc_run_(date now | format date '%Y%m%d_%H%M%S').log"

def run-fit [] {
    for block in 1..8 {
        let b_arg = $"block-($block) mva_cmb-7 mva_prc-7"
        for project in [rk, rkst] {
            hqm make-trfc -b $b_arg -p $project -s jpsi -t jpsi
            hqm make-trfc -b $b_arg -p $project -s jpsi -t psi2
            hqm make-trfc -b $b_arg -p $project -s psi2 -t jpsi
            hqm make-trfc -b $b_arg -p $project -s psi2 -t psi2
            hqm make-trfc -b $b_arg -p $project -s psi2 -t high
            hqm make-trfc -b $b_arg -p $project -s jpsi -t high
        }
    }
}

run-fit out+err> $log_file

