import os

from dmu.generic import utilities as gut

qsq_bin  = config['qsq_bin']
project  = config['project']
channel  = config['channel']
name     = config['name'   ] 

data     = gut.load_data(package = 'fitter_data', fpath = f'yields/{name}.yaml')
mva_cmb  = data['grid']['cmb']
mva_prc  = data['grid']['prc']
# -------------
ENV       = 'rx_run3'
HOME      = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR    = '/publicfs/ucas/user/campoverde/Data'
LOGDIR    = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
out_path  = f'{ANADIR}/fits/data'
mode      = 'rare'
fit_name  = f'rare_fit_{name}'
# ---------------------------------------
paths = []
for qsq in qsq_bin:
    for cmb in mva_cmb:
        for prc in mva_prc:
            for prj in project:
                for chn in channel:
                    path = f'{out_path}/{fit_name}/{cmb}_{prc}_all/{mode}/{prj}/{chn}/{qsq}/data_24/fit/brem_x12/brem_x12/fit_linear.png'
                    paths.append(path)
# ---------------------------------------
rule all:
    input : paths
# ---------------------
rule fits:
    output: f'{out_path}/{fit_name}/{{cmb}}_{{prc}}_all/{mode}/{{prj}}/{{chn}}/{{qsq}}/data_24/fit/brem_x12/brem_x12/fit_linear.png'
    log:
        prc = f'{LOGDIR}/{{cmb}}_{{prc}}_{{prj}}_{{chn}}_{{qsq}}.prc',
        err = f'{LOGDIR}/{{cmb}}_{{prc}}_{{prj}}_{{chn}}_{{qsq}}.err',
        out = f'{LOGDIR}/{{cmb}}_{{prc}}_{{prj}}_{{chn}}_{{qsq}}.out',
        LOG = f'{LOGDIR}/{{cmb}}_{{prc}}_{{prj}}_{{chn}}_{{qsq}}.log',
    params:
        LOGD     = LOGDIR,
        fit_name = fit_name,
        home     = HOME,
        env      = ENV,
        mode     = mode,
    resources:
        htcondor_request_mem_mb = 6000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        (
        source setup.sh {params.env} {params.home}

        fit_rx_rare                                                 \
                    -b -1                                           \
                    -g {params.fit_name}                            \
                    -c {params.mode}/{wildcards.prj}/{wildcards.chn}\
                    -q {wildcards.qsq}                              \
                    -C {wildcards.cmb}                              \
                    -P {wildcards.prc} || true
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
# ---------------------
