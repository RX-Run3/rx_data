let projects = ["rk"] #, "rkst"]
let blocks   = seq 1 8
let mode     = "reuse"

# Will pick up ratios and templates and build a model representing the
# charmonium leaking into the high-q2 bin
def main [
    --binning (-b) : string # Bin associated to this template, E.g. "mva_cmb-3 mva_prc-2"
] {
    for block in $blocks {
        for project in $projects {
            hqm make-ccbar -b $"block-($block) ($binning)" -p $project -m $mode
        }
        return
    }
}
