let pairs = [
    [component     , trigger   ];
    [bpkpjpsiee    , rk_ee_os  ]
    [bpkppsi2ee    , rk_ee_os  ]
    [bpkpjpsimm    , rk_mm_os  ]
    [bpkppsi2mm    , rk_mm_os  ]
    # [bdkstkpijpsiee, rkst_ee_os]
    # [bdkstkpipsi2ee, rkst_ee_os]
    # [bdkstkpijpsimm, rkst_mm_os]
    # [bdkstkpipsi2mm, rkst_mm_os]
]

let jpsi_ee = [bpkpjpsiee, bdkstkpijpsiee]
let psi2_ee = [bpkppsi2ee, bdkstkpipsi2ee]
let high_ee = []

let jpsi_mm = [bpkpjpsimm, bdkstkpijpsimm]
let psi2_mm = [bpkppsi2mm, bdkstkpipsi2mm]
let high_mm = []

let q2bins  = [jpsi psi2 high]
let blocks  = seq 1 8
let mode    = "reuse"
# -------------------------------
def in_resonant [q2bin: string, component: string] {
    let in_jpsi = ($q2bin == 'jpsi' and $component in $jpsi_ee)
    let in_psi2 = ($q2bin == 'psi2' and $component in $psi2_ee)

    return ($in_jpsi or $in_psi2)
}
# -------------------------------
def skip_fit [q2bin: string, component: string, trigger: string] {
    let is_muon = ($trigger | str contains '_mm_')

    if not $is_muon {
        return false
    }

    if ($q2bin == 'jpsi') and ($component not-in $jpsi_mm) {
        return true
    }

    if ($q2bin == 'psi2') and ($component not-in $psi2_mm) {
        return true
    }

    if ($q2bin == 'high') and ($component not-in $high_mm) {
        return true
    }

    return false
}
# -------------------------------
def fit_mc [component : string, trigger : string, q2bin : string, binning : string] {
    let is_leakage = not (in_resonant $q2bin $component)
    if $is_leakage {
        hqm fit-mc -c $component -t $trigger -q $q2bin    -s -b $binning -m $mode
    } else {
        hqm fit-mc -c $component -t $trigger -q $q2bin -d -s -b $binning -m $mode
        hqm fit-mc -c $component -t $trigger -q $q2bin -k -s -b $binning -m $mode
    }
}
# -------------------------------
# Runs fits for a given bin
def main [
    --wp (-w) : string # E.g. "mva_cmb-7 mva_prc-3"
] {
    for block in $blocks {
        for pair in $pairs {
            for q2bin in $q2bins {
                let component = $pair.component
                let trigger   = $pair.trigger
                let binning   = $"block-($block) ($wp)"

                let skip = (skip_fit $q2bin $component $trigger)
                if $skip {
                    continue
                }

                fit_mc $component $trigger $q2bin $binning
            }
        }
        return
    }
}
# -------------------------------
