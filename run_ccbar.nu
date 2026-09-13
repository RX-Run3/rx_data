#!/usr/bin/env nu

for project in ["rk", "rkst"] {
    for iblock in 1..8 {
        hqm make-ccbar -b $"block-($iblock) mva_cmb-7 mva_prc-7" -p $project
    }
}
