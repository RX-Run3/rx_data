import os
from pathlib import Path

_COMPONENTS = [
    'data', 
    'combinatorial', 
    'ccbar', 
    'prec', 
    'jpsi_leakage', 
    'psi2_leakage',
    'signal',
    ]
_Q2BINS    = ['low', 'central', 'high']
_INPUT_DIR = Path('/home/acampove/Downloads/scan_003')
_OUTPUTDIR = os.environ['ANADIR'] + '/plots_for_web/scan/components'
# ----------------------------
def _get_wc() -> tuple[list[str], list[str]]:
    '''
    Returns
    ---------
    Working points for BDT
    '''
    paths = list(_INPUT_DIR.glob('*'))

    cmb   = [ path.name.split('_')[0] for path in paths ]
    prc   = [ path.name.split('_')[1] for path in paths ]

    return cmb, prc
# ----------------------------
cmb, prc = _get_wc()

rule all:
    input: 
        expand(
        _OUTPUTDIR + '/{q2bin}/{prc}_{cmb}/{component}.png',
        cmb       = cmb, 
        prc       = prc, 
        component = _COMPONENTS,
        q2bin     = _Q2BINS,
        ),
        # ----------
        expand(
        _OUTPUTDIR + '/{q2bin}/{prc}_{cmb}/index.md',
        cmb       = cmb, 
        prc       = prc, 
        component = _COMPONENTS,
        q2bin     = _Q2BINS,
        )
rule metadata:
    output: _OUTPUTDIR + '/{q2bin}/{prc}_{cmb}/index.md'
    shell :
        '''
        echo "Title: {wildcards.prc}-{wildcards.cmb}"  > {output}
        echo "Thumbnail: data.png"   >> {output}
        '''
rule link:
    output: _OUTPUTDIR + '/{q2bin}/{prc}_{cmb}/{component}.png'
    params:
        root_dir = _INPUT_DIR,
        trigger  = 'Hlt2RD_B0ToKpPimEE_MVA',
    shell:
        '''
        mkdir -p $(dirname {output})

        COMP={wildcards.component}
        WP={wildcards.cmb}_{wildcards.prc}_all

        if [[ $COMP == "data" ]]; then
            SOURCE={params.root_dir}/$WP/rare/rkst/electron/{wildcards.component}/{wildcards.q2bin}/brem_x12/fit_linear.png
        elif [[ $COMP == "ccbar" ]]; then
            SOURCE={params.root_dir}/$WP/rare/rkst/electron/{wildcards.component}/{params.trigger}_{wildcards.q2bin}/c-bar-c-X.png
        elif [[ $COMP == "combinatorial" ]]; then
            SOURCE={params.root_dir}/$WP/rare/rkst/electron/{wildcards.component}/{params.trigger}_{wildcards.q2bin}/fit_linear.png
        else
            SOURCE={params.root_dir}/$WP/rare/rkst/electron/{wildcards.component}/{params.trigger}_{wildcards.q2bin}/main/fit_linear.png
        fi

        if [[ -f $SOURCE ]] && ! identify "$SOURCE" >/dev/null 2>&1; then
            rm "$SOURCE"
        fi

        if [[ ! -f $SOURCE ]]; then
            rxfitter make-dummy-plot -p {output} -t "{wildcards.component}" -l 30
        else
            cp $SOURCE {output}
        fi
        '''
