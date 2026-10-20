import os

from dmu.generic import utilities as gut

qsq_bin   = config['qsq_bin'   ]
systs     = config['systematic']
# -------------
KIND      = 'rx'
CMB       = '0900'
PRC       = '0600'
ENV       = 'rx_run3'
HOME      = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR    = '/publicfs/ucas/user/campoverde/Data'
LOGDIR    = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
OUT_PATH  = f'{ANADIR}/nlls/data'
MODE      = 'rare'
# ---------------------------------------
paths = []
for qsq in qsq_bin:
    for syst in systs:
        path = f'{OUT_PATH}/nll/{CMB}_{PRC}_all/{MODE}/nll_{qsq}_{syst}.bytes'
        paths.append(path)
# ---------------------------------------
rule all:
    input : paths
# ---------------------
rule nlls:
    output: f'{OUT_PATH}/nll/{CMB}_{PRC}_all/{MODE}/nll_{{qsq}}_{{syst}}.bytes'
    log:
        prc = f'{LOGDIR}/{{qsq}}_{{syst}}.prc',
        err = f'{LOGDIR}/{{qsq}}_{{syst}}.err',
        out = f'{LOGDIR}/{{qsq}}_{{syst}}.out',
        LOG = f'{LOGDIR}/{{qsq}}_{{syst}}.log',
    params:
        LOGD = LOGDIR,
        home = HOME,
        kind = KIND,
        env  = ENV,
        cmb  = CMB,
        prc  = PRC,
    resources:
        htcondor_request_mem_mb = 6000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        (
        source setup.sh {params.env} {params.home}

        fit_rx_rare_sim                         \
                        -b -1                   \
                        -k {params.kind}        \
                        -C {params.cmb}         \
                        -P {params.prc}         \
                        -g nll_{wildcards.syst} \
                        -q {wildcards.qsq}      \
                        -s {wildcards.syst}     \
                        -d  || true
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
# ---------------------
