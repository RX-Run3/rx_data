'''
Snakefile for branch_calculator pipeline.
Runs branch calculations for all kinds/projects/parts,
with mva and smear depending on all other kinds.
'''
import os

ENV       = 'rx_run3'
NAME      = 'branch_calculator' 
LOGDIR    = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
HOME      = os.environ['HOME'] 
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
                path = f'{ANADIR}/tmp/sentinels/{NAME}/{project}/{kind}/{vers}/part_{part:03d}.done'
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
        done = f'{ANADIR}/tmp/sentinels/{NAME}/{{project}}/{{kind}}/{{vers}}/part_{{part}}.done'
    wildcard_constraints:
        kind = '|'.join(VERSIONS),
        vers = r'v\d+'
    log: 
        prc = f'{LOGDIR}/{{project}}_{{kind}}_{{vers}}_{{part}}.prc',
        err = f'{LOGDIR}/{{project}}_{{kind}}_{{vers}}_{{part}}.err',
        out = f'{LOGDIR}/{{project}}_{{kind}}_{{vers}}_{{part}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{kind}}_{{vers}}_{{part}}.log',
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    params:
        LOGD       = LOGDIR,
        vers       = lambda wc: VERSIONS[wc.kind],
        phot_veto  = PHOT_VETO,
        chunk      = CHUNK,
        part_idx   = lambda wc: int(wc.part),
        n_parts    = N_PARTS,
        home       = HOME,
        env        = ENV,
    shell:
        '''
        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true

        (
        source setup.sh {params.env} {params.home}
        branch_calculator                         \
            -k {wildcards.kind}                   \
            -P {wildcards.project}                \
            -v {params.vers}                      \
            -s {params.chunk}                     \
            -p {params.part_idx} {params.n_parts} \
            -g {params.phot_veto}
        ) > {log.prc} 2>&1

        mkdir -p $(dirname {output.done})
        touch {output.done}
        '''
