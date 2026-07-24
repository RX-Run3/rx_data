import os

CMB    = [
    '990',
    ]
PRC    = [
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
BREM   = ['brem_xx0']
NAME   = 'reso_dtf'
YEAR   = '2024'
QSQ    = config['q2bin']
PRJ    = config['project']

if   QSQ == 'jpsi'        and PRJ == 'rk':
    SIGNAL = 'bpkpjpsimm'
elif QSQ == 'psi2'        and PRJ == 'rk':
    SIGNAL = 'bpkppsi2mm'
elif QSQ == 'jpsi'        and PRJ == 'rkst':
    SIGNAL = 'bdkstkpijpsimm'
elif QSQ == 'psi2'        and PRJ == 'rkst':
    SIGNAL = 'bdkstkpipsi2mm'
else:
    raise ValueError(f'Invalid q2 bin/project: {QSQ}/{PRJ}')
# ---------------------
rule all:
    input:
        expand(
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/data_24/fit/brem_xx0/{{brem}}/swt_yld_{SIGNAL}_{{brem}}.json',
            cmb   = CMB,
            prc   = PRC,
            brem  = BREM,
            block = BLOCK)
# ---------------------
rule sweights:
    output :
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/data_24/fit/brem_xx0/{{brem}}/swt_yld_{SIGNAL}_{{brem}}.json',
    input  :
        expand(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/data_24/fit/brem_xx0/{{brem}}/nll.bytes',
            cmb   = CMB,
            prc   = PRC,
            brem  = BREM,
            block = BLOCK)
    log   :
        prc = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}_{{brem}}_swt.prc',
        err = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}_{{brem}}_swt.err',
        out = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}_{{brem}}_swt.out',
        LOG = f'{LOGDIR}/{{cmb}}_{{prc}}_b{{block}}_{{brem}}_swt.log',
    params :
        LOGD    = LOGDIR,
        home    = HOME,
        env     = ENV,
        ana_dir = ANADIR,
        nll_path= lambda wc : f'{ANADIR}/fits/data/{NAME}/{wc.cmb}_{wc.prc}_b{wc.block}/reso/{PRJ}/mm/{QSQ}/data_24/fit/brem_xx0/{wc.brem}/nll.bytes',
    shell  :
        '''
        (
        source setup.sh {params.env} {params.home}

        rxfitter calculate-sweights -f {params.nll_path}

        echo "Fit done with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
# ---------------------
rule fits:
    output   :
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/data_24/fit/brem_xx0/brem_xx0/nll.bytes',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/data_24/fit/brem_xx0/brem_xx0/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/{SIGNAL}/fit/brem_xx0/brem_xx0/parameters.json',
        directory(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/data_24'),
        directory(f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/{PRJ}/mm/{QSQ}/{SIGNAL}'),
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
                    -g {params.name}    \
                    -c reso/{PRJ}/mm       \
                    -q {QSQ}            \
                    -C $CMB_WP          \
                    -P $PRC_WP

        echo "Fit done with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
