import os

CMB    = [
    '990',
    ]
PRC    = [
    '600',
    ]
# ---------------------
ENV    = 'rx_run3'
HOME   = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR = '/publicfs/ucas/user/campoverde/Data'
LOGDIR = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
BLOCK  = list(range(1, 2))
NAME   = 'reso_no_dtf'
YEAR   = '2024'
# ---------------------
rule all:
    input:
        expand(
            [
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}/rk_mm/plots/scales.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/data_24/fit/brem_xx0/brem_xx0/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/bpkpjpsimm/fit/brem_xx0/brem_xx0/parameters.json'],
            cmb   = CMB,
            prc   = PRC,
            block = BLOCK)
# ---------------------
rule scales:
    output :
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}/rk_mm/plots/fit_summary.json',
    input  :
        expand(
            [
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/data_24/fit/brem_xx0/brem_xx0/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/bpkpjpsimm/fit/brem_xx0/brem_xx0/parameters.json',
            ],
            allow_missing = True,
            block         = BLOCK)
    log    : f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}/rk_mm/plots/scales.log'
    params :
        home = HOME,
        env  = ENV,
    shell  :
        '''
        source setup.sh {params.env} {params.home}

        CMB_WP=$(rxfitter wp-translator -w {wildcards.cmb})
        PRC_WP=$(rxfitter wp-translator -w {wildcards.prc})

        dump_q2_ratios -k B -p rk_mm -y 2024 -C $CMB_WP -P $PRC_WP > {log} 2>&1 || true
        '''
# ---------------------
rule fits:
    output   :
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/data_24/fit/brem_xx0/brem_xx0/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/bpkpjpsimm/fit/brem_xx0/brem_xx0/parameters.json',
        directory(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/data_24'),
        directory(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/mm/jpsi/bpkpjpsimm'),
    log   :
        prc = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}.prc',
        err = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}.err',
        out = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}.out',
        LOG = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}.log',
    params:
        LOGD = LOGDIR,
        name = NAME,
        home = HOME,
        env  = ENV,
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        (
        source setup.sh {params.env} {params.home}

        CMB_WP=$(rxfitter wp-translator -w {wildcards.cmb})
        PRC_WP=$(rxfitter wp-translator -w {wildcards.prc})

        fit_rx_reso -b {wildcards.block}\
                    -g {params.name}\
                    -c reso/rk/mm \
                    -q jpsi \
                    -r \
                    -C $CMB_WP\
                    -P $PRC_WP

        echo "Fit done with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
