# Fits simultaneously the jpsi and psi2S bin in order to extract
# the part-reco over fully-reco ratios 
def main [ 
    --binning (-b) : string # Binning, e.g. mva_cmb-7 mva_prc-6
] {
    for project in ["rk", "rkst"] {
        for iblock in 1..8 {
            hqm fit-resonant -b $"block-($iblock) ($binning)" -p $project
            return
        }
    }
}
