#!/usr/env/bin nu

# Runs full chain with
# - Fit to simulated samples
def main [
    --binning (-b) : string # E.g. "mva_cmb-3 mva_prc-2"
] {
    nu run_fits.nu -w $binning
}
