import os

ANADIR = os.environ['ANADIR']
CMB    = [
    '950',
    ]
PRC    = [
    '600',
    ]

BLOCK  = list(range(1, 9))[:1]
NAME   = 'reso_no_dtf'
# ---------------------
rule all:
    input: 
        expand(
            [f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/fit_linear.png',
             f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/fit_linear.png'],
            cmb   = CMB,
            prc   = PRC,
            block = BLOCK)
# ---------------------
rule fits:
    output   : 
        f'{ANADIR}/fits/data/{NAME}/{{cmb}}_{{prc}}_b{{block}}/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/{{brem}}/fit_linear.png',
    params:
        name = NAME
    shell :
        '''
        source setup.sh rx_run3 $HOME
        CMB_WP=$(rxfitter wp-translator -w {wildcards.cmb})
        PRC_WP=$(rxfitter wp-translator -w {wildcards.prc})

        fit_rx_reso -b {wildcards.block}\
                    -g {params.name}\
                    -c reso/rk/ee \
                    -q jpsi \
                    -r \
                    -C $CMB_WP\
                    -P $PRC_WP || true

        rxfitter make-dummy-plot -p {output} -t {wildcards.cmb}_{wildcards.prc}
        '''
