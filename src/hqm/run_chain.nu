# Runs full chain with
# - Fit to simulated samples
# - Pick fits to create transfer functions
# - Use transfer functions to get part-reco in electron channel
# - Run simultaneous fit to resonant mode to get part-reco ratios
# - Put together ratios and fully reco and part reco templates into single PDF
def main [
    --binning (-b) : string # E.g. "mva_cmb-3 mva_prc-2"
] {
    nu run_fits.nu   -w $binning
    nu run_trfc.nu   -b $binning
    nu run_prec.nu   -w $binning
    nu run_ratios.nu -b $binning
    nu run_ccbar.nu  -b $binning
}
