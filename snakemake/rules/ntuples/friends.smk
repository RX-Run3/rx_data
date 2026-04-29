"""
Snakefile for branch_calculator pipeline.
Runs branch calculations for all kinds/projects/parts,
with mva and smear depending on all other kinds.
"""

import os
import glob

# ── Config ────────────────────────────────────────────────────────────────────

configfile: "snakemake/configs/ntuples/friends.yaml"

CHUNK      = config["chunk_size"]
PHOT_VETO  = config["photon_veto"]
N_PARTS    = config["parts"]
VERSIONS   = config["versions"]
PROJECTS   = config["projects"]

# Split kinds into independent vs dependent
DEPENDENT_KINDS   = ["mva", "smear"]

INDEPENDENT_KINDS = { kind : vers for kind, vers in VERSIONS.items() if kind not in DEPENDENT_KINDS }
BASE_DIR          = "/home/acampove/external_02/Data"
PARTS             = list(range(N_PARTS))
# ── Helper ────────────────────────────────────────────────────────────────────
def sentinels():
    """Path to the sentinel file that marks a part as done."""
    paths = []
    for project in PROJECTS:
        for kind, vers in INDEPENDENT_KINDS.items():
            for part in PARTS:
                path = f"sentinels/{project}/{kind}/{vers}/part_{part:03d}.done"
                paths.append(path)

    return paths
# ── Rules ─────────────────────────────────────────────────────────────────────
rule all:
    """Request all sentinel files for every combination."""
    input:
        sentinels()
# --- Independent kinds (no dependencies) -------------------------------------
rule run_independent:
    """Run branch_calculator for one independent kind / project / part."""
    output:
        done = "sentinels/{project}/{kind}/{vers}/part_{part}.done"
    wildcard_constraints:
        kind = "|".join(INDEPENDENT_KINDS),
    params:
        version    = lambda wc: VERSIONS[wc.kind],
        phot_veto  = PHOT_VETO,
        chunk      = CHUNK,
        part_idx   = lambda wc: int(wc.part),
        n_parts    = N_PARTS,
    shell:
        """
        branch_calculator \
            -k {wildcards.kind} \
            -P {wildcards.project} \
            -v {params.version} \
            -s {params.chunk} \
            -p {params.part_idx} {params.n_parts} \
            -g {params.phot_veto}

        mkdir -p $(dirname {output.done})
        touch {output.done}
        """
