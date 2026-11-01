import os

from dmu.generic import utilities as gut

qsq_bin   = config['qsq_bin'   ]
systs     = config['systematic']
# -------------
KIND      = 'rx'
ENV       = 'rx_run3'
HOME      = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR    = '/publicfs/ucas/user/campoverde/Data'
PACDIR    = '/publicfs/ucas/user/campoverde/Packages/cal-rx-run3'
LOGDIR    = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
OUT_PATH  = f'{ANADIR}/fits/data/nll'
MODE      = 'rare'
# ---------------------------------------
paths = []
for qsq in qsq_bin:
    for syst in systs:
        path = f'{OUT_PATH}/{syst}/default_default_all/{MODE}/{qsq}/nll.bytes'
        paths.append(path)
# ---------------------------------------
rule all:
    input : paths
# ---------------------
rule nlls:
    output: f'{OUT_PATH}/{{syst}}/default_default_all/{MODE}/{{qsq}}/nll.bytes'
    wildcard_constraints:
        qsq  = '|'.join(qsq_bin),
        syst = '|'.join(systs),
    log:
        prc = f'{LOGDIR}/{{qsq}}_{{syst}}.prc',
        err = f'{LOGDIR}/{{qsq}}_{{syst}}.err',
        out = f'{LOGDIR}/{{qsq}}_{{syst}}.out',
        LOG = f'{LOGDIR}/{{qsq}}_{{syst}}.log',
    params:
        LOGD = LOGDIR,
        pkg  = PACDIR,
        home = HOME,
        kind = KIND,
        env  = ENV,
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        (
        export USER={params.env}
        export HOME={params.home}
        set +euo pipefail
        source {params.home}/.bashrc
        set -euo pipefail
        cd {params.pkg}

        pixi run --as-is fit_rx_rare_sim    \
                        -b -1               \
                        -k {params.kind}    \
                        -g nll              \
                        -q {wildcards.qsq}  \
                        -s {wildcards.syst}
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
# ---------------------
