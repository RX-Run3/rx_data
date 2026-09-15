mkdir logs
let log_file = $"logs/prec_run_(date now | format date '%Y%m%d_%H%M%S').log"
let blocks   = seq 1 8
let projects = ["rk"] #  , "rkst"]
let sources  = ["jpsi", "psi2"]
let targets  = ["jpsi", "psi2", "high"]
let total    = ($blocks | length) * ($projects | length) * ($sources | length) * ($targets | length)
let mode     = "reuse"

# - Selects lower sideband in muon data
# - Fits it to a non-parametric PDF
# - Convolves it with transfer function to produce part-reco templates
def main [ 
    --wp (-w) : string # String specifying working point, e.g. "mva_cmb-7 mva_prc-6"
] {
    mut index = 0
    for block in $blocks {
        for project in $projects {
            for source in $sources {
                for target in $targets {
                    if $source == "jpsi" and $target == "high" {
                        continue
                    }

                    $index = $index + 1
                    let binning = $"block-($block) ($wp)"
                    print $"[Progress: ($index)/($total)] block: ($block), project: ($project), -s ($source) -t ($target)"
                    hqm make-prec -p $project -s $source -t $target -b $binning -m $mode out+err>> $log_file
                }
            }
            return
        }
    }
}
