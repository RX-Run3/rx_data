#!/usr/bin/env nu

mkdir logs
let log_file     = $"logs/prec_run_(date now | format date '%Y%m%d_%H%M%S').log"
let blocks       = seq 1 8
let projects     = ["rk", "rkst"]
let sources      = ["jpsi", "psi2"]
let targets      = ["jpsi", "psi2", "high"]

let total = ($blocks | length) * ($projects | length) * ($sources | length) * ($targets | length)
mut index = 0

for project in $projects {
    for source in $sources {
        for target in $targets {
            if $source == "jpsi" and $target == "high" {
                continue
            }

            for block in $blocks {
                $index = $index + 1
                let binning = $"block-($block) mva_cmb-7 mva_prc-7"
                print $"[Progress: ($index)/($total)] block: ($block), project: ($project), -s ($source) -t ($target)"
                hqm make-prec -p $project -s $source -t $target -b $binning out+err>> $log_file
            }
        }
    }
}
