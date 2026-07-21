import os

from omegaconf   import OmegaConf
from dmu.generic import utilities as gut

# ---------------------
ENV     = 'rx_run3'
HOME    = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR  = '/publicfs/ucas/user/campoverde/Data'
LOGDIR  = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
KIND    = config['kind']
Q2BINS  = ['low', 'central', 'jpsi', 'psi2', 'high']
# ---------------------
def _get_inputs() -> list[str]:
    paths = []
    for args in config['args']:
        for fname in config['output']:
            sample = args['sample' ]
            trigger= args['trigger']
            q2bin  = args['q2bin'  ]

            fpath  = f'{ANADIR}/plots/cutflow/{KIND}/{sample}_{trigger}_{q2bin}/{fname}'
            paths.append(fpath)

    return paths
# ---------------------
rule all:
    input: _get_inputs()
# ---------------------
rule cutflow:
    output:
        [
            f'{ANADIR}/plots/cutflow/{KIND}/{{sample}}_{{trigger}}_{{q2bin}}/{fname}'
            for fname in config['output'] 
        ]
    wildcard_constraints:
        trigger = '(rk|rkst)_(ee|mm)_(os|ss)'
        q2bin   = '|'.Q2BINS
    log:
        prc = f'{LOGDIR}/cutflow_{KIND}_{{sample}}_{{trigger}}_{{q2bin}}.prc',
        err = f'{LOGDIR}/cutflow_{KIND}_{{sample}}_{{trigger}}_{{q2bin}}.err',
        out = f'{LOGDIR}/cutflow_{KIND}_{{sample}}_{{trigger}}_{{q2bin}}.out',
        LOG = f'{LOGDIR}/cutflow_{KIND}_{{sample}}_{{trigger}}_{{q2bin}}.log',
    params:
        LOGD = LOGDIR,
        home = HOME,
        env  = ENV,
        kind = KIND,
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}

        cutflow -q {wildcards.q2bin} \
                -s {wildcards.sample} \
                -t {wildcards.trigger} \
                -c {params.kind} \
                -n 1 

        echo "Cutflow done with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
