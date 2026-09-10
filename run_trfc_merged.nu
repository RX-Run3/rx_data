#!/usr/bin/env nu

mkdir logs
let log_file     = $"logs/trfc_run_(date now | format date '%Y%m%d_%H%M%S').log"
let projects     = ["rk", "rkst"]
let combinations = [
    {s: jpsi, t: jpsi},
    {s: jpsi, t: psi2},
    {s: psi2, t: jpsi},
    {s: psi2, t: psi2},
    {s: psi2, t: high}
]

let total = ($projects | length) * ($combinations | length)
mut index = 0

let b_arg = $"mva_cmb-7 mva_prc-7"
for project in $projects {
    for c in $combinations {
        $index = $index + 1
        print $"[Progress: ($index)/($total)]: project: ($project), -s ($c.s) -t ($c.t)"
        hqm make-trfc -b $b_arg -p $project -s $c.s -t $c.t out+err>> $log_file
    }
}

