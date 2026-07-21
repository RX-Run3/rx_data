import os

# ---------------------
ENV     = 'rx_run3'
HOME    = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR  = '/publicfs/ucas/user/campoverde/Data'
LOGDIR  = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
KIND    = config['kind']

BLOCKS  = [1, 2, 3, 4, 5, 6, 7, 8]
BREMS   = [-1, 1, 2]
MVAS    = [0, 1]
Q2BINS  = ['none', 'all', 'low', 'central', 'jpsi', 'psi2', 'high']

OUTPUT_NAMES = config['output'][KIND]

# ---------------------
def _brem_name(brem: int) -> str:
    return 'all' if brem == -1 else str(brem)

def _mva_name(mva: int) -> str:
    return 'drop_mva' if mva == 0 else 'with_mva'

# ---------------------
def _get_inputs() -> list[str]:
    paths = []
    for args in config['args']:
        sample  = args['sample' ]
        trigger = args['trigger']
        q2_bin  = args['q2_bin' ]

        for block in BLOCKS:
            for brem in BREMS:
                for mva in MVAS:
                    brem_name = _brem_name(brem)
                    mva_name  = _mva_name(mva)
                    dir_path  = f'{ANADIR}/plots/comparison/{KIND}/{sample}/{trigger}/{q2_bin}/{brem_name}_{block}/{mva_name}'

                    for fname in OUTPUT_NAMES:
                        paths.append(f'{dir_path}/{fname}')

    return paths
# ---------------------
rule all:
    input: _get_inputs()
# ---------------------
rule compare:
    output:
        [
            f'{ANADIR}/plots/comparison/{KIND}/{{sample}}/{{trigger}}/{{q2_bin}}/{{brem_name}}_{{block}}/{{mva_name}}/{fname}'
            for fname in OUTPUT_NAMES
        ]
    wildcard_constraints:
        q2_bin    = '|'.join(Q2BINS),
        block     = '|'.join(str(b) for b in BLOCKS),
        brem_name = 'all|1|2',
        mva_name  = 'drop_mva|with_mva',
    log:
        prc = f'{LOGDIR}/compare_{KIND}_{{sample}}_{{trigger}}_{{q2_bin}}_{{brem_name}}_{{block}}_{{mva_name}}.prc',
        err = f'{LOGDIR}/compare_{KIND}_{{sample}}_{{trigger}}_{{q2_bin}}_{{brem_name}}_{{block}}_{{mva_name}}.err',
        out = f'{LOGDIR}/compare_{KIND}_{{sample}}_{{trigger}}_{{q2_bin}}_{{brem_name}}_{{block}}_{{mva_name}}.out',
        LOG = f'{LOGDIR}/compare_{KIND}_{{sample}}_{{trigger}}_{{q2_bin}}_{{brem_name}}_{{block}}_{{mva_name}}.log',
    params:
        LOGD = LOGDIR,
        home = HOME,
        env  = ENV,
        kind = KIND,
        brem = lambda wc: -1 if wc.brem_name == 'all' else int(wc.brem_name),
        mva  = lambda wc: 0 if wc.mva_name == 'drop_mva' else 1,
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}

        compare -s {wildcards.sample} \
                -t {wildcards.trigger} \
                -q {wildcards.q2_bin} \
                -c {params.kind} \
                -b {params.brem} \
                -B {wildcards.block} \
                -m {params.mva} \
                -e 1 \
                -n 1

        echo "Compare done with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
