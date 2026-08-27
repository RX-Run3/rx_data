# Description

These files are meant to store the selection used by RK and RKstar analyses.

## v1

This is a soft preselection used to get the `v5` of the `post_ap` ntuples and it has been taken from Run1/2 RX analysis.

## v2

It adds:

`cascade`   : Veto to remove cascade decays, i.e. $B\to D(\to K\pi)X$ decays.
`jpsi_misid`: Veto to remove leakage from resonant into rare channel.
`hop`       : Veto on HOP mass to remove partially reconstructed

None of these requirements have been optimized yet.

## latest

Cut on both leptons $p_T$ at 250 MeV
