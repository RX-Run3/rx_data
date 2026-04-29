'''
Snakefile for branch_calculator pipeline.
Runs branch calculations for all kinds/projects/parts,
with mva and smear depending on all other kinds.
'''
import os
import glob

ANADIR    = os.environ['ANADIR']
CHUNK     = config['chunk_size']
PHOT_VETO = config['photon_veto']
N_PARTS   = config['parts']
VERSIONS  = config['versions']
PROJECTS  = config['projects']
# ── Helper ────────────────────────────────────────────────────────────────────
def sentinels():
    '''Path to the sentinel file that marks a part as done.'''
    paths = []
    for project in PROJECTS:
        for kind, vers in VERSIONS.items():
            for part in range(N_PARTS):
                path = f'{ANADIR}/tmp/sentinels/{project}/{kind}/{vers}/part_{part:03d}.done'
                paths.append(path)

    return paths
# ── Rules ─────────────────────────────────────────────────────────────────────
rule all:
    '''Request all sentinel files for every combination.'''
    input:
        sentinels()
rule run_independent:
    '''Run branch_calculator for one independent kind / project / part.'''
    output:
        done = f'{ANADIR}/tmp/sentinels/{{project}}/{{kind}}/{{vers}}/part_{{part}}.done'
    wildcard_constraints:
        kind = '|'.join(VERSIONS),
    params:
        version    = lambda wc: VERSIONS[wc.kind],
        phot_veto  = PHOT_VETO,
        chunk      = CHUNK,
        part_idx   = lambda wc: int(wc.part),
        n_parts    = N_PARTS,
    shell:
        '''
        branch_calculator \
            -k {wildcards.kind} \
            -P {wildcards.project} \
            -v {params.version} \
            -s {params.chunk} \
            -p {params.part_idx} {params.n_parts} \
            -g {params.phot_veto}

        mkdir -p $(dirname {output.done})
        touch {output.done}
        '''
