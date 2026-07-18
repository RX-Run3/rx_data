import os

CMB    = [
    '990',
    ]
PRC    = [
    '400',
    '500',
    '600',
    '700',
    '800',
    ]

# ---------------------
ENV    = 'rx_run3'
HOME   = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR = '/publicfs/ucas/user/campoverde/Data'
LOGDIR = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
BLOCK  = list(range(1, 9))
BREM   = ['brem_xx1', 'brem_xx2']
NAME   = 'reso_dtf'
YEAR   = '2024'
# ---------------------
rule all:
    input:
        expand(
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/{{brem}}/sweights.json',
            cmb   = CMB,
            prc   = PRC,
            brem  = BREM,
            block = BLOCK)
# ---------------------
rule sweights:
    output :
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/{{brem}}/sweights.json',
    input  :
        expand(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/{{brem}}/nll.bytes',
            cmb   = CMB,
            prc   = PRC,
            brem  = BREM,
            block = BLOCK)
    log    : f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_{{block}}_{{brem}}/rk_ee/plots/sweights.log'
    params :
        home    = HOME,
        env     = ENV,
        ana_dir = ANADIR,
        nll_path= lambda wc : f'{ANADIR}/fits/data/{NAME}/{wc.cmb}_{wc.prc}_b{wc.block}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/{wc.brem}/nll.bytes',
    shell  :
        '''
        source setup.sh {params.env} {params.home}
        rxfitter calculate-sweights -f {params.nll_path}
        '''
# ---------------------
rule fits:
    output   :
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/nll.bytes',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/nll.bytes',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
        directory(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24'),
        directory(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee'),
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
                    -c reso/rk/ee \
                    -q jpsi \
                    -C $CMB_WP\
                    -P $PRC_WP

        echo "Fit done with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
