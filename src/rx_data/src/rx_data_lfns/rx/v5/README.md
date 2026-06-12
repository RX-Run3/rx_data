# Description

This version of the ntuples contains data and MC for all the blocks:

- Added preselection to reduce size of rx trigger trees **only** for RK trees (__Hlt2RD_Bu*__).
The preselection used was:

```yaml
ghost     : H_TRACK_GhostProb<0.3 && L1_TRACK_GhostProb <0.3 && L2_TRACK_GhostProb<0.3
hlt1      : (B_Hlt1TrackMVADecision_TOS == 1) || (B_Hlt1TwoTrackMVADecision_TOS == 1)
hlt2      : (1)
kinem_lep : L1_PT > 500 && L2_PT > 500 && L1_P > 3000 && L2_P > 3000
kinem_had : H_PT > 300 && H_P > 2500
clones    : (th_l1_l2 > 5e-4) && (th_l1_kp > 5e-4) && (th_l2_kp > 5e-4)
tr_ipchi2 : H_IPCHI2_OWNPV > 9 && L1_IPCHI2_OWNPV > 9 && L2_IPCHI2_OWNPV > 9
pid_l     : L1_ProbNNe > 0.2 && L2_ProbNNe > 0.2 && L1_PIDe  > 3.000 && L2_PIDe  > 3.000
pid_k     : H_PIDe <  0.000 && H_PID_K > 2.0
rich      : L1_PPHASRICH && L2_PPHASRICH && H_PPHASRICH
acceptance: L1_INECAL    && L2_INECAL
```

for the electron channel and:

```yaml
ghost     : H_TRACK_GhostProb < 0.3 && L1_TRACK_GhostProb < 0.3 && L2_TRACK_GhostProb< 0.3
hlt1      : (B_Hlt1TrackMVADecision_TOS == 1) || (B_Hlt1TwoTrackMVADecision_TOS == 1)
hlt2      : (1)
kinem_lep : L1_PT > 500 && L2_PT > 500 && L1_P > 3000 && L2_P > 3000
kinem_had : H_PT > 300 && H_P > 2500
clones    : (th_l1_l2 > 5e-4) && (th_l1_kp > 5e-4) && (th_l2_kp > 5e-4)
tr_ipchi2 : H_IPCHI2_OWNPV > 9 && L1_IPCHI2_OWNPV > 9 && L2_IPCHI2_OWNPV > 9
pid_l     : L1_ProbNNmu> 0.2 && L2_ProbNNmu> 0.2 && L1_ISMUON && L2_ISMUON && L1_PID_MU >-3. && L2_PID_MU > -3
pid_k     : (H_ProbNNk   * (1 - H_PROBNN_P) > 0.05) && H_PID_K > 0
rich      : L1_PPHASRICH && L2_PPHASRICH && H_PPHASRICH
acceptance: L1_INMUON && L2_INMUON
cascade   : (1)
jpsi_misid: (1)
```

for the muon channel

- Added extra branches for HOP variables calculation

# Contents

Branches added are:

- **B_BPVX/Y/Z:** Position of the B primary vertex 
- **B_END_VX/Y/Z:** Position of the B vertex 

# On the YAML file

## rx_samples.yaml 

Contains the same as the JSON files but:

- Organized in a tree structure, such that the user can build dataframes more easily
- We dropped the non-rk/rk* trees, only the __Hlt2RD_Bu*__ and __Hlt2RD_B0*__ DecayTree triggers are present.

## rk_samples.yaml 

Same as above but only with  the triggers used for RK.

## Extra trees to befriend main ones

One way to befriend the trees is described 
[here](https://gitlab.cern.ch/rx_run3/rx_data#accessing-ntuples)

All these trees contain the `EVENTNUMBER` and `RUNNUMBER` branches that can be used as an index.

### rk_mva.yaml

These are small trees with the MVA scores and only for RK. They can be attached to the trees in `rk_samples.yaml`
in order to add the combinatorial and prec scores to the main trees through friend trees.

### rk_hop.yaml

This file contains the paths to the HOP variables $\alpha$ and the mass as described [here](https://cds.cern.ch/record/2102345/files/LHCb-INT-2015-037.pdf)

### rk_swp_cascade.yaml

The branches in this file are the $m(K,\ell)$ masses, both assuming the original lepton mass and with the $\ell\to\pi$
hypothesis change. They are meant to be used to study $B\to D(\to K\pi) X$ backgrounds.

### rk_swp_jpsi_misid.yaml

The branches in this file are the $m(K,\ell)$ masses, both assuming the original lepton mass and with the $K\to\ell$
hypothesis change. They are meant to be used to study $B\to J/\psi(\to\ell\ell)K^+$ backgrounds, where one of the leptons
is misidentified as a Kaon and the Kaon is misidentified as a lepton.
