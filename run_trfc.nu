
mkdir logs
let log_file     = $"logs/trfc_run_(date now | format date '%Y%m%d_%H%M%S').log"
let blocks       = seq 1 8
let mode         = "reuse"
let projects     = ["rk"] #, "rkst"]
let combinations = [
    {s: jpsi, t: jpsi},
    {s: jpsi, t: psi2},
    {s: psi2, t: jpsi},
    {s: psi2, t: psi2},
    {s: psi2, t: high}
]

# Run fits to electron channel simulation to extract transfer functions 
def main [ 
    --binning (-b) : string # String defining binning, e.g. "mva_cmb-1 mva_prc-3"
] {
    let total = ($blocks | length) * ($projects | length) * ($combinations | length)
    mut index = 0

    for block in $blocks {
        let b_arg = $"block-($block) ($binning)"
        for project in $projects {
            for c in $combinations {
                $index = $index + 1
                print $"[Progress: ($index)/($total)] block: ($block), project: ($project), -s ($c.s) -t ($c.t)"
                hqm make-trfc -b $b_arg -p $project -s $c.s -t $c.t -m $mode out+err>> $log_file
            }
            return
        }
    }
}
