# Runs full chain with
# - Fit to simulated samples
def main [
    --binning (-b) : string # E.g. "mva_cmb-3 mva_prc-2"
] {
    nu run_fits.nu -w $binning
    nu run_trfc.nu -b $binning
    nu run_prec.nu -b $binning
}
