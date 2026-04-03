import os

CMB    = [
    '950',
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
BLOCK  = list(range(1, 9))
NAME   = 'reso_no_dtf'
# ---------------------
rule all:
    input: 
        expand(
            [
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}/rk_ee/plots/scales.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/main_brem_xx1_b{{block}}/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/main_brem_xx2_b{{block}}/parameters.json'],
            cmb   = CMB,
            prc   = PRC,
            block = BLOCK)
# ---------------------
rule scales:
    output : f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}/rk_ee/plots/scales.json'
    input  : 
        expand(
            [
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/main_brem_xx1_b{{block}}/parameters.json',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/main_brem_xx2_b{{block}}/parameters.json',
            ],
            allow_missing = True,
            block         = BLOCK)
    log    : f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}/rk_ee/plots/scales.log'
    params :
        home = HOME,
        env  = ENV,
    shell  :
        '''
        source setup.sh {params.env} {params.home}

        CMB_WP=$(rxfitter wp-translator -w {wildcards.cmb})
        PRC_WP=$(rxfitter wp-translator -w {wildcards.prc})

        dump_q2_ratios -k B -p rk_ee -y 2024 -C $CMB_WP -P $PRC_WP > {log} 2>&1 || true
        '''
# ---------------------
rule fits:
    output   : 
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/main_brem_xx1_b{{block}}/parameters.json',
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/main_brem_xx2_b{{block}}/parameters.json',
    log   : f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/fits.log'
    params:
        name = NAME,
        home = HOME,
        env  = ENV,
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        source setup.sh {params.env} {params.home}

        CMB_WP=$(rxfitter wp-translator -w {wildcards.cmb})
        PRC_WP=$(rxfitter wp-translator -w {wildcards.prc})

        set +e
        fit_rx_reso -b {wildcards.block}\
                    -g {params.name}\
                    -c reso/rk/ee \
                    -q jpsi \
                    -r \
                    -C $CMB_WP\
                    -P $PRC_WP  > {log} 2>&1
        set -e
        '''
